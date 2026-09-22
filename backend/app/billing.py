from dataclasses import asdict
from datetime import timedelta
import hashlib
import json
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy import select, text
from .access import business_access
from .auth import selected_user
from .common import page, record
from .db import get_db
from .models import Business, now
from .commercial_models import Invoice, PaymentEvent, PlatformAudit, Subscription
from .payment_provider import get_provider

router=APIRouter(prefix='/billing',tags=['Assinatura'])


def billing_manager(user=Depends(selected_user)):
    if user.role!='gestor': raise HTTPException(403,'Cobrança disponível apenas ao responsável pela empresa')
    return user


def transaction_lock(db,key):
    value=int.from_bytes(hashlib.sha256(key.encode()).digest()[:8],'big',signed=True)
    db.execute(text('SELECT pg_advisory_xact_lock(:key)'),{'key':value})


@router.get('/status')
def status(user=Depends(billing_manager),db=Depends(get_db),provider=Depends(get_provider)):
    business=db.get(Business,user.business_id)
    subscription=db.get(Subscription,business.id)
    return {**business_access(db,business),'company_name':business.name,'trial_started_at':business.trial_started_at,'trial_ends_at':business.trial_ends_at,
            'subscription':record(subscription) if subscription else None,'payment_available':provider is not None,
            'message':None if provider else 'Pagamento indisponível: planos, preços e provedor ainda não configurados. Contate o Beloria.'}


@router.get('/invoices')
def invoices(page_number:int=Query(1,alias='page',ge=1),page_size:int=Query(25,ge=1,le=100),user=Depends(billing_manager),db=Depends(get_db)):
    return page(db,select(Invoice).where(Invoice.business_id==user.business_id).order_by(Invoice.id.desc()),page_number,page_size,lambda row:record(row,('request_key',)))


@router.post('/checkout',status_code=201)
def checkout(idempotency_key:str=Header(min_length=8,max_length=100),user=Depends(billing_manager),db=Depends(get_db),provider=Depends(get_provider)):
    if provider is None: raise HTTPException(503,'Pagamento indisponível: integração e condições comerciais não configuradas')
    transaction_lock(db,f'checkout:{user.business_id}:{idempotency_key}')
    existing=db.scalar(select(Invoice).where(Invoice.business_id==user.business_id,Invoice.request_key==idempotency_key))
    if existing: return record(existing,('request_key',))
    result=provider.create_checkout(user.business_id,idempotency_key)
    if result.amount_cents<=0 or len(result.currency)!=3 or urlparse(result.url).scheme!='https':
        raise HTTPException(502,'Resposta de cobrança inválida')
    row=Invoice(business_id=user.business_id,provider=provider.name,provider_reference=result.reference,request_key=idempotency_key,amount_cents=result.amount_cents,currency=result.currency,checkout_url=result.url)
    db.add(row);db.flush();db.add(PlatformAudit(identity_id=user.identity_id,business_id=user.business_id,action='billing.checkout_created',details={'invoice_id':row.id}))
    db.commit()
    return record(row,('request_key',))


def apply_verified_payment(db,provider_name,event):
    if not event.event_id or not event.reference or event.amount_cents<=0 or event.paid_at.tzinfo is None or event.valid_until.tzinfo is None or event.paid_at>now()+timedelta(minutes=5) or event.valid_until<=event.paid_at:
        raise HTTPException(400,'Confirmação de pagamento inválida')
    fingerprint=hashlib.sha256(json.dumps(asdict(event),default=str,sort_keys=True).encode()).hexdigest()
    transaction_lock(db,f'payment:{provider_name}:{event.event_id}')
    existing=db.scalar(select(PaymentEvent).where(PaymentEvent.provider==provider_name,PaymentEvent.event_id==event.event_id))
    if existing:
        if existing.fingerprint!=fingerprint: raise HTTPException(409,'Evento repetido com conteúdo diferente')
        return {'received':True,'duplicate':True}
    invoice=db.scalar(select(Invoice).where(Invoice.provider==provider_name,Invoice.provider_reference==event.reference).with_for_update())
    if not invoice or invoice.amount_cents!=event.amount_cents or invoice.currency!=event.currency:
        raise HTTPException(400,'Confirmação não corresponde à cobrança')
    if invoice.status=='canceled': raise HTTPException(409,'Cobrança cancelada exige conciliação')
    # Serialize subscriptions across different invoices for the same business.
    db.scalar(select(Business).where(Business.id==invoice.business_id).with_for_update())
    duplicate=invoice.status=='paid'
    if not duplicate:
        invoice.status='paid';invoice.paid_at=event.paid_at
        subscription=db.get(Subscription,invoice.business_id)
        if subscription is None:
            db.add(Subscription(business_id=invoice.business_id,status='active',valid_until=event.valid_until))
        elif event.valid_until>subscription.valid_until:
            subscription.status='active';subscription.valid_until=event.valid_until
    db.add(PaymentEvent(provider=provider_name,event_id=event.event_id,invoice_id=invoice.id,fingerprint=fingerprint))
    db.add(PlatformAudit(business_id=invoice.business_id,action='billing.payment_confirmed',details={'invoice_id':invoice.id,'duplicate_invoice':duplicate}))
    db.commit()
    return {'received':True,'duplicate':duplicate}


@router.post('/webhook')
async def webhook(request:Request,x_payment_signature:str=Header(default=''),db=Depends(get_db),provider=Depends(get_provider)):
    if provider is None: raise HTTPException(503,'Provedor não configurado')
    raw=await request.body()
    if len(raw)>65536: raise HTTPException(413,'Evento muito grande')
    try:
        event=provider.verify_payment(raw,x_payment_signature)
    except (ValueError,PermissionError):
        raise HTTPException(400,'Evento não autenticado ou pagamento não confirmado')
    return apply_verified_payment(db,provider.name,event)
