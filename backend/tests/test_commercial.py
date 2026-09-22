"""Commercial lifecycle integration proofs against disposable PostgreSQL only."""
import hashlib
import hmac
import json
import secrets
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.accounts import create_identity
from app.commercial_models import Invitation, Invoice, JoinRequest, PaymentEvent, PlatformAdmin, Subscription
from app.db import SessionLocal
from app.main import app
from app.models import Business, Identity, User, now
from app.payment_provider import Checkout, VerifiedPayment, get_provider
from conftest import create


def company(label='company'):
    client = TestClient(app)
    secret = secrets.token_urlsafe(24)
    payload = dict(company_name=label, responsible_name='Responsavel sintetico', email=f'{secrets.token_hex(8)}@example.com', password=secret)
    response = client.post('/api/public/signup', json=payload)
    assert response.status_code == 201, response.text
    client.headers['X-CSRF-Token'] = response.json()['csrf_token']
    return client, payload, response.json()


def invitation(manager):
    return create(manager, 'invitations', {'valid_days': 7})


def specialist(manager):
    invite = invitation(manager)
    client = TestClient(app)
    payload = dict(name='Especialista sintetico', engagement='autonomo', cpf='52998224725', email=f'{secrets.token_hex(8)}@example.com', password=secrets.token_urlsafe(24))
    response = client.post('/api/public/invitations/'+invite['path'].split('/')[-1]+'/signup', json=payload)
    assert response.status_code == 201, response.text
    client.headers['X-CSRF-Token'] = response.json()['csrf_token']
    request = manager.get('/api/join-requests').json()['items'][0]
    return client, request, payload


def approve(manager, request):
    specialty = create(manager, 'specialties', {'name':'Especialidade '+secrets.token_hex(4)})
    response = manager.post(f"/api/join-requests/{request['id']}/review", json={'decision':'approved','specialty_ids':[specialty['id']],'commission_bps':3500})
    assert response.status_code == 200, response.text


def business_id_for(client):
    with SessionLocal() as db:
        return db.get(User, client.get('/api/auth/me').json()['id']).business_id


def expire(client):
    business_id = business_id_for(client)
    with SessionLocal.begin() as db:
        row = db.get(Business, business_id)
        row.trial_started_at = now()-timedelta(days=16)
        row.trial_ends_at = now()-timedelta(days=1)
    return business_id


def test_public_signup_privilege_trial_retry_and_destinations():
    manager, payload, session = company()
    assert session['destination'] == 'client'
    assert session['role'] == 'gestor'
    assert manager.get('/api/platform/companies').status_code == 403
    assert manager.get('/api/dashboard').status_code == 200
    with SessionLocal() as db:
        business = db.get(Business, business_id_for(manager))
        start = business.trial_started_at
        assert business.trial_ends_at-start == timedelta(days=15)
        assert abs((now()-start).total_seconds()) < 10
        assert business.legacy_access is False
        assert db.scalar(select(func.count()).select_from(PlatformAdmin)) == 0
    assert TestClient(app).post('/api/public/signup', json=payload).status_code == 409
    for extra in ({'role':'platform'}, {'legacy_access':True}, {'trial_ends_at':'2099-01-01'}, {'platform_admin':True}):
        assert TestClient(app).post('/api/public/signup', json={**payload, **extra}).status_code == 422
    with SessionLocal() as db:
        assert db.get(Business,business_id_for(manager)).trial_started_at == start
    professional, request, credentials = specialist(manager)
    assert professional.get('/api/auth/me').json()['destination'] == 'waiting'
    for path in ('dashboard','professionals','attendances','payouts','join-requests','billing/status'):
        assert professional.get('/api/'+path).status_code == 403
    approve(manager,request)
    assert professional.get('/api/auth/me').json()['destination'] == 'specialist'
    assert professional.get('/api/dashboard').status_code == 200
    assert professional.get('/api/join-requests').status_code == 403
    for creds, destination in ((payload,'client'),(credentials,'specialist')):
        response = TestClient(app).post('/api/auth/login',json={k:creds[k] for k in ('email','password')})
        assert response.json()['destination'] == destination


