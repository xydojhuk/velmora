import uuid
from fastapi.responses import Response
from app.services.csv_export import export_csv

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.audit import write_audit
from app.config import settings
from app.database import get_db
from app.dependencies import require_staff, require_staff_read
from app.media import delete_product_image_file, store_product_image
from app.models import Category, Product, ProductImage, User
from app.schemas.products import ProductCreate, ProductImageOrder, ProductImageRead, ProductList, ProductRead, ProductUpdate


router = APIRouter(prefix="/admin/products", tags=["admin-products"])


@router.get("", response_model=ProductList)
def list_products(
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=100),
    search: str | None = Query(default=None, max_length=120),
    active: bool | None = None,
    category: str | None = Query(default=None, max_length=80),
    low_stock: bool = False,
    _: User = Depends(require_staff_read),
    db: Session = Depends(get_db),
):
    filters = []
    if search:
        term = f"%{search.strip()}%"
        filters.append(or_(Product.title.ilike(term), Product.sku.ilike(term), Product.slug.ilike(term), Product.model.ilike(term)))
    if active is not None:
        filters.append(Product.is_active == active)
    if category:
        filters.append(Product.category_slug == category)
    if low_stock:
        filters.extend([Product.track_inventory.is_(True), Product.stock_quantity <= Product.low_stock_threshold])
    total = db.scalar(select(func.count(Product.id)).where(*filters)) or 0
    items = db.scalars(
        select(Product)
        .where(*filters)
        .order_by(Product.sort_order.asc(), Product.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).all()
    return ProductList(items=items, total=total, page=page, size=size)


@router.get("/export.csv")
def export_products(_: User = Depends(require_staff_read), db: Session = Depends(get_db)):
    products = db.scalars(select(Product).order_by(Product.sort_order.asc()).limit(20000)).all()
    rows = [(
        product.slug, product.sku, product.title, product.category_slug, product.price_minor,
        product.currency, product.is_active, product.track_inventory, product.stock_quantity,
    ) for product in products]
    content = export_csv(("slug", "sku", "title", "category_slug", "price_minor", "currency", "is_active", "track_inventory", "stock_quantity"), rows)
    return Response(content, media_type="text/csv; charset=utf-8", headers={"Content-Disposition": 'attachment; filename="velmora-products.csv"', "Cache-Control":"no-store"})


@router.get("/{product_id}", response_model=ProductRead)
def get_product(product_id: uuid.UUID, _: User = Depends(require_staff_read), db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.post("", response_model=ProductRead, status_code=201)
def create_product(
    payload: ProductCreate,
    request: Request,
    actor: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    if db.scalar(select(Product.id).where(Product.slug == payload.slug)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A product with this page slug already exists")
    category = db.get(Category, payload.category_slug)
    if category is None:
        raise HTTPException(status_code=422, detail="Create this category in the catalog first")
    data = payload.model_dump(mode="json")
    product = Product(**data, created_by_id=actor.id, updated_by_id=actor.id)
    db.add(product)
    db.flush()
    write_audit(
        db,
        request,
        "product.created",
        actor=actor,
        resource_type="product",
        resource_id=product.id,
        details={"slug": product.slug, "sku": product.sku},
    )
    db.commit()
    db.refresh(product)
    return product


@router.patch("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: uuid.UUID,
    payload: ProductUpdate,
    request: Request,
    actor: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    product = db.scalar(select(Product).where(Product.id == product_id).with_for_update())
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    changes = payload.model_dump(exclude_unset=True, mode="json")
    if "slug" in changes and changes["slug"] != product.slug:
        if db.scalar(select(Product.id).where(Product.slug == changes["slug"], Product.id != product.id)):
            raise HTTPException(status_code=409, detail="A product with this page slug already exists")
    if "category_slug" in changes and changes["category_slug"] is not None and not db.get(Category, changes["category_slug"]):
        raise HTTPException(status_code=422, detail="Create this category in the catalog first")
    for key, value in changes.items():
        if value is None:
            continue  # Product columns are non-nullable; omit instead of 500.
        setattr(product, key, value)
    product.updated_by_id = actor.id
    write_audit(
        db,
        request,
        "product.updated",
        actor=actor,
        resource_type="product",
        resource_id=product.id,
        details={"changed_fields": sorted(changes.keys())},
    )
    db.commit()
    db.refresh(product)
    return product


@router.post("/{product_id}/images", response_model=ProductImageRead, status_code=201)
async def upload_product_image(
    product_id: uuid.UUID,
    request: Request,
    file: UploadFile = File(...),
    alt_text: str | None = Form(default=None, max_length=240),
    actor: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if len(product.images) >= settings.product_image_max_count:
        raise HTTPException(status_code=409, detail=f"A product can have no more than {settings.product_image_max_count} images")

    stored = await store_product_image(file)
    locked_product = db.scalar(select(Product).where(Product.id == product_id).with_for_update())
    current_count = db.scalar(select(func.count(ProductImage.id)).where(ProductImage.product_id == product_id)) or 0
    if current_count >= settings.product_image_max_count:
        delete_product_image_file(stored.storage_name)
        raise HTTPException(status_code=409, detail=f"A product can have no more than {settings.product_image_max_count} images")
    image = ProductImage(
        product_id=product.id,
        storage_name=stored.storage_name,
        url=stored.url,
        original_name=stored.original_name,
        mime_type=stored.mime_type,
        size_bytes=stored.size_bytes,
        width=stored.width,
        height=stored.height,
        alt_text=(alt_text or product.title).strip()[:240],
        sort_order=current_count,
    )
    try:
        db.add(image)
        locked_product.updated_by_id = actor.id
        write_audit(
            db,
            request,
            "product.image_uploaded",
            actor=actor,
            resource_type="product",
            resource_id=product.id,
            details={
                "original_name": stored.original_name,
                "size_bytes": stored.size_bytes,
                "width": stored.width,
                "height": stored.height,
            },
        )
        db.commit()
        db.refresh(image)
        return image
    except Exception:
        db.rollback()
        delete_product_image_file(stored.storage_name)
        raise


@router.patch("/{product_id}/images/order", response_model=list[ProductImageRead])
def reorder_product_images(
    product_id: uuid.UUID,
    payload: ProductImageOrder,
    request: Request,
    actor: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    current_ids = [image.id for image in product.images]
    if len(payload.image_ids) != len(current_ids) or set(payload.image_ids) != set(current_ids):
        raise HTTPException(status_code=422, detail="The order must contain every product image exactly once")
    by_id = {image.id: image for image in product.images}
    for index, image_id in enumerate(payload.image_ids):
        by_id[image_id].sort_order = index
    product.updated_by_id = actor.id
    write_audit(
        db,
        request,
        "product.images_reordered",
        actor=actor,
        resource_type="product",
        resource_id=product.id,
        details={"image_ids": [str(image_id) for image_id in payload.image_ids]},
    )
    db.commit()
    db.expire(product, ["images"])
    return product.images


@router.delete("/{product_id}/images/{image_id}", status_code=204)
def delete_product_image(
    product_id: uuid.UUID,
    image_id: uuid.UUID,
    request: Request,
    actor: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    image = db.get(ProductImage, image_id)
    if not image or image.product_id != product.id:
        raise HTTPException(status_code=404, detail="Product image not found")
    storage_name = image.storage_name
    db.delete(image)
    db.flush()
    remaining = db.scalars(
        select(ProductImage).where(ProductImage.product_id == product.id).order_by(ProductImage.sort_order.asc(), ProductImage.created_at.asc())
    ).all()
    for index, item in enumerate(remaining):
        item.sort_order = index
    product.updated_by_id = actor.id
    write_audit(
        db,
        request,
        "product.image_deleted",
        actor=actor,
        resource_type="product",
        resource_id=product.id,
        details={"image_id": str(image_id)},
    )
    db.commit()
    delete_product_image_file(storage_name)
    return None


@router.delete("/{product_id}", status_code=204)
def deactivate_product(
    product_id: uuid.UUID,
    request: Request,
    actor: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product.is_active = False
    product.updated_by_id = actor.id
    write_audit(db, request, "product.deactivated", actor=actor, resource_type="product", resource_id=product.id)
    db.commit()
    return None
