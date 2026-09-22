import hashlib
import os
import secrets
from datetime import timedelta
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from .db import get_db
from .models import AuthSession, Business, Identity, LoginThrottle, Professional, User, now
from .schemas import LoginInput, SelectBusinessInput
from .commercial_models import PlatformAdmin, JoinRequest
from .access import business_access

router = APIRouter(prefix="/auth", tags=["Autenticação"])
hasher = PasswordHasher()
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(32))
COOKIE = "beloria_session"


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def authorized_memberships(db, identity_id):
    return db.scalars(select(User).outerjoin(Professional, Professional.id == User.professional_id).where(
        User.identity_id == identity_id, User.active.is_(True),
        (User.professional_id.is_(None) | Professional.active.is_(True))
    ).order_by(User.id)).all()


def authenticated_session(request: Request, db=Depends(get_db)):
    token = request.cookies.get(COOKIE)
    session = db.get(AuthSession, digest(token)) if token else None
    if not session or session.expires_at <= now():
        raise HTTPException(401, "Sessão expirada. Entre novamente.")
    account = db.get(Identity, session.identity_id)
    if not account or not account.login_enabled:
        raise HTTPException(401, "Acesso desativado")
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        if not secrets.compare_digest(request.headers.get("X-CSRF-Token", ""), session.csrf_token):
            raise HTTPException(403, "Token de segurança inválido")
    return session


def selected_user(session=Depends(authenticated_session), db=Depends(get_db)):
    if db.get(Identity, session.identity_id).specialist_conflict:
        raise HTTPException(403, "Vínculos preexistentes em análise pelo administrador")
    if session.user_id is None:
        raise HTTPException(403, "Selecione um negócio autorizado para continuar")
    user = next((u for u in authorized_memberships(db, session.identity_id) if u.id == session.user_id), None)
    if user is None:
        raise HTTPException(401, "Vínculo desativado. Entre novamente.")
    return user


def current_user(user=Depends(selected_user), db=Depends(get_db)):
    access=business_access(db, db.get(Business,user.business_id))
    if not access['allowed']:
        raise HTTPException(402, "Pagamento necessário" if user.role=='gestor' else "Acesso suspenso. Entre em contato com o responsável pela empresa.")
    return user


def platform_admin(session=Depends(authenticated_session),db=Depends(get_db)):
    if not db.get(PlatformAdmin,session.identity_id):
        raise HTTPException(403,"Acesso exclusivo do administrador Beloria")
    return db.get(Identity,session.identity_id)


def manager(user=Depends(current_user)):
    if user.role != "gestor":
        raise HTTPException(403, "Acesso exclusivo do gestor")
    return user


def session_view(session, db):
    account = db.get(Identity, session.identity_id)
    memberships = authorized_memberships(db, account.id)
    choices = [{"membership_id": u.id, "name": db.get(Business, u.business_id).name, "role": u.role} for u in memberships]
    base = {"email": account.email, "csrf_token": session.csrf_token, "businesses": choices}
    if db.get(PlatformAdmin, account.id):
        return {**base, "selection_required":False, "destination":"platform", "role":"platform", "id":account.id}
    if account.specialist_conflict:
        return {**base, "selection_required":False, "destination":"conflict", "role":"profissional", "id":account.id}
    if session.user_id is None:
        if memberships:
            return {**base, "selection_required": True, "destination":"select"}
        application=db.scalar(select(JoinRequest).where(JoinRequest.identity_id==account.id).order_by(JoinRequest.id.desc()).limit(1))
        return {**base, "selection_required":False, "destination":"waiting", "role":"profissional", "id":account.id,
                "request_state": application.status if application else "unlinked", "rejection_reason":application.rejection_reason if application else None}
    user = next((u for u in memberships if u.id == session.user_id), None)
    if user is None:
        raise HTTPException(401, "Vínculo desativado. Entre novamente.")
    business=db.get(Business,user.business_id)
    access=business_access(db,business)
    destination=('client' if user.role=='gestor' else 'specialist') if access['allowed'] else ('payment' if user.role=='gestor' else 'suspended')
    return {**base, "selection_required": False, "id": user.id, "role": user.role, "professional_id": user.professional_id, "business_name": business.name,
            "destination":destination,"access_state":access['state'],"trial_ends_at":business.trial_ends_at}


def issue_session(db, response, account_id, user_id, hours=12):
    token, csrf = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
    session = AuthSession(token_hash=digest(token), identity_id=account_id, user_id=user_id, csrf_token=csrf, expires_at=now()+timedelta(hours=hours))
    db.add(session)
    response.set_cookie(COOKIE, token, httponly=True, secure=os.getenv("COOKIE_SECURE", "true").lower() == "true", samesite="strict", max_age=int(hours*3600), path="/")
    return session


@router.post("/login")
def login(payload: LoginInput, request: Request, response: Response, db=Depends(get_db)):
    email = str(payload.email).lower()
    key = digest(f"{request.client.host if request.client else 'unknown'}:{email}")
    db.execute(insert(LoginThrottle).values(key=key, attempts=0, window_start=now()).on_conflict_do_nothing())
    throttle = db.scalar(select(LoginThrottle).where(LoginThrottle.key == key).with_for_update())
    if throttle.window_start + timedelta(minutes=15) <= now():
        throttle.attempts, throttle.window_start = 0, now()
    if throttle.attempts >= 10:
        db.commit()
        raise HTTPException(429, "Muitas tentativas. Aguarde 15 minutos.")
    throttle.attempts += 1
    db.commit()
    # Never choose the first match, nor infer account ownership from matching email.
    matches = db.scalars(select(Identity).where(Identity.email == email).order_by(Identity.id).limit(2).with_for_update()).all()
    account = matches[0] if len(matches) == 1 and matches[0].login_enabled else None
    try:
        valid = hasher.verify(account.password_hash if account else DUMMY_HASH, payload.password)
    except (VerificationError, InvalidHashError):
        valid = False
    memberships = authorized_memberships(db, account.id) if account and valid else []
    if not valid or not account or (not memberships and not db.get(PlatformAdmin,account.id) and not db.scalar(select(JoinRequest.id).where(JoinRequest.identity_id==account.id).limit(1))):
        raise HTTPException(401, "E-mail ou senha inválidos, ou acesso indisponível. Se necessário, contate o administrador.")
    old_token = request.cookies.get(COOKIE)
    old = db.get(AuthSession, digest(old_token)) if old_token else None
    if old:
        db.delete(old)
    session = issue_session(db, response, account.id, memberships[0].id if len(memberships) == 1 else None)
    db.commit()
    return session_view(session, db)


@router.post("/select-business")
def select_business(payload: SelectBusinessInput, response: Response, session=Depends(authenticated_session), db=Depends(get_db)):
    user = next((u for u in authorized_memberships(db, session.identity_id) if u.id == payload.membership_id), None)
    if user is None:
        raise HTTPException(403, "Negócio não autorizado")
    # Rotate cookie and CSRF token; the selected membership supplies tenant and role.
    account_id = session.identity_id
    db.delete(session)
    replacement = issue_session(db, response, account_id, user.id)
    db.commit()
    return session_view(replacement, db)


@router.get("/me")
def me(session=Depends(authenticated_session), db=Depends(get_db)):
    memberships=authorized_memberships(db,session.identity_id)
    if session.user_id is None and len(memberships)==1:
        session.user_id=memberships[0].id
        db.commit()
    return session_view(session, db)


@router.post("/logout", status_code=204)
def logout(response: Response, session=Depends(authenticated_session), db=Depends(get_db)):
    db.delete(session)
    db.commit()
    response.delete_cookie(COOKIE, path="/")
