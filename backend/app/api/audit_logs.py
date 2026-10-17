import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin_read
from app.models import AuditLog, User
from app.schemas.audit import AuditLogList


router = APIRouter(prefix="/admin/logs", tags=["admin-logs"])


@router.get("", response_model=AuditLogList)
def list_logs(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    action: str | None = Query(default=None, max_length=120),
    client_ip: str | None = Query(default=None, max_length=45),
    actor_user_id: uuid.UUID | None = None,
    resource_type: str | None = Query(default=None, max_length=80),
    resource_id: str | None = Query(default=None, max_length=120),
    request_id: str | None = Query(default=None, max_length=64),
    success: bool | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    _: User = Depends(require_admin_read),
    db: Session = Depends(get_db),
):
    filters = []
    if action:
        filters.append(AuditLog.action.ilike(f"%{action.strip()}%"))
    if client_ip:
        filters.append(AuditLog.client_ip == client_ip.strip())
    if actor_user_id:
        filters.append(AuditLog.actor_user_id == actor_user_id)
    if resource_type:
        filters.append(AuditLog.resource_type == resource_type.strip())
    if resource_id:
        filters.append(AuditLog.resource_id == resource_id.strip())
    if request_id:
        filters.append(AuditLog.request_id == request_id.strip())
    if success is not None:
        filters.append(AuditLog.success == success)
    if date_from:
        filters.append(AuditLog.created_at >= date_from)
    if date_to:
        filters.append(AuditLog.created_at <= date_to)
    total = db.scalar(select(func.count(AuditLog.id)).where(*filters)) or 0
    items = db.scalars(
        select(AuditLog)
        .where(*filters)
        .order_by(AuditLog.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).all()
    return AuditLogList(items=items, total=total, page=page, size=size)
