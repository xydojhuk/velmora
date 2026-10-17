import uuid
from datetime import timedelta
from typing import Any

from fastapi import HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AuditLog, User
from app.utils import clean_text, get_client_ip, get_user_agent, utcnow


def write_audit(
    db: Session,
    request: Request | None,
    action: str,
    *,
    actor: User | None = None,
    success: bool = True,
    resource_type: str | None = None,
    resource_id: str | uuid.UUID | None = None,
    message: str | None = None,
    details: dict[str, Any] | None = None,
    client_ip: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    log = AuditLog(
        actor_user_id=actor.id if actor else None,
        actor_email=actor.email if actor else None,
        action=action[:120],
        resource_type=resource_type[:80] if resource_type else None,
        resource_id=str(resource_id)[:120] if resource_id is not None else None,
        success=success,
        message=clean_text(message)[:500] if message else None,
        details=details or {},
        client_ip=client_ip if client_ip is not None else (get_client_ip(request) if request else None),
        user_agent=user_agent if user_agent is not None else (get_user_agent(request) if request else None),
        request_id=getattr(request.state, "request_id", None) if request else None,
        method=request.method if request else None,
        path=str(request.url.path)[:500] if request else None,
    )
    db.add(log)
    return log


def enforce_rate_limit(
    db: Session,
    *,
    action_prefix: str,
    client_ip: str | None,
    limit: int,
    window_minutes: int,
) -> None:
    if not client_ip:
        return
    since = utcnow() - timedelta(minutes=window_minutes)
    count = db.scalar(
        select(func.count(AuditLog.id)).where(
            AuditLog.client_ip == client_ip,
            AuditLog.created_at >= since,
            AuditLog.action.like(f"{action_prefix}%"),
        )
    )
    if count and count >= limit:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests. Try again later")
