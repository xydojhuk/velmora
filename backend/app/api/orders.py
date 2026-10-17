import uuid
from fastapi.responses import Response
from app.services.csv_export import export_csv

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.database import SessionLocal, get_db
from app.dependencies import require_staff, require_staff_read
from app.enums import OrderStatus, PaymentStatus
from app.models import Order, User
from app.schemas.orders import AdminOrderCreate, OrderDetailRead, OrderList, OrderUpdate
from app.services.notifications import dispatch_order_notifications
from app.services.orders import create_admin_order, update_order


router = APIRouter(prefix="/admin/orders", tags=["admin-orders"])


def _notify_order(order_id) -> None:
    with SessionLocal() as db:
        order = db.scalar(select(Order).options(selectinload(Order.items)).where(Order.id == order_id))
        if order:
            dispatch_order_notifications(db, order)


@router.get("", response_model=OrderList)
def list_orders(
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    search: str | None = Query(default=None, max_length=160),
    order_status: OrderStatus | None = Query(default=None, alias="status"),
    payment_status: PaymentStatus | None = None,
    source: str | None = Query(default=None, max_length=80),
    assigned_to_id: uuid.UUID | None = None,
    _: User = Depends(require_staff_read),
    db: Session = Depends(get_db),
):
    filters = []
    if search:
        term = f"%{search.strip()}%"
        filters.append(or_(Order.order_number.ilike(term), Order.customer_name.ilike(term), Order.customer_phone.ilike(term), Order.customer_email.ilike(term), Order.tracking_number.ilike(term)))
    if order_status is not None:
        filters.append(Order.status == order_status)
    if payment_status is not None:
        filters.append(Order.payment_status == payment_status)
    if source:
        filters.append(Order.source == source.strip())
    if assigned_to_id is not None:
        filters.append(Order.assigned_to_id == assigned_to_id)
    total = db.scalar(select(func.count(Order.id)).where(*filters)) or 0
    items = db.scalars(
        select(Order).options(selectinload(Order.items)).where(*filters).order_by(Order.created_at.desc()).offset((page - 1) * size).limit(size)
    ).all()
    return OrderList(items=items, total=total, page=page, size=size)


@router.get("/export.csv")
def export_orders(
    _: User = Depends(require_staff_read),
    db: Session = Depends(get_db),
):
    # Export is bounded: large stores should eventually use streaming jobs.
    orders = db.scalars(select(Order).order_by(Order.created_at.desc()).limit(20000)).all()
    rows = [(
        order.order_number, order.created_at.isoformat(), order.status.value,
        order.customer_name, order.customer_phone, order.customer_email,
        order.total_minor, order.currency, order.payment_status.value,
    ) for order in orders]
    content = export_csv(("order_number", "created_at", "status", "customer_name", "phone", "email", "total_minor", "currency", "payment_status"), rows)
    return Response(content, media_type="text/csv; charset=utf-8", headers={"Content-Disposition": 'attachment; filename="velmora-orders.csv"', "Cache-Control":"no-store"})


@router.post("", response_model=OrderDetailRead, status_code=201)
def admin_create_order(
    payload: AdminOrderCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    actor: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    order = create_admin_order(db, request, actor, payload)
    background_tasks.add_task(_notify_order, order.id)
    return order


@router.get("/{order_id}", response_model=OrderDetailRead)
def get_order(order_id: uuid.UUID, _: User = Depends(require_staff_read), db: Session = Depends(get_db)):
    order = db.scalar(select(Order).options(selectinload(Order.items), selectinload(Order.history)).where(Order.id == order_id))
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.patch("/{order_id}", response_model=OrderDetailRead)
def patch_order(
    order_id: uuid.UUID,
    payload: OrderUpdate,
    request: Request,
    actor: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return update_order(db, request, actor, order, payload.model_dump(exclude_unset=True))
