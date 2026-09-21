from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, select
from .auth import current_user, hasher, manager
from .common import audit, owned, page, record
from .db import get_db
from .models import Client, Professional, ProfessionalSpecialty, Service, Specialty, User
from .schemas import ClientInput, ProfessionalInput, ServiceInput, SpecialtyInput

router = APIRouter(tags=["Cadastros"])

def professional_record(db, row, user):
    data = record(row)
    data["specialty_ids"] = list(db.scalars(select(ProfessionalSpecialty.specialty_id).where(ProfessionalSpecialty.business_id == user.business_id, ProfessionalSpecialty.professional_id == row.id)))
    account = db.scalar(select(User).where(User.business_id == user.business_id, User.professional_id == row.id))
    data["email"] = account.email if account else ""
    return data

@router.get("/professionals")
def professionals(number: int = Query(1, alias="page", ge=1), page_size: int = Query(25, ge=1, le=100), user=Depends(current_user), db=Depends(get_db)):
    query = select(Professional).where(Professional.business_id == user.business_id).order_by(Professional.name, Professional.id)
    if user.role == "profissional":
        query = query.where(Professional.id == user.professional_id)
    return page(db, query, number, page_size, lambda row: professional_record(db, row, user))

def save_professional(payload, db, user, row=None):
    for specialty_id in payload.specialty_ids:
        owned(db, Specialty, specialty_id, user, active=payload.active)
    values = payload.model_dump(exclude={"specialty_ids", "email", "password"})
    if row is None:
        if not payload.password:
            raise HTTPException(422, "Informe uma senha de pelo menos 12 caracteres")
        row = Professional(business_id=user.business_id, **values)
        db.add(row)
        db.flush()
        account = User(business_id=user.business_id, professional_id=row.id, role="profissional", email=str(payload.email).lower(), password_hash=hasher.hash(payload.password), active=payload.active)
        db.add(account)
        action = "created"
    else:
        for key, value in values.items():
            setattr(row, key, value)
        account = db.scalar(select(User).where(User.business_id == user.business_id, User.professional_id == row.id).with_for_update())
        account.email, account.active = str(payload.email).lower(), payload.active
        if payload.password:
            account.password_hash = hasher.hash(payload.password)
            from .models import AuthSession
            db.execute(delete(AuthSession).where(AuthSession.user_id == account.id))
        action = "updated"
    db.execute(delete(ProfessionalSpecialty).where(ProfessionalSpecialty.business_id == user.business_id, ProfessionalSpecialty.professional_id == row.id))
    for specialty_id in payload.specialty_ids:
        db.add(ProfessionalSpecialty(business_id=user.business_id, professional_id=row.id, specialty_id=specialty_id))
    audit(db, user, action, row, {"active": row.active})
    db.commit()
    return professional_record(db, row, user)

@router.post("/professionals", status_code=201)
def create_professional(payload: ProfessionalInput, user=Depends(manager), db=Depends(get_db)):
    return save_professional(payload, db, user)

@router.put("/professionals/{object_id}")
def update_professional(object_id: int, payload: ProfessionalInput, user=Depends(manager), db=Depends(get_db)):
    return save_professional(payload, db, user, owned(db, Professional, object_id, user, lock=True))

# Separate, typed routes share the same tenant-safe persistence primitive.
def save_catalog(model, payload, db, user, object_id=None):
    if isinstance(payload, ServiceInput):
        owned(db, Specialty, payload.specialty_id, user, active=payload.active)
    if object_id is None:
        row = model(business_id=user.business_id, **payload.model_dump())
        db.add(row)
        action = "created"
    else:
        row = owned(db, model, object_id, user, lock=True)
        for key, value in payload.model_dump().items():
            setattr(row, key, value)
        action = "updated"
    db.flush()
    audit(db, user, action, row, {"active": row.active})
    db.commit()
    return record(row)

def list_catalog(model, db, user, number, size):
    query = select(model).where(model.business_id == user.business_id).order_by(model.name, model.id)
    if user.role == "profissional":
        query = query.where(model.active.is_(True))
    return page(db, query, number, size, record)

@router.get("/specialties")
def specialties(page_number: int = Query(1, alias="page", ge=1), page_size: int = Query(25, ge=1, le=100), user=Depends(current_user), db=Depends(get_db)):
    return list_catalog(Specialty, db, user, page_number, page_size)

@router.post("/specialties", status_code=201)
def create_specialty(payload: SpecialtyInput, user=Depends(manager), db=Depends(get_db)):
    return save_catalog(Specialty, payload, db, user)

@router.put("/specialties/{object_id}")
def update_specialty(object_id: int, payload: SpecialtyInput, user=Depends(manager), db=Depends(get_db)):
    return save_catalog(Specialty, payload, db, user, object_id)

@router.get("/clients")
def clients(page_number: int = Query(1, alias="page", ge=1), page_size: int = Query(25, ge=1, le=100), user=Depends(current_user), db=Depends(get_db)):
    return list_catalog(Client, db, user, page_number, page_size)

@router.post("/clients", status_code=201)
def create_client(payload: ClientInput, user=Depends(manager), db=Depends(get_db)):
    return save_catalog(Client, payload, db, user)

@router.put("/clients/{object_id}")
def update_client(object_id: int, payload: ClientInput, user=Depends(manager), db=Depends(get_db)):
    return save_catalog(Client, payload, db, user, object_id)

@router.get("/services")
def services(page_number: int = Query(1, alias="page", ge=1), page_size: int = Query(25, ge=1, le=100), user=Depends(current_user), db=Depends(get_db)):
    return list_catalog(Service, db, user, page_number, page_size)

@router.post("/services", status_code=201)
def create_service(payload: ServiceInput, user=Depends(manager), db=Depends(get_db)):
    return save_catalog(Service, payload, db, user)

@router.put("/services/{object_id}")
def update_service(object_id: int, payload: ServiceInput, user=Depends(manager), db=Depends(get_db)):
    return save_catalog(Service, payload, db, user, object_id)
