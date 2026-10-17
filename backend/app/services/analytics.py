from datetime import timedelta

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.enums import OrderStatus, PaymentStatus
from app.models import Order, OrderItem, Product
from app.schemas.analytics import AnalyticsSummary, DashboardAnalytics, RecentOrder, SalesPoint, SourcePoint, StatusPoint, TopProduct
from app.utils import utcnow


def build_dashboard(db: Session, days: int) -> DashboardAnalytics:
    now = utcnow()
    since = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    today = now.date()
    total_orders = db.scalar(select(func.count(Order.id)).where(Order.created_at >= since)) or 0
    orders_today = db.scalar(select(func.count(Order.id)).where(func.date(Order.created_at) == today)) or 0
    new_orders = db.scalar(select(func.count(Order.id)).where(Order.status == OrderStatus.NEW)) or 0
    processing_orders = db.scalar(select(func.count(Order.id)).where(Order.status == OrderStatus.PROCESSING)) or 0
    unpaid_orders = db.scalar(select(func.count(Order.id)).where(Order.payment_status.in_([PaymentStatus.UNPAID, PaymentStatus.PENDING]), Order.status.notin_([OrderStatus.CANCELLED, OrderStatus.RETURNED]))) or 0
    shipped_without_tracking = db.scalar(select(func.count(Order.id)).where(Order.status == OrderStatus.SHIPPED, (Order.tracking_number.is_(None)) | (Order.tracking_number == ""))) or 0
    paid_revenue = db.scalar(select(func.coalesce(func.sum(Order.total_minor), 0)).where(Order.payment_status == PaymentStatus.PAID, Order.paid_at >= since)) or 0
    revenue_today = db.scalar(select(func.coalesce(func.sum(Order.total_minor), 0)).where(Order.payment_status == PaymentStatus.PAID, func.date(Order.paid_at) == today)) or 0
    paid_count = db.scalar(select(func.count(Order.id)).where(Order.payment_status == PaymentStatus.PAID, Order.paid_at >= since)) or 0
    cancelled_orders = db.scalar(select(func.count(Order.id)).where(Order.status == OrderStatus.CANCELLED, Order.created_at >= since)) or 0
    active_products = db.scalar(select(func.count(Product.id)).where(Product.is_active.is_(True))) or 0
    inactive_products = db.scalar(select(func.count(Product.id)).where(Product.is_active.is_(False))) or 0
    unique_customers = db.scalar(select(func.count(distinct(Order.customer_phone)))) or 0

    order_rows = db.execute(select(func.date(Order.created_at), func.count(Order.id)).where(Order.created_at >= since).group_by(func.date(Order.created_at))).all()
    revenue_rows = db.execute(select(func.date(Order.paid_at), func.coalesce(func.sum(Order.total_minor), 0)).where(Order.payment_status == PaymentStatus.PAID, Order.paid_at >= since).group_by(func.date(Order.paid_at))).all()
    orders_by_day = {row[0]: int(row[1]) for row in order_rows}
    revenue_by_day = {row[0]: int(row[1]) for row in revenue_rows}
    sales = []
    for offset in range(days):
        day = (since + timedelta(days=offset)).date()
        sales.append(SalesPoint(date=day, orders=orders_by_day.get(day, 0), revenue_minor=revenue_by_day.get(day, 0)))

    status_rows = db.execute(select(Order.status, func.count(Order.id)).group_by(Order.status)).all()
    statuses = [StatusPoint(status=row[0].value, count=int(row[1])) for row in status_rows]
    source_rows = db.execute(select(Order.source, func.count(Order.id)).group_by(Order.source).order_by(func.count(Order.id).desc())).all()
    sources = [SourcePoint(source=row[0], count=int(row[1])) for row in source_rows]
    top_rows = db.execute(
        select(OrderItem.product_slug, OrderItem.title, func.sum(OrderItem.quantity), func.sum(OrderItem.line_total_minor))
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.payment_status == PaymentStatus.PAID, Order.paid_at >= since)
        .group_by(OrderItem.product_slug, OrderItem.title)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(10)
    ).all()
    top_products = [TopProduct(product_slug=row[0], title=row[1], quantity=int(row[2]), revenue_minor=int(row[3])) for row in top_rows]
    recent_rows = db.scalars(select(Order).order_by(Order.created_at.desc()).limit(8)).all()
    recent_orders = [
        RecentOrder(
            id=str(order.id),
            order_number=order.order_number,
            customer_name=order.customer_name,
            total_minor=order.total_minor,
            currency=order.currency,
            status=order.status.value,
            payment_status=order.payment_status.value,
            source=order.source,
            created_at=order.created_at,
        ) for order in recent_rows
    ]
    summary = AnalyticsSummary(
        period_days=days,
        total_orders=int(total_orders),
        orders_today=int(orders_today),
        new_orders=int(new_orders),
        processing_orders=int(processing_orders),
        unpaid_orders=int(unpaid_orders),
        shipped_without_tracking=int(shipped_without_tracking),
        paid_revenue_minor=int(paid_revenue),
        revenue_today_minor=int(revenue_today),
        average_order_minor=int(paid_revenue / paid_count) if paid_count else 0,
        cancelled_orders=int(cancelled_orders),
        active_products=int(active_products),
        inactive_products=int(inactive_products),
        unique_customers=int(unique_customers),
    )
    return DashboardAnalytics(summary=summary, sales=sales, statuses=statuses, sources=sources, top_products=top_products, recent_orders=recent_orders)
