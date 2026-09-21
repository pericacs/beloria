import hashlib
import json
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import select, text
from .auth import current_user, manager
from .common import audit, owned, page, record
from .db import get_db
from .filters import Period
from .models import Attendance, Client, Payout, PayoutItem, Professional, ProfessionalSpecialty, Service, Specialty, now
from .schemas import AttendanceInput, PayoutInput, ReviewInput

router = APIRouter(tags=["Financeiro"])

def fingerprint(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

def idempotency(db, user, model, key, body):
    # Transaction-scoped advisory lock serializes retries, including first insertion.
    lock = int.from_bytes(hashlib.sha256(f"{user.business_id}:{model.__tablename__}:{key}".encode()).digest()[:8], "big", signed=True)
    db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock})
    existing = db.scalar(select(model).where(model.business_id == user.business_id, model.request_key == key))
    if existing and existing.request_fingerprint != fingerprint(body):
        raise HTTPException(409, "Chave de operação já utilizada com outros dados")
    return existing

def attendance_record(db, row):
    data = record(row, ("request_key", "request_fingerprint"))
    data["paid"] = db.get(PayoutItem, row.id) is not None
    return data

@router.get("/attendances")
def attendances(filters: Period = Depends(), status: str | None = Query(None, pattern="^(pending|approved|rejected)$"), paid: bool | None = None, page_number: int = Query(1, alias="page", ge=1), page_size: int = Query(25, ge=1, le=100), db=Depends(get_db)):
    query = filters.query().order_by(Attendance.created_at.desc(), Attendance.id.desc())
    if status:
        query = query.where(Attendance.status == status)
    if paid is not None:
        query = query.where(Attendance.id.in_(select(PayoutItem.attendance_id)) if paid else ~Attendance.id.in_(select(PayoutItem.attendance_id)))
    return page(db, query, page_number, page_size, lambda row: attendance_record(db, row))

@router.post("/attendances", status_code=201)
def create_attendance(payload: AttendanceInput, idempotency_key: str = Header(min_length=8, max_length=100), user=Depends(current_user), db=Depends(get_db)):
    if user.role == "profissional" and payload.professional_id != user.professional_id:
        raise HTTPException(403, "Você só pode lançar seus próprios atendimentos")
    body = {**payload.model_dump(), "actor": user.id}
    existing = idempotency(db, user, Attendance, idempotency_key, body)
    if existing:
        return attendance_record(db, existing)
    professional = owned(db, Professional, payload.professional_id, user, active=True, lock=True)
    service = owned(db, Service, payload.service_id, user, active=True, lock=True)
    owned(db, Specialty, service.specialty_id, user, active=True)
    link = db.get(ProfessionalSpecialty, (user.business_id, professional.id, service.specialty_id))
    if not link:
        raise HTTPException(422, "Profissional não vinculado à especialidade do serviço")
    client = owned(db, Client, payload.client_id, user, active=True) if payload.client_id else None
    row = Attendance(business_id=user.business_id, **payload.model_dump(), professional_name=professional.name, client_name=client.name if client else "Cliente avulso", service_name=service.name, price_cents=service.price_cents, commission_bps=professional.commission_bps, commission_cents=(service.price_cents*professional.commission_bps+5000)//10000, created_by=user.id, request_key=idempotency_key, request_fingerprint=fingerprint(body))
    db.add(row)
    db.flush()
    audit(db, user, "attendance.created", row)
    db.commit()
    return attendance_record(db, row)

@router.post("/attendances/{object_id}/review")
def review_attendance(object_id: int, payload: ReviewInput, user=Depends(manager), db=Depends(get_db)):
    row = owned(db, Attendance, object_id, user, lock=True)
    if row.status != "pending":
        raise HTTPException(409, "Atendimento já analisado")
    row.status, row.rejection_reason = payload.decision, payload.reason if payload.decision == "rejected" else None
    row.reviewed_by, row.reviewed_at = user.id, now()
    audit(db, user, "attendance."+payload.decision, row, {"reason": row.rejection_reason})
    db.commit()
    return attendance_record(db, row)

@router.post("/payouts", status_code=201)
def create_payout(payload: PayoutInput, idempotency_key: str = Header(min_length=8, max_length=100), user=Depends(manager), db=Depends(get_db)):
    ids = sorted(set(payload.attendance_ids))
    if len(ids) != len(payload.attendance_ids):
        raise HTTPException(422, "Atendimentos repetidos na seleção")
    body = {"attendance_ids": ids, "reference": payload.reference}
    existing = idempotency(db, user, Payout, idempotency_key, body)
    if existing:
        return record(existing, ("request_key", "request_fingerprint"))
    rows = db.scalars(select(Attendance).where(Attendance.business_id == user.business_id, Attendance.id.in_(ids)).order_by(Attendance.id).with_for_update()).all()
    if len(rows) != len(ids):
        raise HTTPException(404, "Atendimento não encontrado")
    if any(row.status != "approved" for row in rows):
        raise HTTPException(409, "Somente atendimentos aprovados podem ser repassados")
    if db.scalar(select(PayoutItem.attendance_id).where(PayoutItem.attendance_id.in_(ids)).limit(1)):
        raise HTTPException(409, "Um ou mais atendimentos já foram pagos")
    payout = Payout(business_id=user.business_id, reference=payload.reference, request_key=idempotency_key, request_fingerprint=fingerprint(body), total_cents=sum(row.commission_cents for row in rows), created_by=user.id)
    db.add(payout)
    db.flush()
    for row in rows:
        db.add(PayoutItem(business_id=user.business_id, payout_id=payout.id, attendance_id=row.id))
    audit(db, user, "payout.created", payout, {"attendance_ids": ids, "reference": payload.reference, "total_cents": payout.total_cents})
    db.commit()
    return record(payout, ("request_key", "request_fingerprint"))

@router.get("/payouts")
def payouts(filters: Period = Depends(), page_number: int = Query(1, alias="page", ge=1), page_size: int = Query(25, ge=1, le=100), db=Depends(get_db)):
    eligible_ids = select(PayoutItem.payout_id).join(Attendance, Attendance.id == PayoutItem.attendance_id).where(*filters.conditions())
    query = select(Payout).where(Payout.business_id == filters.user.business_id, Payout.id.in_(eligible_ids)).order_by(Payout.id.desc())
    def serialize(row):
        data = record(row, ("request_key", "request_fingerprint"))
        # Never expose a mixed payout total to an individual professional.
        matches = db.scalars(filters.query().join(PayoutItem, PayoutItem.attendance_id == Attendance.id).where(PayoutItem.payout_id == row.id)).all()
        data["total_cents"] = sum(item.commission_cents for item in matches)
        data["attendance_ids"] = [item.id for item in matches]
        return data
    return page(db, query, page_number, page_size, serialize)
