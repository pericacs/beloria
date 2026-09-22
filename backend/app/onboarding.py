from datetime import timedelta
import secrets
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from .accounts import create_identity, membership
from .auth import authenticated_session, digest, issue_session, manager, session_view
from .common import audit, owned, page, record
from .db import get_db
from .models import Business, Identity, Professional, ProfessionalSpecialty, Specialty, User, now
from .commercial_models import Invitation, JoinRequest, PlatformAdmin, PlatformAudit, SpecialistClaim
from .commercial_schemas import CompanySignup, InviteInput, JoinReview, SpecialistProfile, SpecialistSignup
from fastapi import Query

router=APIRouter(tags=['Cadastro e convites'])


@router.post('/public/signup',status_code=201)
def signup(payload:CompanySignup,response:Response,db=Depends(get_db)):
    account=create_identity(db,str(payload.email),payload.password)
    start=now()
    business=Business(slug='company-'+secrets.token_hex(12),name=payload.company_name,responsible_name=payload.responsible_name,contact=payload.contact,legacy_access=False,trial_started_at=start,trial_ends_at=start+timedelta(days=15))
    db.add(business);db.flush()
    user=membership(db,account,business.id)
    audit(db,user,'company.public_signup',business)
    db.add(PlatformAudit(identity_id=account.id,business_id=business.id,action='company.public_signup',details={}))
    session=issue_session(db,response,account.id,user.id)
    db.commit()
    return session_view(session,db)


@router.post('/invitations',status_code=201)
def invite(payload:InviteInput,user=Depends(manager),db=Depends(get_db)):
    token=secrets.token_urlsafe(32)
    row=Invitation(business_id=user.business_id,token_hash=digest(token),created_by=user.id,expires_at=now()+timedelta(days=payload.valid_days))
    db.add(row);db.flush();audit(db,user,'invitation.created',row);db.commit()
    return {**record(row,('token_hash',)), 'path':'/convite/'+token}


@router.get('/invitations')
def invitations(page_number:int=Query(1,alias='page',ge=1),page_size:int=Query(25,ge=1,le=100),user=Depends(manager),db=Depends(get_db)):
    return page(db,select(Invitation).where(Invitation.business_id==user.business_id).order_by(Invitation.id.desc()),page_number,page_size,lambda row:record(row,('token_hash',)))


@router.post('/invitations/{invitation_id}/revoke')
def revoke(invitation_id:int,user=Depends(manager),db=Depends(get_db)):
    row=owned(db,Invitation,invitation_id,user,lock=True)
    row.revoked=True;audit(db,user,'invitation.revoked',row);db.commit()
    return {'revoked':True}


def valid_invite(db,token,lock=False):
    if len(token)>100: raise HTTPException(404,'Convite inválido, expirado ou revogado')
    query=select(Invitation).where(Invitation.token_hash==digest(token))
    if lock: query=query.with_for_update()
    row=db.scalar(query)
    if not row or row.revoked or row.expires_at<=now():
        raise HTTPException(404,'Convite inválido, expirado ou revogado')
    return row


@router.get('/public/invitations/{token}')
def preview(token:str,db=Depends(get_db)):
    row=valid_invite(db,token)
    return {'company_name':db.get(Business,row.business_id).name,'expires_at':row.expires_at}


def request_membership(db,account,invitation,profile):
    # All paths reserve one identity row; two invitations cannot win concurrently.
    db.refresh(account,with_for_update=True)
    if account.specialist_conflict or db.get(PlatformAdmin,account.id):
        raise HTTPException(409,'Esta identidade não pode solicitar vínculo de especialista')
    users=db.scalars(select(User).where(User.identity_id==account.id)).all()
    if users:
        raise HTTPException(409,'Você já possui vínculo. O convite não transfere nem adiciona outro vínculo.')
    claim=db.get(SpecialistClaim,account.id)
    existing=db.scalar(select(JoinRequest).where(JoinRequest.identity_id==account.id,JoinRequest.status.in_(['pending','approved'])))
    if existing:
        if existing.business_id==invitation.business_id and existing.status=='pending': return existing
        raise HTTPException(409,'Já existe um vínculo ou solicitação em outra empresa')
    if claim and claim.status!='rejected':
        raise HTTPException(409,'Já existe uma solicitação ou vínculo')
    if not claim:
        claim=SpecialistClaim(identity_id=account.id,business_id=invitation.business_id,status='pending');db.add(claim)
    else:
        claim.business_id=invitation.business_id;claim.status='pending'
    row=JoinRequest(business_id=invitation.business_id,identity_id=account.id,invitation_id=invitation.id,**profile)
    db.add(row);db.flush()
    db.add(PlatformAudit(identity_id=account.id,business_id=invitation.business_id,action='specialist.requested',details={'request_id':row.id}))
    return row


@router.post('/public/invitations/{token}/signup',status_code=201)
def signup_specialist(token:str,payload:SpecialistSignup,response:Response,db=Depends(get_db)):
    invitation=valid_invite(db,token,lock=True)
    account=create_identity(db,str(payload.email),payload.password)
    request_membership(db,account,invitation,payload.model_dump(exclude={'email','password'}))
    session=issue_session(db,response,account.id,None)
    db.commit()
    return session_view(session,db)


@router.post('/invitations/{token}/apply',status_code=201)
def apply(token:str,payload:SpecialistProfile,session=Depends(authenticated_session),db=Depends(get_db)):
    invitation=valid_invite(db,token,lock=True)
    account=db.get(Identity,session.identity_id)
    row=request_membership(db,account,invitation,payload.model_dump())
    db.commit()
    return {'status':row.status,'id':row.id}


@router.get('/join-requests')
def applications(page_number:int=Query(1,alias='page',ge=1),page_size:int=Query(25,ge=1,le=100),user=Depends(manager),db=Depends(get_db)):
    return page(db,select(JoinRequest).where(JoinRequest.business_id==user.business_id).order_by(JoinRequest.id.desc()),page_number,page_size,record)


@router.post('/join-requests/{request_id}/review')
def review(request_id:int,payload:JoinReview,user=Depends(manager),db=Depends(get_db)):
    row=owned(db,JoinRequest,request_id,user,lock=True)
    if row.status!='pending': raise HTTPException(409,'Solicitação já analisada')
    account=db.scalar(select(Identity).where(Identity.id==row.identity_id).with_for_update())
    claim=db.get(SpecialistClaim,account.id)
    if payload.decision=='approved':
        for specialty_id in payload.specialty_ids: owned(db,Specialty,specialty_id,user,active=True)
        if account.specialist_conflict or db.scalar(select(User.id).where(User.identity_id==account.id).limit(1)):
            raise HTTPException(409,'Identidade já vinculada; aprovação não transfere vínculo')
        professional=Professional(business_id=user.business_id,name=row.name,contact=row.contact,engagement=row.engagement,cpf=row.cpf,cnpj=row.cnpj,commission_bps=payload.commission_bps)
        db.add(professional);db.flush()
        for specialty_id in payload.specialty_ids:
            db.add(ProfessionalSpecialty(business_id=user.business_id,professional_id=professional.id,specialty_id=specialty_id))
        membership(db,account,user.business_id,'profissional',professional.id)
    row.status=payload.decision;row.rejection_reason=payload.reason if payload.decision=='rejected' else None
    row.reviewed_by=user.id;row.reviewed_at=now();claim.status=payload.decision
    audit(db,user,'specialist.'+payload.decision,row,{'reason':row.rejection_reason})
    db.commit()
    return record(row)
