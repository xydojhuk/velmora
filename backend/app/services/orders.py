import hashlib
import json

from fastapi import HTTPException, Request, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload

from app.audit import enforce_rate_limit, write_audit
from app.config import settings
from app.enums import OrderStatus, PaymentStatus
from app.models import Order, OrderItem, OrderStatusHistory, PaymentMethod, Product, ShippingMethod, User
from app.schemas.orders import AdminOrderCreate, PublicOrderCreate
from app.services.store import get_or_create_store_settings
from app.utils import get_client_ip, get_user_agent, new_order_number, utcnow


def _validate_fulfillment(db: Session, shipping_code: str | None, payment_code: str | None, payload):
    shipping = None
    payment = None
    shipping_price = 0
    if shipping_code:
        shipping = db.scalar(select(ShippingMethod).where(ShippingMethod.code == shipping_code, ShippingMethod.is_active.is_(True)))
        if not shipping:
            raise HTTPException(status_code=400, detail="The selected shipping method is unavailable")
        if shipping.requires_city and not payload.shipping_city:
            raise HTTPException(status_code=422, detail="The selected shipping method requires a city")
        if shipping.requires_branch and not payload.shipping_branch:
            raise HTTPException(status_code=422, detail="The selected shipping method requires a branch")
        if shipping.requires_address and not payload.shipping_address:
            raise HTTPException(status_code=422, detail="The selected shipping method requires an address")
        shipping_price = shipping.price_minor
    if payment_code:
        payment = db.scalar(select(PaymentMethod).where(PaymentMethod.code == payment_code, PaymentMethod.is_active.is_(True)))
        if not payment:
            raise HTTPException(status_code=400, detail="The selected payment method is unavailable")
    return shipping.code if shipping else None, payment.code if payment else None, shipping_price


def _build_items(db: Session, item_payloads, allow_inactive: bool = False) -> tuple[list[OrderItem], int, str]:
    slugs = list(dict.fromkeys(item.product_slug for item in item_payloads))
    # Lock products in stable order so concurrent orders cannot oversell tracked stock.
    query = select(Product).where(Product.slug.in_(slugs)).order_by(Product.id).with_for_update()
    if not allow_inactive:
        query = query.where(Product.is_active.is_(True))
    products = db.scalars(query).all()
    by_slug = {product.slug: product for product in products}
    if len(by_slug) != len(slugs):
        raise HTTPException(status_code=400, detail="One or more products are unavailable for ordering")
    quantities = {}
    for item in item_payloads:
        quantities[item.product_slug] = quantities.get(item.product_slug, 0) + item.quantity
    # Validate the entire basket before touching any inventory row.
    currencies = {by_slug[slug].currency for slug in slugs}
    if len(currencies) > 1:
        raise HTTPException(status_code=400, detail="An order cannot contain multiple currencies")
    for slug, requested in quantities.items():
        product = by_slug[slug]
        if product.track_inventory and product.stock_quantity < requested:
            raise HTTPException(status_code=409, detail=f"Insufficient stock for {product.title}")
    for slug, requested in quantities.items():
        product = by_slug[slug]
        if product.track_inventory:
            product.stock_quantity -= requested
    subtotal = 0
    rows = []
    currency = None
    for item in item_payloads:
        product = by_slug[item.product_slug]
        if currency is None:
            currency = product.currency
        if currency != product.currency:
            raise HTTPException(status_code=400, detail="An order cannot contain multiple currencies")
        line_total = product.price_minor * item.quantity
        subtotal += line_total
        rows.append(
            OrderItem(
                product_id=product.id,
                product_slug=product.slug,
                sku=product.sku,
                title=product.title,
                unit_price_minor=product.price_minor,
                quantity=item.quantity,
                line_total_minor=line_total,
                snapshot={
                    "slug": product.slug,
                    "sku": product.sku,
                    "model": product.model,
                    "name": product.name,
                    "title": product.title,
                    "price_minor": product.price_minor,
                    "currency": product.currency,
                    "primary_image": product.primary_image,
                    "inventory_reserved": bool(product.track_inventory),
                },
            )
        )
    return rows, subtotal, currency or "USD"


