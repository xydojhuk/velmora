from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.schemas.orders import OrderRead


class CustomerSummary(BaseModel):
    name: str
    phone: str
    email: EmailStr | None
    orders_count: int
    total_spent_minor: int
    last_order_at: datetime


class CustomerList(BaseModel):
    items: list[CustomerSummary]
    total: int
    page: int
    size: int


class CustomerDetail(CustomerSummary):
    orders: list[OrderRead]
