import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from app.enums import UserRole
from app.schemas.common import CleanTextModel, ORMModel


class UserCreate(CleanTextModel):
    email: EmailStr
    display_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=12, max_length=128)
    role: UserRole = UserRole.MODERATOR


class UserUpdate(CleanTextModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=120)
    role: UserRole | None = None
    is_active: bool | None = None


class UserPasswordReset(CleanTextModel):
    new_password: str = Field(min_length=12, max_length=128)


class UserRead(ORMModel):
    id: uuid.UUID
    email: str
    display_name: str
    role: UserRole
    is_active: bool
    failed_login_attempts: int
    locked_until: datetime | None
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime

class UserList(CleanTextModel):
    items: list[UserRead]
    total: int
    page: int
    size: int
