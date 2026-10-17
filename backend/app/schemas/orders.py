import uuid
from datetime import datetime

from pydantic import EmailStr, Field, field_validator

from app.enums import OrderStatus, PaymentStatus
from app.schemas.common import CleanTextModel, ORMModel, validate_slug


class PublicOrderItemCreate(CleanTextModel):
    product_slug: str = Field(min_length=2, max_length=120)
    quantity: int = Field(ge=1, le=99)

    @field_validator("product_slug")
    @classmethod
    def slug_valid(cls, value: str) -> str:
        return validate_slug(value)


class PublicOrderCreate(CleanTextModel):
    customer_name: str = Field(min_length=2, max_length=160)
    customer_phone: str = Field(min_length=5, max_length=32)
    customer_email: EmailStr | None = None
    items: list[PublicOrderItemCreate] = Field(min_length=1, max_length=20)
    shipping_method: str | None = Field(default=None, max_length=120)
    shipping_city: str | None = Field(default=None, max_length=160)
    shipping_address: str | None = Field(default=None, max_length=300)
    shipping_branch: str | None = Field(default=None, max_length=160)
    payment_method: str | None = Field(default=None, max_length=120)
    customer_note: str | None = Field(default=None, max_length=2000)
    website: str | None = Field(default=None, max_length=200)


class AdminOrderCreate(CleanTextModel):
    customer_name: str = Field(min_length=2, max_length=160)
    customer_phone: str = Field(min_length=5, max_length=32)
    customer_email: EmailStr | None = None
    items: list[PublicOrderItemCreate] = Field(min_length=1, max_length=20)
    shipping_method: str | None = Field(default=None, max_length=120)
    shipping_city: str | None = Field(default=None, max_length=160)
    shipping_address: str | None = Field(default=None, max_length=300)
    shipping_branch: str | None = Field(default=None, max_length=160)
    shipping_carrier: str | None = Field(default=None, max_length=120)
    payment_method: str | None = Field(default=None, max_length=120)
    customer_note: str | None = Field(default=None, max_length=2000)
    admin_note: str | None = Field(default=None, max_length=5000)
    discount_minor: int = Field(default=0, ge=0, le=2_000_000_000)
    shipping_minor: int = Field(default=0, ge=0, le=2_000_000_000)
    source: str = Field(default="manual", min_length=2, max_length=80)
    status: OrderStatus = OrderStatus.NEW
    payment_status: PaymentStatus = PaymentStatus.UNPAID


class PublicOrderCreated(CleanTextModel):
    order_number: str
    status: OrderStatus
    total_minor: int
    currency: str


class OrderItemRead(ORMModel):
    id: uuid.UUID
    product_id: uuid.UUID | None
    product_slug: str
    sku: str
    title: str
    unit_price_minor: int
    quantity: int
    line_total_minor: int
    snapshot: dict


class OrderRead(ORMModel):
    id: uuid.UUID
    order_number: str
    status: OrderStatus
    payment_status: PaymentStatus
    customer_name: str
    customer_phone: str
    customer_email: EmailStr | None
    shipping_method: str | None
    shipping_city: str | None
    shipping_address: str | None
    shipping_branch: str | None
    shipping_carrier: str | None
    tracking_number: str | None
    payment_method: str | None
    customer_note: str | None
    admin_note: str | None
    subtotal_minor: int
    discount_minor: int
    shipping_minor: int
    total_minor: int
    currency: str
    source: str
    assigned_to_id: uuid.UUID | None
    paid_at: datetime | None
    shipped_at: datetime | None
    completed_at: datetime | None
    version: int
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemRead]


class OrderHistoryRead(ORMModel):
    id: uuid.UUID
    from_status: OrderStatus | None
    to_status: OrderStatus
    changed_by_id: uuid.UUID | None
    note: str | None
    created_at: datetime


class OrderDetailRead(OrderRead):
    history: list[OrderHistoryRead]


class OrderUpdate(CleanTextModel):
    status: OrderStatus | None = None
    payment_status: PaymentStatus | None = None
    customer_name: str | None = Field(default=None, min_length=2, max_length=160)
    customer_phone: str | None = Field(default=None, min_length=5, max_length=32)
    customer_email: EmailStr | None = None
    source: str | None = Field(default=None, min_length=2, max_length=80)
    shipping_method: str | None = Field(default=None, max_length=120)
    shipping_city: str | None = Field(default=None, max_length=160)
    shipping_address: str | None = Field(default=None, max_length=300)
    shipping_branch: str | None = Field(default=None, max_length=160)
    shipping_carrier: str | None = Field(default=None, max_length=120)
    tracking_number: str | None = Field(default=None, max_length=120)
    payment_method: str | None = Field(default=None, max_length=120)
    customer_note: str | None = Field(default=None, max_length=2000)
    admin_note: str | None = Field(default=None, max_length=5000)
    discount_minor: int | None = Field(default=None, ge=0, le=2_000_000_000)
    shipping_minor: int | None = Field(default=None, ge=0, le=2_000_000_000)
    assigned_to_id: uuid.UUID | None = None
    version: int = Field(ge=1)
    status_note: str | None = Field(default=None, max_length=500)


class OrderList(CleanTextModel):
    items: list[OrderRead]
    total: int
    page: int
    size: int
