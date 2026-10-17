import uuid
from datetime import timedelta

from fastapi import HTTPException, Request, Response, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.audit import enforce_rate_limit, write_audit
from app.config import settings
from app.models import RefreshSession, User
from app.security import (
    clear_auth_cookies,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    new_csrf_token,
    set_auth_cookies,
    validate_password_policy,
    verify_csrf,
    verify_password,
)
from app.utils import get_client_ip, get_user_agent, random_token, sha256_hex, utcnow


DUMMY_PASSWORD_HASH = hash_password("VELMORA-Dummy-Password!2026")


def authenticate_and_start_session(db: Session, request: Request, response: Response, email: str, password: str) -> User:
    normalized_email = email.strip().lower()
    client_ip = get_client_ip(request)
    enforce_rate_limit(
        db,
        action_prefix="auth.login",
        client_ip=client_ip,
        limit=settings.login_ip_limit,
        window_minutes=settings.login_ip_window_minutes,
    )
    user = db.scalar(select(User).where(User.email == normalized_email))
    now = utcnow()

    if not user:
        verify_password(password, DUMMY_PASSWORD_HASH)
        write_audit(
            db,
            request,
            "auth.login.failed",
            success=False,
            message="Invalid email or password",
            details={"email_attempted": normalized_email},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if not user.is_active:
        verify_password(password, user.password_hash)
        write_audit(
            db,
            request,
            "auth.login.failed",
            actor=user,
            success=False,
            message="Inactive account",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if user.locked_until and user.locked_until > now:
        verify_password(password, user.password_hash)
        write_audit(
            db,
            request,
            "auth.login.locked",
            actor=user,
            success=False,
            message="Account temporarily locked",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    valid, needs_rehash = verify_password(password, user.password_hash)
    if not valid:
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.login_max_failures_per_account:
            user.locked_until = now + timedelta(minutes=settings.login_lock_minutes)
        write_audit(
            db,
            request,
            "auth.login.failed",
            actor=user,
            success=False,
            message="Invalid email or password",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    if needs_rehash:
        user.password_hash = hash_password(password)

    session = RefreshSession(
        user_id=user.id,
        refresh_jti_hash="",
        csrf_hash="",
        expires_at=now + timedelta(days=settings.refresh_token_days),
        ip_address=client_ip,
        user_agent=get_user_agent(request),
    )
    db.add(session)
    db.flush()
    refresh_jti = random_token(32)
    csrf_token = new_csrf_token()
    session.refresh_jti_hash = sha256_hex(refresh_jti)
    session.csrf_hash = sha256_hex(csrf_token)
    access_token = create_access_token(user.id, session.id, user.role.value)
    refresh_token = create_refresh_token(user.id, session.id, refresh_jti, session.expires_at)
    write_audit(db, request, "auth.login.success", actor=user, resource_type="session", resource_id=session.id)
    db.commit()
    set_auth_cookies(response, access_token, refresh_token, csrf_token)
    return user


def rotate_session(db: Session, request: Request, response: Response) -> User:
    token = request.cookies.get(settings.cookie_refresh_name)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh session required")
    payload = decode_token(token, "refresh")
    try:
        user_id = uuid.UUID(payload["sub"])
        session_id = uuid.UUID(payload["sid"])
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh session") from exc

    session = db.get(RefreshSession, session_id)
    now = utcnow()
    if not session or session.user_id != user_id or session.revoked_at or session.expires_at <= now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh session is inactive")

    header = request.headers.get("x-csrf-token")
    cookie = request.cookies.get(settings.cookie_csrf_name)
    if not header or not cookie or header != cookie or not verify_csrf(header, session.csrf_hash):
        write_audit(db, request, "auth.refresh.csrf_failed", success=False, resource_type="session", resource_id=session.id)
        db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed")

    incoming_jti = payload.get("jti", "")
    if sha256_hex(incoming_jti) != session.refresh_jti_hash:
        session.revoked_at = now
        write_audit(
            db,
            request,
            "auth.refresh.reuse_detected",
            success=False,
            resource_type="session",
            resource_id=session.id,
            message="Refresh token reuse detected; session revoked",
        )
        db.commit()
        clear_auth_cookies(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh session is inactive")

    user = db.get(User, user_id)
    if not user or not user.is_active:
        session.revoked_at = now
        db.commit()
        clear_auth_cookies(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="The account is inactive")

    new_jti = random_token(32)
    new_csrf = new_csrf_token()
    session.refresh_jti_hash = sha256_hex(new_jti)
    session.csrf_hash = sha256_hex(new_csrf)
    session.last_used_at = now
    access_token = create_access_token(user.id, session.id, user.role.value)
    refresh_token = create_refresh_token(user.id, session.id, new_jti, session.expires_at)
    write_audit(db, request, "auth.refresh.success", actor=user, resource_type="session", resource_id=session.id)
    db.commit()
    set_auth_cookies(response, access_token, refresh_token, new_csrf)
    return user


def revoke_current_session(db: Session, request: Request, response: Response, user: User) -> None:
    session_id = request.state.session_id if isinstance(request.state.session_id, uuid.UUID) else uuid.UUID(str(request.state.session_id))
    session = db.get(RefreshSession, session_id)
    if session and not session.revoked_at:
        session.revoked_at = utcnow()
    write_audit(db, request, "auth.logout", actor=user, resource_type="session", resource_id=session_id)
    db.commit()
    clear_auth_cookies(response)


def change_own_password(db: Session, request: Request, user: User, current_password: str, new_password: str) -> None:
    valid, _ = verify_password(current_password, user.password_hash)
    if not valid:
        write_audit(db, request, "auth.password_change.failed", actor=user, success=False, message="Current password does not match")
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    try:
        validate_password_policy(new_password, user.email)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    user.password_hash = hash_password(new_password)
    user.password_changed_at = utcnow()
    db.execute(
        update(RefreshSession)
        .where(RefreshSession.user_id == user.id, RefreshSession.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )
    write_audit(db, request, "auth.password_change.success", actor=user, resource_type="user", resource_id=user.id)
    db.commit()
