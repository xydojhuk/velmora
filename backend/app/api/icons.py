import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import write_audit
from app.config import settings
from app.database import get_db
from app.dependencies import require_admin, require_admin_read
from app.icon_assets import read_icon_upload
from app.models import IconAsset, Product, User
from app.schemas.icons import IconAssetRead, IconAssetUpdate


router = APIRouter(prefix="/admin/icons", tags=["admin-icons"])


def _product_references(product: Product, key: str) -> bool:
    for collection in (product.catalog_metrics or [], product.summary_features or []):
        for item in collection:
            if isinstance(item, dict) and str(item.get("icon") or "").strip() == key:
                return True
    return False


@router.get("", response_model=list[IconAssetRead])
def list_icons(_: User = Depends(require_admin_read), db: Session = Depends(get_db)):
    return db.scalars(select(IconAsset).order_by(IconAsset.label.asc(), IconAsset.created_at.asc())).all()


@router.post("", response_model=IconAssetRead, status_code=201)
async def create_icon(
    request: Request,
    label: str = Form(..., min_length=1, max_length=120),
    file: UploadFile = File(...),
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    total = db.scalar(select(func.count(IconAsset.id))) or 0
    if total >= settings.icon_max_count:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Icon limit reached")
    stored = await read_icon_upload(file, label)
    row = IconAsset(
        key=stored.key,
        label=stored.label,
        svg_markup=stored.svg_markup,
        original_name=stored.original_name,
        size_bytes=stored.size_bytes,
        created_by_id=actor.id,
        updated_by_id=actor.id,
    )
    db.add(row)
    db.flush()
    write_audit(
        db,
        request,
        "icon.created",
        actor=actor,
        resource_type="icon",
        resource_id=row.id,
        details={"key": row.key, "label": row.label, "original_name": row.original_name},
    )
    db.commit()
    db.refresh(row)
    return row


@router.patch("/{icon_id}", response_model=IconAssetRead)
def update_icon(
    icon_id: uuid.UUID,
    payload: IconAssetUpdate,
    request: Request,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    row = db.get(IconAsset, icon_id)
    if not row:
        raise HTTPException(status_code=404, detail="Icon not found")
    row.label = payload.label
    row.updated_by_id = actor.id
    write_audit(
        db,
        request,
        "icon.updated",
        actor=actor,
        resource_type="icon",
        resource_id=row.id,
        details={"changed_fields": ["label"]},
    )
    db.commit()
    db.refresh(row)
    return row


@router.post("/{icon_id}/file", response_model=IconAssetRead)
async def replace_icon_file(
    icon_id: uuid.UUID,
    request: Request,
    file: UploadFile = File(...),
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    row = db.get(IconAsset, icon_id)
    if not row:
        raise HTTPException(status_code=404, detail="Icon not found")
    stored = await read_icon_upload(file, row.label)
    row.svg_markup = stored.svg_markup
    row.original_name = stored.original_name
    row.size_bytes = stored.size_bytes
    row.updated_by_id = actor.id
    write_audit(
        db,
        request,
        "icon.file_replaced",
        actor=actor,
        resource_type="icon",
        resource_id=row.id,
        details={"original_name": row.original_name, "size_bytes": row.size_bytes},
    )
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{icon_id}", status_code=204)
def delete_icon(
    icon_id: uuid.UUID,
    request: Request,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    row = db.get(IconAsset, icon_id)
    if not row:
        raise HTTPException(status_code=404, detail="Icon not found")
    products = db.scalars(select(Product)).all()
    used_by = [product.title for product in products if _product_references(product, row.key)]
    if used_by:
        names = ", ".join(used_by[:4])
        suffix = "…" if len(used_by) > 4 else ""
        raise HTTPException(status_code=409, detail=f"Icon is used by products: {names}{suffix}")
    write_audit(
        db,
        request,
        "icon.deleted",
        actor=actor,
        resource_type="icon",
        resource_id=row.id,
        details={"key": row.key, "label": row.label},
    )
    db.delete(row)
    db.commit()
    return None
