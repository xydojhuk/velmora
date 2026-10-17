import uuid

from pydantic import BaseModel, Field, field_validator

from app.enums import UserRole
from app.schemas.common import ORMModel
from app.utils import clean_text


class LoginRequest(BaseModel):
    # Login accepts bootstrap/local addresses such as admin@velmora.local.
    # Account creation can still enforce EmailStr for normal production users.
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        return clean_text(value) if isinstance(value, str) else value


class AuthUser(ORMModel):
    id: uuid.UUID
    email: str
    display_name: str
    role: UserRole
    is_active: bool


class LoginResponse(BaseModel):
    user: AuthUser


class ChangePasswordRequest(BaseModel):
    # Password values must be preserved exactly; do not run CleanTextModel's
    # whitespace trimming on authentication secrets.
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)
