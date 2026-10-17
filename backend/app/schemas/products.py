import uuid
from datetime import datetime
from typing import Any

from pydantic import Field, field_validator

from app.schemas.common import CleanTextModel, ORMModel, validate_slug


class Metric(CleanTextModel):
    icon: str = Field(min_length=1, max_length=60, pattern=r"^[a-z0-9][a-z0-9-]{0,59}$")
    label: str = Field(min_length=1, max_length=120)
    value: str = Field(min_length=1, max_length=180)


class Feature(CleanTextModel):
    icon: str = Field(min_length=1, max_length=60, pattern=r"^[a-z0-9][a-z0-9-]{0,59}$")
    text: str = Field(min_length=1, max_length=240)


class Specification(CleanTextModel):
    label: str = Field(min_length=1, max_length=160)
    value: str = Field(min_length=1, max_length=400)
    group: str | None = Field(default=None, max_length=100)


class ProductBase(CleanTextModel):
    slug: str = Field(min_length=2, max_length=120)
    sku: str = Field(min_length=1, max_length=120)
    model: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=160)
    title: str = Field(min_length=1, max_length=240)
    subtitle: str = Field(default="", max_length=300)
    short_description: str = Field(default="", max_length=1800)
    description_title: str = Field(default="", max_length=240)
    description_paragraphs: list[str] = Field(default_factory=list, max_length=12)
    price_minor: int = Field(ge=0, le=2_000_000_000)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    is_active: bool = True
    category_slug: str = Field(default="general", pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=80)
    track_inventory: bool = False
    stock_quantity: int = Field(default=0, ge=0, le=2_000_000_000)
    low_stock_threshold: int = Field(default=5, ge=0, le=2_000_000_000)
    catalog_metrics: list[Metric] = Field(default_factory=list, max_length=20)
    summary_features: list[Feature] = Field(default_factory=list, max_length=20)
    specifications: list[Specification] = Field(default_factory=list, max_length=100)
    extra: dict[str, Any] = Field(default_factory=dict)
    sort_order: int = Field(default=0, ge=-100000, le=100000)

    @field_validator("slug")
    @classmethod
    def slug_valid(cls, value: str) -> str:
        return validate_slug(value)

    @field_validator("currency")
    @classmethod
    def currency_upper(cls, value: str) -> str:
        return value.upper()

    @field_validator("description_paragraphs")
    @classmethod
    def paragraph_lengths(cls, value: list[str]) -> list[str]:
        if any(len(item) > 3000 for item in value):
            raise ValueError("Each paragraph must contain no more than 3000 characters")
        return value

class ProductCreate(ProductBase):
    pass


class ProductUpdate(CleanTextModel):
    slug: str | None = Field(default=None, min_length=2, max_length=120)
    sku: str | None = Field(default=None, min_length=1, max_length=120)
    model: str | None = Field(default=None, min_length=1, max_length=120)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    title: str | None = Field(default=None, min_length=1, max_length=240)
    subtitle: str | None = Field(default=None, max_length=300)
    short_description: str | None = Field(default=None, max_length=1800)
    description_title: str | None = Field(default=None, max_length=240)
    description_paragraphs: list[str] | None = Field(default=None, max_length=12)
    price_minor: int | None = Field(default=None, ge=0, le=2_000_000_000)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    is_active: bool | None = None
    category_slug: str | None = Field(default=None, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=80)
    track_inventory: bool | None = None
    stock_quantity: int | None = Field(default=None, ge=0, le=2_000_000_000)
    low_stock_threshold: int | None = Field(default=None, ge=0, le=2_000_000_000)
    catalog_metrics: list[Metric] | None = Field(default=None, max_length=20)
    summary_features: list[Feature] | None = Field(default=None, max_length=20)
    specifications: list[Specification] | None = Field(default=None, max_length=100)
    extra: dict[str, Any] | None = None
    sort_order: int | None = Field(default=None, ge=-100000, le=100000)

    @field_validator("slug")
    @classmethod
    def slug_valid(cls, value: str | None) -> str | None:
        return validate_slug(value) if value is not None else None

    @field_validator("currency")
    @classmethod
    def currency_upper(cls, value: str | None) -> str | None:
        return value.upper() if value else value

    @field_validator("description_paragraphs")
    @classmethod
    def paragraph_lengths(cls, value: list[str] | None) -> list[str] | None:
        if value and any(len(item) > 3000 for item in value):
            raise ValueError("Each paragraph must contain no more than 3000 characters")
        return value




class ProductImageRead(ORMModel):
    id: uuid.UUID
    url: str
    original_name: str
    mime_type: str
    size_bytes: int
    width: int
    height: int
    alt_text: str
    sort_order: int
    created_at: datetime


class ProductImageOrder(CleanTextModel):
    image_ids: list[uuid.UUID] = Field(min_length=1, max_length=4)

class ProductRead(ORMModel):
    id: uuid.UUID
    slug: str
    sku: str
    model: str
    name: str
    title: str
    subtitle: str
    short_description: str
    description_title: str
    description_paragraphs: list[str]
    price_minor: int
    currency: str
    is_active: bool
    category_slug: str
    track_inventory: bool
    stock_quantity: int
    low_stock_threshold: int
    images: list[ProductImageRead]
    primary_image: str
    gallery: list[str]
    catalog_metrics: list[dict[str, Any]]
    summary_features: list[dict[str, Any]]
    specifications: list[dict[str, Any]]
    extra: dict[str, Any]
    sort_order: int
    created_at: datetime
    updated_at: datetime


class PublicProductRead(ProductRead):
    pass

class ProductList(CleanTextModel):
    items: list[ProductRead]
    total: int
    page: int
    size: int