def test_platform_admin_cli_no_company_no_public_promotion(monkeypatch):
    import sys
    from app.platform_cli import main
    manager, payload, _ = company()
    secret=secrets.token_urlsafe(24)
    monkeypatch.setattr('getpass.getpass',lambda _:secret)
    monkeypatch.setattr(sys,'argv',['platform-cli','--email',payload['email']])
    with pytest.raises(SystemExit): main()
    monkeypatch.setattr(sys,'argv',['platform-cli','--email','platform@example.com'])
    main()
    client=TestClient(app)
    response=client.post('/api/auth/login',json={'email':'platform@example.com','password':secret})
    assert response.status_code == 200, response.text
    assert response.json()['destination'] == 'platform'
    assert response.json()['businesses'] == []
    client.headers['X-CSRF-Token']=response.json()['csrf_token']
    assert client.get('/api/platform/companies').json()['total'] == 1
    assert client.get('/api/dashboard').status_code == 403
    business=business_id_for(manager)
    assert client.put(f'/api/platform/companies/{business}/access',json={'access_blocked':True,'reason':'Teste controlado'}).status_code == 200
    assert manager.get('/api/dashboard').status_code == 402
    audit=client.get('/api/platform/audit').json()['items'][0]
    assert audit['business_id']==business and audit['company_name'] is not None
    assert audit['details']['reason']=='Teste controlado'
    assert manager.get('/api/billing/status').status_code == 200
    assert client.put(f'/api/platform/companies/{business}/access',json={'access_blocked':False,'reason':'Fim do teste'}).status_code == 200
    assert manager.get('/api/dashboard').status_code == 200


@pytest.mark.parametrize('state',['expired','revoked'])
def test_invite_expiration_revocation_and_hash(state):
    manager, _, _ = company()
    invite=invitation(manager)
    token=invite['path'].split('/')[-1]
    visitor=TestClient(app)
    assert visitor.get('/api/public/invitations/'+token).status_code == 200
    with SessionLocal.begin() as db:
        row=db.get(Invitation,invite['id'])
        assert row.token_hash != token and len(token)>=40
        if state=='expired': row.expires_at=now()-timedelta(seconds=1)
    if state=='revoked': assert manager.post(f"/api/invitations/{invite['id']}/revoke").status_code==200
    assert visitor.get('/api/public/invitations/'+token).status_code == 404
    assert visitor.post('/api/public/invitations/'+token+'/signup',json=dict(name='Sintetico',engagement='autonomo',cpf='52998224725',email='unused@example.com',password=secrets.token_urlsafe(24))).status_code == 404
    with SessionLocal() as db:
        assert db.scalar(select(Identity).where(Identity.email=='unused@example.com')) is None


def test_review_isolation_rejection_and_second_membership():
    a, _, _=company('A'); b, _, _=company('B')
    pro, request, credentials=specialist(a)
    endpoint=f"/api/join-requests/{request['id']}/review"
    reject={'decision':'rejected','reason':'Documentacao pendente'}
    assert b.post(endpoint,json=reject).status_code==404
    assert pro.post(endpoint,json=reject).status_code==403
    foreign=create(b,'specialties',{'name':'Foreign'})
    assert a.post(endpoint,json={'decision':'approved','specialty_ids':[foreign['id']],'commission_bps':1000}).status_code==404
    assert a.post(endpoint,json=reject).status_code==200
    assert pro.get('/api/auth/me').json()['request_state']=='rejected'
    assert a.post(endpoint,json=reject).status_code==409
    token=invitation(a)['path'].split('/')[-1]
    profile={k:v for k,v in credentials.items() if k not in ('email','password')}
    assert pro.post('/api/invitations/'+token+'/apply',json={**profile,'commission_bps':9999}).status_code==422
    assert pro.post('/api/invitations/'+token+'/apply',json=profile).status_code==201
    current=a.get('/api/join-requests').json()['items'][0]
    approve(a,current)
    assert pro.get('/api/auth/me').json()['destination']=='specialist'
    foreign_token=invitation(b)['path'].split('/')[-1]
    assert pro.post('/api/invitations/'+foreign_token+'/apply',json=profile).status_code==409
    assert b.get('/api/join-requests').json()['total']==0
    assert pro.get('/api/billing/status').status_code==403


def test_concurrent_invites_reserve_only_one_company():
    a, _, _=company('A'); b, _, _=company('B')
    pro, request, credentials=specialist(a)
    assert a.post(f"/api/join-requests/{request['id']}/review",json={'decision':'rejected','reason':'Reiniciar teste'}).status_code==200
    tokens=[invitation(c)['path'].split('/')[-1] for c in (a,b)]
    profile={k:v for k,v in credentials.items() if k not in ('email','password')}
    barrier=Barrier(2)
    def apply(token):
        client=TestClient(app);client.cookies.update(pro.cookies);client.headers.update(pro.headers)
        barrier.wait()
        return client.post('/api/invitations/'+token+'/apply',json=profile).status_code
    with ThreadPoolExecutor(2) as pool: results=list(pool.map(apply,tokens))
    assert sorted(results)==[201,409]
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(JoinRequest).where(JoinRequest.status=='pending'))==1


