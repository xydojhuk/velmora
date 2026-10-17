import re
from fastapi import Query, APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.audit import enforce_rate_limit, write_audit
from app.config import settings
from app.database import SessionLocal, get_db
from app.models import IconAsset, Product
from app.schemas.icons import PublicIconAsset
from app.schemas.orders import PublicOrderCreate, PublicOrderCreated
from app.schemas.products import PublicProductRead
from app.schemas.public import VisitCreate
from app.schemas.settings import PublicStoreConfig
from app.services.notifications import dispatch_order_notifications
from app.services.orders import create_public_order
from app.services.store import active_payment_methods, active_shipping_methods, get_or_create_store_settings
from app.utils import get_client_ip


router = APIRouter(prefix="/public", tags=["public"])


def _notify_order(order_id) -> None:
    from app.models import Order
    from sqlalchemy import or_, select
    from sqlalchemy.orm import selectinload

    with SessionLocal() as db:
        order = db.scalar(select(Order).options(selectinload(Order.items)).where(Order.id == order_id))
        if order:
            dispatch_order_notifications(db, order)


@router.get("/config", response_model=PublicStoreConfig)
def public_config(db: Session = Depends(get_db)):
    config = get_or_create_store_settings(db)
    shipping = active_shipping_methods(db)
    payment = active_payment_methods(db)
    icons = db.scalars(select(IconAsset).order_by(IconAsset.label.asc(), IconAsset.created_at.asc())).all()
    db.commit()
    return PublicStoreConfig(
        store_name=config.store_name,
        brand_tagline=config.brand_tagline,
        footer_description=config.footer_description,
        phone=config.phone,
        email=config.email,
        working_hours=config.working_hours,
        business_hours=config.business_hours,
        timezone=config.timezone,
        service_region=config.service_region,
        storefront=config.storefront,
        seo_title=config.seo_title,
        seo_description=config.seo_description,
        seo_og_image=config.seo_og_image,
        maintenance_mode=config.maintenance_mode,
        maintenance_title=config.maintenance_title,
        maintenance_message=config.maintenance_message,
        orders_enabled=config.orders_enabled,
        shipping_methods=shipping,
        payment_methods=payment,
        icons=icons,
    )


@router.get("/icons", response_model=list[PublicIconAsset])
def public_icons(db: Session = Depends(get_db)):
    return db.scalars(select(IconAsset).order_by(IconAsset.label.asc(), IconAsset.created_at.asc())).all()


@router.get("/products", response_model=list[PublicProductRead])
def public_products(
    q: str | None = Query(default=None, max_length=120),
    category: str | None = Query(default=None, min_length=1, max_length=80, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"),
    available: bool = False,
    db: Session = Depends(get_db),
):
    query = select(Product).where(Product.is_active.is_(True))
    if q and q.strip():
        term = "%" + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        query = query.where(or_(Product.title.ilike(term, escape="\\"), Product.sku.ilike(term, escape="\\"), Product.short_description.ilike(term, escape="\\")))
    if category:
        query = query.where(Product.category_slug == category)
    if available:
        query = query.where(or_(Product.track_inventory.is_(False), Product.stock_quantity > 0))
    return db.scalars(query.order_by(Product.sort_order.asc(), Product.created_at.asc())).all()


@router.get("/products/{slug}", response_model=PublicProductRead)
def public_product(slug: str, db: Session = Depends(get_db)):
    product = db.scalar(select(Product).where(Product.slug == slug, Product.is_active.is_(True)))
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.post("/orders", response_model=PublicOrderCreated, status_code=201)
def public_order(
    payload: PublicOrderCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    if idempotency_key:
        idempotency_key = idempotency_key.strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]{16,120}", idempotency_key):
            raise HTTPException(status_code=422, detail="Idempotency key must contain 16–120 letters, digits, hyphens or underscores")
    order, created = create_public_order(db, request, payload, idempotency_key)
    if created:
        background_tasks.add_task(_notify_order, order.id)
    return PublicOrderCreated(order_number=order.order_number, status=order.status, total_minor=order.total_minor, currency=order.currency)


@router.post("/visit", status_code=204)
def register_visit(payload: VisitCreate, request: Request, db: Session = Depends(get_db)):
    client_ip = get_client_ip(request)
    enforce_rate_limit(
        db,
        action_prefix="public.page_visit",
        client_ip=client_ip,
        limit=settings.visit_ip_limit,
        window_minutes=settings.visit_ip_window_minutes,
    )
    write_audit(
        db,
        request,
        "public.page_visit",
        resource_type="page",
        resource_id=payload.page,
        details={"referrer": payload.referrer, "session_id": payload.session_id},
    )
    db.commit()
    return None
