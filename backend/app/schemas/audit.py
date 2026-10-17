import uuid
from datetime import datetime
from typing import Any

from app.schemas.common import ORMModel


class AuditLogRead(ORMModel):
    id: uuid.UUID
    created_at: datetime
    actor_user_id: uuid.UUID | None
    actor_email: str | None
    action: str
    resource_type: str | None
    resource_id: str | None
    success: bool
    message: str | None
    details: dict[str, Any]
    client_ip: str | None
    user_agent: str | None
    request_id: str | None
    method: str | None
    path: str | None

from pydantic import BaseModel


class AuditLogList(BaseModel):
    items: list[AuditLogRead]
    total: int
    page: int
    size: int
