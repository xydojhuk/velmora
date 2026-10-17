"""Public category discovery and staff-managed catalog organization."""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import write_audit
from app.database import get_db
from app.dependencies import require_admin, require_staff_read
from app.models import Category, Product, User
from app.schemas.categories import CategoryCreate, CategoryRead, CategoryUpdate

router = APIRouter(tags=["categories"])


@router.get("/public/categories", response_model=list[CategoryRead])
def public_categories(db: Session = Depends(get_db)):
    return db.scalars(select(Category).where(Category.is_active.is_(True)).order_by(Category.sort_order, Category.name)).all()


@router.get("/admin/categories", response_model=list[CategoryRead])
def admin_categories(_: User = Depends(require_staff_read), db: Session = Depends(get_db)):
    return db.scalars(select(Category).order_by(Category.sort_order, Category.name)).all()


@router.post("/admin/categories", response_model=CategoryRead, status_code=201)
def create_category(payload: CategoryCreate, request: Request, actor: User = Depends(require_admin), db: Session = Depends(get_db)):
    if db.get(Category, payload.slug):
        raise HTTPException(409, "A category with this slug already exists")
    category = Category(**payload.model_dump())
    db.add(category)
    write_audit(db, request, "category.created", actor=actor, resource_type="category", resource_id=category.slug)
    db.commit()
    db.refresh(category)
    return category


@router.patch("/admin/categories/{slug}", response_model=CategoryRead)
def update_category(slug: str, payload: CategoryUpdate, request: Request, actor: User = Depends(require_admin), db: Session = Depends(get_db)):
    category = db.scalar(select(Category).where(Category.slug == slug).with_for_update())
    if category is None:
        raise HTTPException(404, "Category not found")
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        if value is not None:
            setattr(category, key, value)
    write_audit(db, request, "category.updated", actor=actor, resource_type="category", resource_id=slug, details={"changed_fields": sorted(changes)})
    db.commit()
    db.refresh(category)
    return category


@router.delete("/admin/categories/{slug}", status_code=204)
def delete_category(slug: str, request: Request, actor: User = Depends(require_admin), db: Session = Depends(get_db)):
    category = db.scalar(select(Category).where(Category.slug == slug).with_for_update())
    if category is None:
        raise HTTPException(404, "Category not found")
    if db.scalar(select(func.count(Product.id)).where(Product.category_slug == slug)):
        raise HTTPException(409, "Move products to another category before deleting")
    db.delete(category)
    write_audit(db, request, "category.deleted", actor=actor, resource_type="category", resource_id=slug)
    db.commit()
