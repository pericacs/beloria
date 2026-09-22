"""Commercial lifecycle and specialist onboarding, separate from operational money."""
from datetime import datetime
from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Integer, JSON, String, UniqueConstraint, Index, text
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base
from .models import Tenant, now


class PlatformAdmin(Base):
    __tablename__ = 'platform_admins'
    identity_id: Mapped[int] = mapped_column(ForeignKey('identities.id'), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PlatformAudit(Base):
    __tablename__ = 'platform_audit'
    id: Mapped[int] = mapped_column(primary_key=True)
    identity_id: Mapped[int | None] = mapped_column(ForeignKey('identities.id'))
    business_id: Mapped[int | None] = mapped_column(ForeignKey('businesses.id'))
    action: Mapped[str] = mapped_column(String(100))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Invitation(Tenant, Base):
    __tablename__ = 'invitations'
    __table_args__ = (UniqueConstraint('business_id','id'), ForeignKeyConstraint(['business_id','created_by'],['users.business_id','users.id']))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SpecialistClaim(Base):
    __tablename__ = 'specialist_claims'
    identity_id: Mapped[int] = mapped_column(ForeignKey('identities.id'), primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey('businesses.id'))
    status: Mapped[str] = mapped_column(String(20))
    __table_args__ = (CheckConstraint("status in ('pending','approved','rejected')"),)


class JoinRequest(Tenant, Base):
    __tablename__ = 'join_requests'
    __table_args__ = (ForeignKeyConstraint(['business_id','invitation_id'],['invitations.business_id','invitations.id']), ForeignKeyConstraint(['business_id','reviewed_by'],['users.business_id','users.id']), CheckConstraint("status in ('pending','approved','rejected')"), Index('uq_open_join_identity','identity_id',unique=True,postgresql_where=text("status in ('pending','approved')")))
    identity_id: Mapped[int] = mapped_column(ForeignKey('identities.id'), index=True)
    invitation_id: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(160))
    contact: Mapped[str] = mapped_column(String(160), default='')
    engagement: Mapped[str] = mapped_column(String(20))
    cpf: Mapped[str | None] = mapped_column(String(11))
    cnpj: Mapped[str | None] = mapped_column(String(14))
    status: Mapped[str] = mapped_column(String(20), default='pending')
    rejection_reason: Mapped[str | None] = mapped_column(String(500))
    reviewed_by: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Subscription(Base):
    __tablename__ = 'subscriptions'
    business_id: Mapped[int] = mapped_column(ForeignKey('businesses.id'), primary_key=True)
    status: Mapped[str] = mapped_column(String(20))
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (CheckConstraint("status in ('active','canceled')"),)


class Invoice(Tenant, Base):
    __tablename__ = 'invoices'
    __table_args__ = (UniqueConstraint('provider','provider_reference'), UniqueConstraint('business_id','request_key'), CheckConstraint('amount_cents > 0'), CheckConstraint("status in ('pending','paid','canceled')"))
    provider: Mapped[str] = mapped_column(String(80))
    provider_reference: Mapped[str] = mapped_column(String(160))
    request_key: Mapped[str] = mapped_column(String(100))
    amount_cents: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(3))
    status: Mapped[str] = mapped_column(String(20), default='pending')
    checkout_url: Mapped[str] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PaymentEvent(Base):
    __tablename__ = 'payment_events'
    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(80))
    event_id: Mapped[str] = mapped_column(String(160))
    invoice_id: Mapped[int] = mapped_column(ForeignKey('invoices.id'))
    fingerprint: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (UniqueConstraint('provider','event_id'),)
