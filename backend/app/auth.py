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
from .models import AuthSession, Business, LoginThrottle, Professional, User, now
from .schemas import LoginInput

router = APIRouter(prefix="/auth", tags=["Autenticação"])
hasher = PasswordHasher()
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(32))
COOKIE = "beloria_session"

def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()

def current_user(request: Request, db=Depends(get_db)):
    token = request.cookies.get(COOKIE)
    session = db.get(AuthSession, digest(token)) if token else None
    if not session or session.expires_at <= now():
        raise HTTPException(401, "Sessão expirada. Entre novamente.")
    user = db.get(User, session.user_id)
    if not user or not user.active:
        raise HTTPException(401, "Acesso desativado")
    if user.professional_id:
        professional = db.get(Professional, user.professional_id)
        if not professional or not professional.active:
            raise HTTPException(401, "Acesso desativado")
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        if not secrets.compare_digest(request.headers.get("X-CSRF-Token", ""), session.csrf_token):
            raise HTTPException(403, "Token de segurança inválido")
    request.state.auth_session = session
    return user

def manager(user=Depends(current_user)):
    if user.role != "gestor":
        raise HTTPException(403, "Acesso exclusivo do gestor")
    return user

def identity(user, db, csrf):
    business = db.get(Business, user.business_id)
    return {"id": user.id, "email": user.email, "role": user.role, "professional_id": user.professional_id, "business_name": business.name, "csrf_token": csrf}

@router.post("/login")
def login(payload: LoginInput, request: Request, response: Response, db=Depends(get_db)):
    # Database-backed throttle shared by workers; no external service required.
    key = digest(f"{request.client.host if request.client else 'unknown'}:{payload.business.lower()}:{str(payload.email).lower()}")
    db.execute(insert(LoginThrottle).values(key=key, attempts=0, window_start=now()).on_conflict_do_nothing())
    throttle = db.scalar(select(LoginThrottle).where(LoginThrottle.key == key).with_for_update())
    if throttle.window_start + timedelta(minutes=15) <= now():
        throttle.attempts, throttle.window_start = 0, now()
    if throttle.attempts >= 10:
        db.commit()
        raise HTTPException(429, "Muitas tentativas. Aguarde 15 minutos.")
    throttle.attempts += 1
    db.commit()
    user = db.scalar(select(User).join(Business).where(Business.slug == payload.business.lower(), User.email == str(payload.email).lower()))
    try:
        valid = hasher.verify(user.password_hash if user else DUMMY_HASH, payload.password)
    except (VerificationError, InvalidHashError):
        valid = False
    if not valid or not user or not user.active or (user.professional_id and not db.get(Professional, user.professional_id).active):
        raise HTTPException(401, "Negócio, e-mail ou senha inválidos")
    token, csrf = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
    db.add(AuthSession(token_hash=digest(token), user_id=user.id, csrf_token=csrf, expires_at=now()+timedelta(hours=12)))
    db.commit()
    response.set_cookie(COOKIE, token, httponly=True, secure=os.getenv("COOKIE_SECURE", "true").lower() == "true", samesite="strict", max_age=43200, path="/")
    response.headers["Cache-Control"] = "no-store"
    return identity(user, db, csrf)

@router.get("/me")
def me(request: Request, user=Depends(current_user), db=Depends(get_db)):
    return identity(user, db, request.state.auth_session.csrf_token)

@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, user=Depends(current_user), db=Depends(get_db)):
    db.delete(request.state.auth_session)
    db.commit()
    response.delete_cookie(COOKIE, path="/")