def test_trial_expiry_gates_existing_sessions_without_data_loss():
    manager, _, _=company(); pro,request,_=specialist(manager);approve(manager,request)
    assert pro.get('/api/auth/me').json()['destination']=='specialist'
    create(manager,'clients',{'name':'Registro preservado'})
    expire(manager)
    assert manager.get('/api/auth/me').json()['destination']=='payment'
    assert pro.get('/api/auth/me').json()['destination']=='suspended'
    for client in (manager,pro):
        for path in ('dashboard','clients','specialties','professionals','services','attendances','payouts'):
            assert client.get('/api/'+path).status_code==402,path
        assert client.post('/api/clients',json={'name':'Forbidden'}).status_code==402
    assert 'Acesso suspenso.' in pro.get('/api/dashboard').json()['detail']
    assert manager.get('/api/billing/status').json()['payment_available'] is False
    assert manager.post('/api/billing/checkout',headers={'Idempotency-Key':'unavailable'}).status_code==503
    assert TestClient(app).post('/api/billing/webhook',json={'paid':True}).status_code==503
    assert pro.get('/api/billing/status').status_code==403
    with SessionLocal() as db:
        from app.models import Client
        assert db.scalar(select(func.count()).select_from(Client))==1
    assert manager.post('/api/auth/logout').status_code==204
    assert pro.post('/api/auth/logout').status_code==204


class ControlledProvider:
    """Test-only signed settlement adapter; never installed by application code."""
    name='controlled-test'
    def __init__(self): self.key=secrets.token_bytes(32)
    def create_checkout(self,business_id,key):
        return Checkout(f'{business_id}:{key}',12345,'BRL','https://checkout.invalid/test')
    def verify_payment(self,raw,signature):
        if not hmac.compare_digest(hmac.new(self.key,raw,hashlib.sha256).hexdigest(),signature): raise PermissionError()
        value=json.loads(raw)
        if value.pop('status')!='settled': raise ValueError()
        for field in ('paid_at','valid_until'): value[field]=datetime.fromisoformat(value[field])
        return VerifiedPayment(**value)
    def send(self,client,event,valid=True):
        raw=json.dumps(event).encode()
        signature=hmac.new(self.key,raw,hashlib.sha256).hexdigest() if valid else 'invalid'
        return client.post('/api/billing/webhook',content=raw,headers={'X-Payment-Signature':signature})


def test_payment_verified_idempotent_concurrent_and_tenant_scoped():
    manager,_,_=company(); other,_,_=company('Other')
    pro,request,_=specialist(manager);approve(manager,request);pro.get('/api/auth/me')
    business=expire(manager);expire(other)
    provider=ControlledProvider();app.dependency_overrides[get_provider]=lambda:provider
    try:
        header={'Idempotency-Key':'controlled-invoice'}
        invoice=manager.post('/api/billing/checkout',headers=header).json()
        assert manager.post('/api/billing/checkout',headers=header).json()['id']==invoice['id']
        assert manager.get('/api/dashboard').status_code==402
        assert other.get('/api/billing/invoices').json()['total']==0
        event=dict(event_id='event-1',reference=invoice['provider_reference'],amount_cents=12345,currency='BRL',paid_at=now().isoformat(),valid_until=(now()+timedelta(days=25)).isoformat(),status='settled')
        client=TestClient(app)
        assert provider.send(client,event,False).status_code==400
        assert provider.send(client,{**event,'status':'pending'}).status_code==400
        assert provider.send(client,{**event,'amount_cents':1}).status_code==400
        assert manager.get('/api/dashboard').status_code==402
        barrier=Barrier(2)
        def send(_):
            barrier.wait();return provider.send(TestClient(app),event)
        with ThreadPoolExecutor(2) as pool: responses=list(pool.map(send,range(2)))
        assert [r.status_code for r in responses]==[200,200]
        assert sorted(r.json()['duplicate'] for r in responses)==[False,True]
        assert manager.get('/api/auth/me').json()['destination']=='client'
        assert pro.get('/api/auth/me').json()['destination']=='specialist'
        assert manager.get('/api/dashboard').status_code==200
        assert pro.get('/api/dashboard').status_code==200
        assert other.get('/api/dashboard').status_code==402
        assert provider.send(client,{**event,'valid_until':(now()+timedelta(days=99)).isoformat()}).status_code==409
        assert provider.send(client,{**event,'event_id':'event-2','valid_until':(now()+timedelta(days=99)).isoformat()}).json()['duplicate'] is True
        with SessionLocal() as db:
            assert db.get(Subscription,business).valid_until==datetime.fromisoformat(event['valid_until'])
            assert db.scalar(select(func.count()).select_from(Invoice))==1
            assert db.scalar(select(func.count()).select_from(PaymentEvent))==2
    finally: app.dependency_overrides.pop(get_provider,None)
