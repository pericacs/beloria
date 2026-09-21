from datetime import datetime, timezone
from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Integer, JSON, String, UniqueConstraint, Index, text
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

def now():
    return datetime.now(timezone.utc)

class Business(Base):
    __tablename__ = "businesses"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(160))

class Tenant:
    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)

class Specialty(Tenant, Base):
    __tablename__ = "specialties"
    __table_args__ = (UniqueConstraint("business_id", "id"), UniqueConstraint("business_id", "name"))
    name: Mapped[str] = mapped_column(String(120))
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class Professional(Tenant, Base):
    __tablename__ = "professionals"
    __table_args__ = (UniqueConstraint("business_id", "id"), CheckConstraint("commission_bps between 0 and 10000"), CheckConstraint("engagement in ('MEI','autonomo','CLT')"))
    name: Mapped[str] = mapped_column(String(160))
    contact: Mapped[str] = mapped_column(String(160), default="")
    commission_bps: Mapped[int] = mapped_column(Integer)
    engagement: Mapped[str] = mapped_column(String(20))
    cpf: Mapped[str | None] = mapped_column(String(11))
    cnpj: Mapped[str | None] = mapped_column(String(14))
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class ProfessionalSpecialty(Base):
    __tablename__ = "professional_specialties"
    __table_args__ = (ForeignKeyConstraint(["business_id", "professional_id"], ["professionals.business_id", "professionals.id"]), ForeignKeyConstraint(["business_id", "specialty_id"], ["specialties.business_id", "specialties.id"]))
    business_id: Mapped[int] = mapped_column(primary_key=True)
    professional_id: Mapped[int] = mapped_column(primary_key=True)
    specialty_id: Mapped[int] = mapped_column(primary_key=True)

class Identity(Base):
    __tablename__ = "identities"
    __table_args__ = (Index("uq_identity_login_email", "email", unique=True, postgresql_where=text("login_enabled")),)
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    login_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

class User(Tenant, Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("identity_id", "id", name="uq_user_identity_id"), UniqueConstraint("identity_id", "business_id", name="uq_identity_business"), UniqueConstraint("business_id", "email"), UniqueConstraint("business_id", "id"), UniqueConstraint("business_id", "professional_id"), ForeignKeyConstraint(["business_id", "professional_id"], ["professionals.business_id", "professionals.id"]), CheckConstraint("(role = 'gestor' and professional_id is null) or (role = 'profissional' and professional_id is not null)"))
    identity_id: Mapped[int] = mapped_column(ForeignKey("identities.id"), index=True)
    # Credential mirrors retained for migration rollback; Identity owns authentication.
    email: Mapped[str] = mapped_column(String(254))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))
    professional_id: Mapped[int | None] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class AuthSession(Base):
    __tablename__ = "auth_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    __table_args__ = (ForeignKeyConstraint(["identity_id", "user_id"], ["users.identity_id", "users.id"], name="fk_session_membership_identity"),)
    identity_id: Mapped[int] = mapped_column(ForeignKey("identities.id"))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    csrf_token: Mapped[str] = mapped_column(String(100))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class LoginThrottle(Base):
    __tablename__ = "login_throttles"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    attempts: Mapped[int] = mapped_column(default=0)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Client(Tenant, Base):
    __tablename__ = "clients"
    __table_args__ = (UniqueConstraint("business_id", "id"),)
    name: Mapped[str] = mapped_column(String(160))
    contact: Mapped[str] = mapped_column(String(160), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class Service(Tenant, Base):
    __tablename__ = "services"
    __table_args__ = (UniqueConstraint("business_id", "id"), ForeignKeyConstraint(["business_id", "specialty_id"], ["specialties.business_id", "specialties.id"]), CheckConstraint("price_cents >= 0"))
    name: Mapped[str] = mapped_column(String(160))
    specialty_id: Mapped[int] = mapped_column(Integer)
    price_cents: Mapped[int] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class Attendance(Tenant, Base):
    __tablename__ = "attendances"
    __table_args__ = (UniqueConstraint("business_id", "id"), UniqueConstraint("business_id", "request_key"), ForeignKeyConstraint(["business_id", "professional_id"], ["professionals.business_id", "professionals.id"]), ForeignKeyConstraint(["business_id", "client_id"], ["clients.business_id", "clients.id"]), ForeignKeyConstraint(["business_id", "service_id"], ["services.business_id", "services.id"]), ForeignKeyConstraint(["business_id", "created_by"], ["users.business_id", "users.id"]), ForeignKeyConstraint(["business_id", "reviewed_by"], ["users.business_id", "users.id"]), CheckConstraint("status in ('pending','approved','rejected')"), CheckConstraint("payment_method in ('pix','dinheiro','credito','debito')"), CheckConstraint("price_cents >= 0 and commission_cents >= 0 and commission_bps between 0 and 10000"), CheckConstraint("status != 'rejected' or length(rejection_reason) > 0"))
    professional_id: Mapped[int] = mapped_column(Integer, index=True)
    client_id: Mapped[int | None] = mapped_column(Integer)
    service_id: Mapped[int] = mapped_column(Integer)
    professional_name: Mapped[str] = mapped_column(String(160))
    client_name: Mapped[str] = mapped_column(String(160))
    service_name: Mapped[str] = mapped_column(String(160))
    price_cents: Mapped[int] = mapped_column(Integer)
    commission_bps: Mapped[int] = mapped_column(Integer)
    commission_cents: Mapped[int] = mapped_column(Integer)
    payment_method: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(500))
    created_by: Mapped[int] = mapped_column(Integer)
    reviewed_by: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    request_key: Mapped[str] = mapped_column(String(100))
    request_fingerprint: Mapped[str] = mapped_column(String(64))

class Payout(Tenant, Base):
    __tablename__ = "payouts"
    __table_args__ = (UniqueConstraint("business_id", "id"), UniqueConstraint("business_id", "request_key"), ForeignKeyConstraint(["business_id", "created_by"], ["users.business_id", "users.id"]), CheckConstraint("total_cents >= 0"))
    reference: Mapped[str] = mapped_column(String(200))
    request_key: Mapped[str] = mapped_column(String(100))
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    total_cents: Mapped[int] = mapped_column(BigInteger)
    created_by: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class PayoutItem(Base):
    __tablename__ = "payout_items"
    __table_args__ = (ForeignKeyConstraint(["business_id", "attendance_id"], ["attendances.business_id", "attendances.id"]), ForeignKeyConstraint(["business_id", "payout_id"], ["payouts.business_id", "payouts.id"]))
    attendance_id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(Integer, index=True)
    payout_id: Mapped[int] = mapped_column(Integer)

class Audit(Tenant, Base):
    __tablename__ = "audit_events"
    __table_args__ = (ForeignKeyConstraint(["business_id", "user_id"], ["users.business_id", "users.id"]),)
    user_id: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(80))
    entity: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[int] = mapped_column(Integer)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
