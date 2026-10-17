from datetime import date, datetime

from pydantic import BaseModel


class AnalyticsSummary(BaseModel):
    period_days: int
    total_orders: int
    orders_today: int
    new_orders: int
    processing_orders: int
    unpaid_orders: int
    shipped_without_tracking: int
    paid_revenue_minor: int
    revenue_today_minor: int
    average_order_minor: int
    cancelled_orders: int
    active_products: int
    inactive_products: int
    unique_customers: int


class SalesPoint(BaseModel):
    date: date
    orders: int
    revenue_minor: int


class StatusPoint(BaseModel):
    status: str
    count: int


class SourcePoint(BaseModel):
    source: str
    count: int


class TopProduct(BaseModel):
    product_slug: str
    title: str
    quantity: int
    revenue_minor: int


class RecentOrder(BaseModel):
    id: str
    order_number: str
    customer_name: str
    total_minor: int
    currency: str
    status: str
    payment_status: str
    source: str
    created_at: datetime


class DashboardAnalytics(BaseModel):
    summary: AnalyticsSummary
    sales: list[SalesPoint]
    statuses: list[StatusPoint]
    sources: list[SourcePoint]
    top_products: list[TopProduct]
    recent_orders: list[RecentOrder]
