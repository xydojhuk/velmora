from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.dependencies import require_staff_read
from app.enums import PaymentStatus
from app.models import Order, User
from app.schemas.customers import CustomerDetail, CustomerList, CustomerSummary


router = APIRouter(prefix="/admin/customers", tags=["admin-customers"])


def _customer_query(search: str | None):
    query = select(
        Order.customer_phone.label("phone"),
        func.max(Order.customer_name).label("name"),
        func.max(Order.customer_email).label("email"),
        func.count(Order.id).label("orders_count"),
        func.coalesce(func.sum(case((Order.payment_status == PaymentStatus.PAID, Order.total_minor), else_=0)), 0).label("total_spent_minor"),
        func.max(Order.created_at).label("last_order_at"),
    ).group_by(Order.customer_phone)
    if search:
        term = f"%{search.strip()}%"
        query = query.where(or_(Order.customer_name.ilike(term), Order.customer_phone.ilike(term), Order.customer_email.ilike(term)))
    return query


@router.get("", response_model=CustomerList)
def list_customers(
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    search: str | None = Query(default=None, max_length=160),
    _: User = Depends(require_staff_read),
    db: Session = Depends(get_db),
):
    base = _customer_query(search).subquery()
    total = db.scalar(select(func.count()).select_from(base)) or 0
    rows = db.execute(
        select(base).order_by(base.c.last_order_at.desc()).offset((page - 1) * size).limit(size)
    ).mappings().all()
    items = [CustomerSummary(**dict(row)) for row in rows]
    return CustomerList(items=items, total=int(total), page=page, size=size)


@router.get("/{phone:path}", response_model=CustomerDetail)
def customer_detail(phone: str, _: User = Depends(require_staff_read), db: Session = Depends(get_db)):
    orders = db.scalars(
        select(Order).options(selectinload(Order.items)).where(Order.customer_phone == phone).order_by(Order.created_at.desc())
    ).all()
    if not orders:
        raise HTTPException(status_code=404, detail="Customer not found")
    latest = orders[0]
    spent = sum(order.total_minor for order in orders if order.payment_status == PaymentStatus.PAID)
    return CustomerDetail(
        name=latest.customer_name,
        phone=latest.customer_phone,
        email=latest.customer_email,
        orders_count=len(orders),
        total_spent_minor=spent,
        last_order_at=latest.created_at,
        orders=orders,
    )
