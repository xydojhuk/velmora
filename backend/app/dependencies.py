import uuid

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.enums import UserRole
from app.models import RefreshSession, User
from app.security import decode_token, verify_csrf
from app.utils import utcnow


def _uuid(value, message: str = "Invalid session") -> uuid.UUID:
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message) from exc


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(settings.cookie_access_name)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    payload = decode_token(token, "access")
    user_id = _uuid(payload.get("sub"))
    session_id = _uuid(payload.get("sid"))
    session = db.get(RefreshSession, session_id)
    now = utcnow()
    if not session or session.user_id != user_id or session.revoked_at or session.expires_at <= now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="The session is inactive")
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="The account is inactive")
    request.state.actor_id = user.id
    request.state.actor_email = user.email
    request.state.session_id = session.id
    return user


def require_csrf(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
    session_id = _uuid(getattr(request.state, "session_id", None))
    session = db.get(RefreshSession, session_id)
    header = request.headers.get("x-csrf-token")
    cookie = request.cookies.get(settings.cookie_csrf_name)
    if not session or not header or not cookie or header != cookie or not verify_csrf(header, session.csrf_hash):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed")
    return user


def require_admin(user: User = Depends(require_csrf)) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator permissions required")
    return user


def require_staff(user: User = Depends(require_csrf)) -> User:
    if user.role not in {UserRole.ADMIN, UserRole.MODERATOR}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Staff permissions required")
    return user


def require_admin_read(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator permissions required")
    return user


def require_staff_read(user: User = Depends(get_current_user)) -> User:
    if user.role not in {UserRole.ADMIN, UserRole.MODERATOR}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Staff permissions required")
    return user
