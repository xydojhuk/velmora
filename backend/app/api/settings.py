import re
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import write_audit
from app.database import get_db
from app.dependencies import require_admin, require_admin_read
from app.media import delete_storefront_image_file, store_storefront_image
from app.models import PaymentMethod, ShippingMethod, StoreSettings, User
from app.schemas.settings import (
    PaymentMethodCreate,
    PaymentMethodRead,
    PaymentMethodUpdate,
    ShippingMethodCreate,
    ShippingMethodRead,
    ShippingMethodUpdate,
    StoreSettingsRead,
    StoreSettingsUpdate,
)
from app.services.store import format_business_hours, get_or_create_store_settings, normalize_business_hours


router = APIRouter(prefix="/admin/settings", tags=["admin-settings"])


def _ensure_unique_code(db: Session, model, code: str, current_id: uuid.UUID | None = None) -> None:
    query = select(model.id).where(model.code == code)
    if current_id:
        query = query.where(model.id != current_id)
    if db.scalar(query):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This code is already in use")


@router.get("", response_model=StoreSettingsRead)
def read_settings(_: User = Depends(require_admin_read), db: Session = Depends(get_db)):
    config = get_or_create_store_settings(db)
    db.commit()
    db.refresh(config)
    return config


@router.patch("", response_model=StoreSettingsRead)
def update_settings(
    payload: StoreSettingsUpdate,
    request: Request,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    config = get_or_create_store_settings(db)
    changes = payload.model_dump(exclude_unset=True, mode="json")
    if "business_hours" in changes and changes["business_hours"] is not None:
        changes["business_hours"] = normalize_business_hours(changes["business_hours"])
    for key, value in changes.items():
        if value is not None:
            setattr(config, key, value)
    if "business_hours" in changes or "timezone" in changes:
        config.working_hours = format_business_hours(config.business_hours, config.timezone)
    write_audit(db, request, "settings.updated", actor=actor, resource_type="settings", resource_id="store", details={"changed_fields": sorted(changes)})
    db.commit()
    db.refresh(config)
    return config


@router.post("/media", status_code=201)
async def upload_storefront_media(
    request: Request,
    file: UploadFile = File(...),
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    stored = await store_storefront_image(file)
    write_audit(
        db,
        request,
        "settings.storefront_media_uploaded",
        actor=actor,
        resource_type="storefront_media",
        resource_id=stored.storage_name,
        details={"url": stored.url, "width": stored.width, "height": stored.height, "size_bytes": stored.size_bytes},
    )
    db.commit()
    return {
        "url": stored.url,
        "storage_name": stored.storage_name,
        "original_name": stored.original_name,
        "width": stored.width,
        "height": stored.height,
        "size_bytes": stored.size_bytes,
    }


@router.delete("/media/{storage_name}", status_code=204)
def delete_storefront_media(
    storage_name: str,
    request: Request,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if not re.fullmatch(r"[0-9a-f]{32}\.webp", storage_name):
        raise HTTPException(status_code=422, detail="Invalid storefront media name")
    delete_storefront_image_file(storage_name)
    write_audit(
        db,
        request,
        "settings.storefront_media_deleted",
        actor=actor,
        resource_type="storefront_media",
        resource_id=storage_name,
    )
    db.commit()
    return None


@router.get("/shipping", response_model=list[ShippingMethodRead])
def list_shipping(_: User = Depends(require_admin_read), db: Session = Depends(get_db)):
    return db.scalars(select(ShippingMethod).order_by(ShippingMethod.sort_order, ShippingMethod.name)).all()


@router.post("/shipping", response_model=ShippingMethodRead, status_code=201)
def create_shipping(
    payload: ShippingMethodCreate,
    request: Request,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _ensure_unique_code(db, ShippingMethod, payload.code)
    row = ShippingMethod(**payload.model_dump())
    db.add(row)
    db.flush()
    write_audit(db, request, "settings.shipping_created", actor=actor, resource_type="shipping_method", resource_id=row.id, details={"code": row.code})
    db.commit()
    db.refresh(row)
    return row


@router.patch("/shipping/{method_id}", response_model=ShippingMethodRead)
def update_shipping(
    method_id: uuid.UUID,
    payload: ShippingMethodUpdate,
    request: Request,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    row = db.get(ShippingMethod, method_id)
    if not row:
        raise HTTPException(status_code=404, detail="Shipping method not found")
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("code") and changes["code"] != row.code:
        _ensure_unique_code(db, ShippingMethod, changes["code"], row.id)
    for key, value in changes.items():
        if value is not None:
            setattr(row, key, value)
    write_audit(db, request, "settings.shipping_updated", actor=actor, resource_type="shipping_method", resource_id=row.id, details={"changed_fields": sorted(changes)})
    db.commit()
    db.refresh(row)
    return row


@router.delete("/shipping/{method_id}", status_code=204)
def delete_shipping(
    method_id: uuid.UUID,
    request: Request,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    row = db.get(ShippingMethod, method_id)
    if not row:
        raise HTTPException(status_code=404, detail="Shipping method not found")
    write_audit(db, request, "settings.shipping_deleted", actor=actor, resource_type="shipping_method", resource_id=row.id, details={"code": row.code})
    db.delete(row)
    db.commit()
    return None


@router.get("/payment", response_model=list[PaymentMethodRead])
def list_payment(_: User = Depends(require_admin_read), db: Session = Depends(get_db)):
    return db.scalars(select(PaymentMethod).order_by(PaymentMethod.sort_order, PaymentMethod.name)).all()


@router.post("/payment", response_model=PaymentMethodRead, status_code=201)
def create_payment(
    payload: PaymentMethodCreate,
    request: Request,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _ensure_unique_code(db, PaymentMethod, payload.code)
    row = PaymentMethod(**payload.model_dump())
    db.add(row)
    db.flush()
    write_audit(db, request, "settings.payment_created", actor=actor, resource_type="payment_method", resource_id=row.id, details={"code": row.code})
    db.commit()
    db.refresh(row)
    return row


@router.patch("/payment/{method_id}", response_model=PaymentMethodRead)
def update_payment(
    method_id: uuid.UUID,
    payload: PaymentMethodUpdate,
    request: Request,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    row = db.get(PaymentMethod, method_id)
    if not row:
        raise HTTPException(status_code=404, detail="Payment method not found")
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("code") and changes["code"] != row.code:
        _ensure_unique_code(db, PaymentMethod, changes["code"], row.id)
    for key, value in changes.items():
        if value is not None:
            setattr(row, key, value)
    write_audit(db, request, "settings.payment_updated", actor=actor, resource_type="payment_method", resource_id=row.id, details={"changed_fields": sorted(changes)})
    db.commit()
    db.refresh(row)
    return row


@router.delete("/payment/{method_id}", status_code=204)
def delete_payment(
    method_id: uuid.UUID,
    request: Request,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    row = db.get(PaymentMethod, method_id)
    if not row:
        raise HTTPException(status_code=404, detail="Payment method not found")
    write_audit(db, request, "settings.payment_deleted", actor=actor, resource_type="payment_method", resource_id=row.id, details={"code": row.code})
    db.delete(row)
    db.commit()
    return None