def _order_fingerprint(payload: PublicOrderCreate) -> str:
    """The same request key must not silently replay an unrelated basket."""
    normalized = json.dumps(payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _check_idempotency(existing: Order, fingerprint: str) -> None:
    if existing.idempotency_fingerprint != fingerprint:
        raise HTTPException(status_code=409, detail="Idempotency key belongs to a different order. Start a new checkout")


def create_public_order(db: Session, request: Request, payload: PublicOrderCreate, idempotency_key: str | None) -> tuple[Order, bool]:
    if payload.website:
        write_audit(db, request, "order.public.bot_rejected", success=False, message="Honeypot field was filled")
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request")
    config = get_or_create_store_settings(db)
    if not config.orders_enabled or config.maintenance_mode:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Orders are temporarily unavailable")
    client_ip = get_client_ip(request)
    fingerprint = _order_fingerprint(payload) if idempotency_key else None
    if idempotency_key:
        # Serialise retries under one key at PostgreSQL transaction scope.
        # Otherwise two workers could both decrement inventory before the unique
        # idempotency key constraint rejects the second commit.
        db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": idempotency_key})
        existing = db.scalar(select(Order).where(Order.idempotency_key == idempotency_key))
        if existing:
            _check_idempotency(existing, fingerprint)
            return existing, False
    enforce_rate_limit(
        db,
        action_prefix="order.public",
        client_ip=client_ip,
        limit=settings.order_ip_limit,
        window_minutes=settings.order_ip_window_minutes,
    )
    has_shipping = db.scalar(select(ShippingMethod.id).where(ShippingMethod.is_active.is_(True)).limit(1)) is not None
    has_payment = db.scalar(select(PaymentMethod.id).where(PaymentMethod.is_active.is_(True)).limit(1)) is not None
    if not has_shipping or not has_payment:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Checkout is temporarily unavailable")
    if not payload.shipping_method:
        raise HTTPException(status_code=422, detail="Choose a shipping method")
    if not payload.payment_method:
        raise HTTPException(status_code=422, detail="Choose a payment method")
    shipping_code, payment_code, shipping_price = _validate_fulfillment(db, payload.shipping_method, payload.payment_method, payload)
    item_rows, subtotal, currency = _build_items(db, payload.items)
    order = Order(
        order_number=new_order_number(),
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        customer_email=str(payload.customer_email) if payload.customer_email else None,
        shipping_method=shipping_code,
        shipping_city=payload.shipping_city,
        shipping_address=payload.shipping_address,
        shipping_branch=payload.shipping_branch,
        payment_method=payment_code,
        customer_note=payload.customer_note,
        subtotal_minor=subtotal,
        discount_minor=0,
        shipping_minor=shipping_price,
        total_minor=subtotal + shipping_price,
        currency=currency,
        source="website",
        idempotency_key=idempotency_key,
        idempotency_fingerprint=fingerprint,
        client_ip=client_ip,
        user_agent=get_user_agent(request),
    )
    order.items = item_rows
    db.add(order)
    db.flush()
    db.add(OrderStatusHistory(order_id=order.id, from_status=None, to_status=OrderStatus.NEW))
    write_audit(
        db,
        request,
        "order.public.created",
        resource_type="order",
        resource_id=order.id,
        details={"order_number": order.order_number, "items": len(item_rows), "total_minor": order.total_minor},
    )
    db.commit()
    return db.scalar(select(Order).options(selectinload(Order.items), selectinload(Order.history)).where(Order.id == order.id)), True


def create_admin_order(db: Session, request: Request, actor: User, payload: AdminOrderCreate) -> Order:
    if payload.status == OrderStatus.CANCELLED:
        raise HTTPException(status_code=422, detail="Cannot create an already-cancelled order")
    shipping_code, payment_code, _ = _validate_fulfillment(db, payload.shipping_method, payload.payment_method, payload)
    item_rows, subtotal, currency = _build_items(db, payload.items)
    total = max(0, subtotal - payload.discount_minor + payload.shipping_minor)
    now = utcnow()
    order = Order(
        order_number=new_order_number(),
        status=payload.status,
        payment_status=payload.payment_status,
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        customer_email=str(payload.customer_email) if payload.customer_email else None,
        shipping_method=shipping_code,
        shipping_city=payload.shipping_city,
        shipping_address=payload.shipping_address,
        shipping_branch=payload.shipping_branch,
        shipping_carrier=payload.shipping_carrier,
        payment_method=payment_code,
        customer_note=payload.customer_note,
        admin_note=payload.admin_note,
        subtotal_minor=subtotal,
        discount_minor=payload.discount_minor,
        shipping_minor=payload.shipping_minor,
        total_minor=total,
        currency=currency,
        source=payload.source,
        assigned_to_id=actor.id,
        paid_at=now if payload.payment_status == PaymentStatus.PAID else None,
        shipped_at=now if payload.status == OrderStatus.SHIPPED else None,
        completed_at=now if payload.status == OrderStatus.COMPLETED else None,
    )
    order.items = item_rows
    db.add(order)
    db.flush()
    db.add(OrderStatusHistory(order_id=order.id, from_status=None, to_status=order.status, changed_by_id=actor.id, note="Order created manually"))
    write_audit(
        db,
        request,
        "order.admin.created",
        actor=actor,
        resource_type="order",
        resource_id=order.id,
        details={"order_number": order.order_number, "source": order.source, "total_minor": order.total_minor},
    )
    db.commit()
    return db.scalar(select(Order).options(selectinload(Order.items), selectinload(Order.history)).where(Order.id == order.id))


def update_order(db: Session, request: Request, actor: User, order: Order, changes: dict) -> Order:
    # Defense in depth: serialize updates even when the service is called
    # without the admin route's existing SELECT ... FOR UPDATE.
    order = db.scalar(select(Order).where(Order.id == order.id).with_for_update().execution_options(populate_existing=True))
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    expected_version = changes.pop("version")
    status_note = changes.pop("status_note", None)
    if order.version != expected_version:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This order was changed by another user. Refresh the page")
    old_status = order.status
    old_payment = order.payment_status
    if changes.get("shipping_method"):
        shipping = db.scalar(select(ShippingMethod).where(ShippingMethod.code == changes["shipping_method"], ShippingMethod.is_active.is_(True)))
        if not shipping:
            raise HTTPException(status_code=400, detail="The selected shipping method is unavailable")
        city = changes.get("shipping_city", order.shipping_city)
        branch = changes.get("shipping_branch", order.shipping_branch)
        address = changes.get("shipping_address", order.shipping_address)
        if shipping.requires_city and not city:
            raise HTTPException(status_code=422, detail="The selected shipping method requires a city")
        if shipping.requires_branch and not branch:
            raise HTTPException(status_code=422, detail="The selected shipping method requires a branch")
        if shipping.requires_address and not address:
            raise HTTPException(status_code=422, detail="The selected shipping method requires an address")
    if changes.get("payment_method"):
        payment = db.scalar(select(PaymentMethod).where(PaymentMethod.code == changes["payment_method"], PaymentMethod.is_active.is_(True)))
        if not payment:
            raise HTTPException(status_code=400, detail="The selected payment method is unavailable")
    if "assigned_to_id" in changes and changes["assigned_to_id"] is not None:
        assignee = db.get(User, changes["assigned_to_id"])
        if not assignee or not assignee.is_active:
            raise HTTPException(status_code=400, detail="The assigned user is inactive")
    nullable_fields = {
        "shipping_method", "shipping_city", "shipping_address", "shipping_branch", "shipping_carrier",
        "tracking_number", "payment_method", "admin_note", "customer_note", "customer_email", "assigned_to_id",
    }
    for key, value in changes.items():
        if value is None and key not in nullable_fields:
            continue
        setattr(order, key, value)
    order.total_minor = max(0, order.subtotal_minor - order.discount_minor + order.shipping_minor)
    now = utcnow()
    if old_payment != order.payment_status and order.payment_status == PaymentStatus.PAID and order.paid_at is None:
        order.paid_at = now
    if old_payment != order.payment_status and order.payment_status in {PaymentStatus.UNPAID, PaymentStatus.REFUNDED}:
        order.paid_at = None
    if old_status != order.status:
        # Restore reserved stock only on the first transition into cancelled.
        if order.status == OrderStatus.CANCELLED and old_status != OrderStatus.CANCELLED:
            product_ids = sorted({item.product_id for item in order.items if item.product_id}, key=str)
            stocked = db.scalars(select(Product).where(Product.id.in_(product_ids)).order_by(Product.id).with_for_update()).all() if product_ids else []
            by_id = {product.id: product for product in stocked}
            for item in order.items:
                product = by_id.get(item.product_id)
                if product is not None and item.snapshot.get("inventory_reserved"):
                    product.stock_quantity += item.quantity
        # Reopening a cancelled order requires a new inventory reservation.
        elif old_status == OrderStatus.CANCELLED:
            product_ids = sorted({item.product_id for item in order.items if item.product_id}, key=str)
            stocked = db.scalars(select(Product).where(Product.id.in_(product_ids)).order_by(Product.id).with_for_update()).all() if product_ids else []
            by_id = {product.id: product for product in stocked}
            for item in order.items:
                product = by_id.get(item.product_id)
                if product is not None and item.snapshot.get("inventory_reserved"):
                    if product.stock_quantity < item.quantity:
                        raise HTTPException(status_code=409, detail=f"Insufficient stock to reopen {product.title}")
                    product.stock_quantity -= item.quantity
        if order.status == OrderStatus.SHIPPED and order.shipped_at is None:
            order.shipped_at = now
        if order.status == OrderStatus.COMPLETED and order.completed_at is None:
            order.completed_at = now
        db.add(OrderStatusHistory(order_id=order.id, from_status=old_status, to_status=order.status, changed_by_id=actor.id, note=status_note))
    order.version += 1
    write_audit(
        db,
        request,
        "order.admin.updated",
        actor=actor,
        resource_type="order",
        resource_id=order.id,
        details={
            "order_number": order.order_number,
            "from_status": old_status.value,
            "to_status": order.status.value,
            "from_payment_status": old_payment.value,
            "to_payment_status": order.payment_status.value,
            "changed_fields": sorted(changes.keys()),
        },
    )
    db.commit()
    return db.scalar(select(Order).options(selectinload(Order.items), selectinload(Order.history)).where(Order.id == order.id))
