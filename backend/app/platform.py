from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from .access import business_access
from .auth import platform_admin
from .common import page, record
from .db import get_db
from .models import Business, Identity, User
from .commercial_models import Invoice, PlatformAudit, Subscription
from .commercial_schemas import BusinessAccessInput

router=APIRouter(prefix='/platform',tags=['Painel Beloria'])


def company_record(db,row):
    subscription=db.get(Subscription,row.id)
    return {**record(row),**business_access(db,row),'subscription':record(subscription) if subscription else None}


@router.get('/companies')
def companies(page_number:int=Query(1,alias='page',ge=1),page_size:int=Query(25,ge=1,le=100),admin=Depends(platform_admin),db=Depends(get_db)):
    return page(db,select(Business).order_by(Business.id.desc()),page_number,page_size,lambda row:company_record(db,row))


@router.put('/companies/{business_id}/access')
def access(business_id:int,payload:BusinessAccessInput,admin=Depends(platform_admin),db=Depends(get_db)):
    business=db.scalar(select(Business).where(Business.id==business_id).with_for_update())
    if business is None: raise HTTPException(404,'Empresa não encontrada')
    business.access_blocked=payload.access_blocked
    db.add(PlatformAudit(identity_id=admin.id,business_id=business_id,action='company.access_changed',details=payload.model_dump()))
    db.commit()
    return company_record(db,business)


@router.get('/payments')
def payments(page_number:int=Query(1,alias='page',ge=1),page_size:int=Query(25,ge=1,le=100),admin=Depends(platform_admin),db=Depends(get_db)):
    def serialize(row):
        return {**record(row,('request_key',)),'company_name':db.get(Business,row.business_id).name}
    return page(db,select(Invoice).order_by(Invoice.id.desc()),page_number,page_size,serialize)


@router.get('/conflicts')
def conflicts(page_number:int=Query(1,alias='page',ge=1),page_size:int=Query(25,ge=1,le=100),admin=Depends(platform_admin),db=Depends(get_db)):
    def serialize(row):
        return {'identity_id':row.id,'memberships':[{'id':u.id,'company_name':db.get(Business,u.business_id).name,'role':u.role} for u in db.scalars(select(User).where(User.identity_id==row.id))]}
    return page(db,select(Identity).where(Identity.specialist_conflict.is_(True)).order_by(Identity.id),page_number,page_size,serialize)


@router.get('/audit')
def history(page_number:int=Query(1,alias='page',ge=1),page_size:int=Query(25,ge=1,le=100),admin=Depends(platform_admin),db=Depends(get_db)):
    def serialize(row):
        business=db.get(Business,row.business_id) if row.business_id else None
        return {**record(row),'business_id':row.business_id,'company_name':business.name if business else None}
    return page(db,select(PlatformAudit).order_by(PlatformAudit.id.desc()),page_number,page_size,serialize)
