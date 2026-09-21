from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select
from .auth import manager
from .common import page, record
from .db import get_db
from .filters import Period
from .models import Attendance, Audit, PayoutItem, User

router = APIRouter(tags=["Indicadores"])

@router.get("/dashboard")
def dashboard(filters: Period = Depends(), db=Depends(get_db)):
    paid = Attendance.id.in_(select(PayoutItem.attendance_id))
    approved = Attendance.status == "approved"
    sums = db.execute(select(
        func.count(Attendance.id),
        func.coalesce(func.sum(case((approved, Attendance.price_cents), else_=0)), 0),
        func.coalesce(func.sum(case((Attendance.status == "pending", Attendance.commission_cents), else_=0)), 0),
        func.coalesce(func.sum(case((approved & ~paid, Attendance.commission_cents), else_=0)), 0),
        func.coalesce(func.sum(case((paid, Attendance.commission_cents), else_=0)), 0),
    ).where(*filters.conditions())).one()
    day = func.date(func.timezone("America/Sao_Paulo", Attendance.created_at))
    series = db.execute(select(day.label("day"), func.sum(Attendance.price_cents).label("revenue_cents")).where(*filters.conditions(), approved).group_by(day).order_by(day)).all()
    return {"attendance_count": sums[0], "revenue_cents": sums[1], "pending_cents": sums[2], "payable_cents": sums[3], "paid_cents": sums[4], "series": [{"day": str(row.day), "revenue_cents": row.revenue_cents} for row in series]}

@router.get("/audit")
def audit_events(page_number: int = Query(1, alias="page", ge=1), page_size: int = Query(25, ge=1, le=100), user=Depends(manager), db=Depends(get_db)):
    query = select(Audit).where(Audit.business_id == user.business_id).order_by(Audit.id.desc())
    def serialize(row):
        data = record(row)
        data["user_email"] = db.get(User, row.user_id).email
        return data
    return page(db, query, page_number, page_size, serialize)
