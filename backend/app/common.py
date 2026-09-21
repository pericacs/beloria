from fastapi import HTTPException
from sqlalchemy import func, select
from .models import Audit

def owned(db, model, object_id, user, active=False, lock=False):
    query = select(model).where(model.id == object_id, model.business_id == user.business_id)
    if lock:
        query = query.with_for_update()
    row = db.scalar(query)
    if row is None or (active and not row.active):
        raise HTTPException(404, "Registro inexistente ou desativado")
    return row

def audit(db, user, action, row, details=None):
    db.add(Audit(business_id=user.business_id, user_id=user.id, action=action, entity=row.__tablename__, entity_id=row.id, details=details or {}))

def page(db, query, number, size, serialize):
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    rows = db.scalars(query.offset((number-1)*size).limit(size)).all()
    return {"items": [serialize(row) for row in rows], "total": total, "page": number, "page_size": size}

def record(row, omit=()):
    return {column.name: getattr(row, column.name) for column in row.__table__.columns if column.name not in ("business_id", *omit)}
