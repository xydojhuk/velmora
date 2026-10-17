from __future__ import annotations

import json
import sys

from sqlalchemy import select

from app.audit import write_audit
from app.database import SessionLocal
from app.enums import UserRole
from app.models import AuditLog, Product, ProductImage, StoreSettings, User
from app.security import hash_password, validate_password_policy
from app.seed_data import CURRENT_PRODUCT_IMAGES, CURRENT_PRODUCTS
from app.services.store import format_business_hours
from app.store_defaults import default_business_hours
from app.utils import utcnow


def main() -> int:
    payload = json.load(sys.stdin)
    admin = payload["admin"]
    store = payload["store"]
    password = admin["password"]
    validate_password_policy(password, admin["email"])

    db = SessionLocal()
    try:
        if db.scalar(select(User.id).limit(1)):
            raise RuntimeError("The target database already contains a Velmora user")

        user = User(
            email=admin["email"].strip().lower(),
            display_name=admin["name"].strip(),
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
            is_active=True,
            password_changed_at=utcnow(),
        )
        db.add(user)
        db.flush()
        db.add(
            AuditLog(
                actor_user_id=user.id,
                actor_email=user.email,
                action="user.browser_installer.created",
                resource_type="user",
                resource_id=str(user.id),
                success=True,
                details={"email": user.email},
            )
        )

        schedule = default_business_hours()
        settings = db.get(StoreSettings, 1) or StoreSettings(id=1)
        settings.store_name = store["store_name"].strip()
        settings.brand_tagline = store["brand_tagline"].strip()
        settings.phone = store["phone"].strip()
        settings.email = str(store["email"] or "").strip().lower()
        settings.service_region = store["service_region"].strip()
        settings.timezone = store["timezone"].strip()
        settings.business_hours = schedule
        settings.working_hours = format_business_hours(schedule, settings.timezone)
        settings.footer_description = store["footer_description"].strip()
        settings.seo_title = f"{settings.store_name} — official storefront"
        settings.seo_description = settings.footer_description[:500]
        settings.seo_og_image = "/brand/velmora-icon-512.png"
        settings.orders_enabled = True
        settings.maintenance_mode = False
        db.add(settings)

        if payload.get("demo_catalog", True):
            for item in CURRENT_PRODUCTS:
                product = Product(**item)
                db.add(product)
                db.flush()
                for sort_order, (image_url, alt_text, width, height) in enumerate(CURRENT_PRODUCT_IMAGES.get(item["slug"], [])):
                    filename = image_url.rsplit("/", 1)[-1]
                    mime_type = "image/jpeg" if filename.lower().endswith((".jpg", ".jpeg")) else "image/png"
                    product.images.append(
                        ProductImage(
                            url=image_url,
                            original_name=filename,
                            mime_type=mime_type,
                            size_bytes=0,
                            width=width,
                            height=height,
                            alt_text=alt_text,
                            sort_order=sort_order,
                        )
                    )

        db.commit()
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
