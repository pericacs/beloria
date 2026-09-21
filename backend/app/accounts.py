"""Identity provisioning; e-mail is never evidence to attach a membership."""
from fastapi import HTTPException
from sqlalchemy import delete, func, select, text
from .auth import digest, hasher
from .models import AuthSession, Identity, User


def reserve_email(db, email, identity_id=None):
    email = email.strip().lower()
    key = int(digest('identity-email:'+email)[:16],16)
    if key >= 2**63:
        key -= 2**64
    db.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key': key})
    query = select(Identity.id).where(Identity.email == email)
    if identity_id is not None:
        query = query.where(Identity.id != identity_id)
    if db.scalar(query.limit(1)) is not None:
        raise HTTPException(409, 'E-mail indisponível. Use outro e-mail ou solicite ao administrador um vínculo explícito com a identidade existente.')
    return email


def create_identity(db, email, password):
    account = Identity(email=reserve_email(db,email), password_hash=hasher.hash(password), login_enabled=True)
    db.add(account)
    db.flush()
    return account


def change_credentials(db, account, email, password=None, tenant_manager=False):
    # A manager of one business cannot reset an identity spanning other businesses.
    count = db.scalar(select(func.count()).select_from(User).where(User.identity_id == account.id))
    if tenant_manager and (count != 1 or not account.login_enabled):
        raise HTTPException(409, 'Identidade compartilhada ou pendente de regularização: solicite a alteração ao administrador do sistema.')
    account.email = reserve_email(db, email, account.id)
    if password is not None:
        account.password_hash = hasher.hash(password)
    account.login_enabled = True
    for membership in db.scalars(select(User).where(User.identity_id == account.id)):
        membership.email, membership.password_hash = account.email, account.password_hash
    db.execute(delete(AuthSession).where(AuthSession.identity_id == account.id))


def membership(db, account, business_id, role='gestor', professional_id=None):
    row = User(identity_id=account.id, business_id=business_id, email=account.email, password_hash=account.password_hash, role=role, professional_id=professional_id)
    db.add(row)
    db.flush()
    return row
