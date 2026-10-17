"""Catalog categories have stable slugs and editable presentation metadata."""
from datetime import datetime
from pydantic import Field, field_validator
from app.schemas.common import CleanTextModel, ORMModel, validate_slug


class CategoryCreate(CleanTextModel):
    slug: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=100)
    description: str = Field(default="", max_length=500)
    is_active: bool = True
    sort_order: int = Field(default=0, ge=-100000, le=100000)

    @field_validator("slug")
    @classmethod
    def safe_slug(cls, value: str) -> str:
        return validate_slug(value)


class CategoryUpdate(CleanTextModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None
    sort_order: int | None = Field(default=None, ge=-100000, le=100000)


class CategoryRead(ORMModel):
    slug: str
    name: str
    description: str
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime
