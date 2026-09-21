from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo
from fastapi import Depends, HTTPException, Query
from sqlalchemy import select
from .auth import current_user
from .models import Attendance

class Period:
    def __init__(self, start: date | None = None, end: date | None = None, professional_id: int | None = Query(None, gt=0), user=Depends(current_user)):
        if start and end and start > end:
            raise HTTPException(422, "Período inválido")
        if user.role == "profissional" and professional_id not in (None, user.professional_id):
            raise HTTPException(403, "Você só pode consultar seus próprios valores")
        self.professional_id = user.professional_id if user.role == "profissional" else professional_id
        self.start, self.end, self.user = start, end, user

    def conditions(self):
        clauses = [Attendance.business_id == self.user.business_id]
        zone = ZoneInfo("America/Sao_Paulo")
        if self.start:
            clauses.append(Attendance.created_at >= datetime.combine(self.start, time.min, zone))
        if self.end:
            clauses.append(Attendance.created_at < datetime.combine(self.end + timedelta(days=1), time.min, zone))
        if self.professional_id:
            clauses.append(Attendance.professional_id == self.professional_id)
        return clauses

    def query(self):
        return select(Attendance).where(*self.conditions())
