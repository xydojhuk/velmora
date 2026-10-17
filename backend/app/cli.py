import argparse
import getpass
import secrets
import sys

from sqlalchemy import select

from app.audit import write_audit
from app.database import SessionLocal
from app.enums import UserRole
from app.models import AuditLog, Product, ProductImage, StoreSettings, User
from app.media import delete_product_image_file
from app.security import hash_password, validate_password_policy
from app.seed_data import CURRENT_PRODUCT_IMAGES, CURRENT_PRODUCTS
from app.utils import utcnow


def create_admin(args: argparse.Namespace) -> int:
    email = args.email.strip().lower()
    password = args.password or getpass.getpass("Administrator password: ")
    confirm = args.password or getpass.getpass("Repeat password: ")
    if password != confirm:
        print("Passwords do not match", file=sys.stderr)
        return 2
    try:
        validate_password_policy(password, email)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    db = SessionLocal()
    try:
        if db.scalar(select(User.id).where(User.email == email)):
            print("A user with this email already exists", file=sys.stderr)
            return 2
        user = User(
            email=email,
            display_name=args.name.strip(),
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
                action="user.bootstrap_admin.created",
                resource_type="user",
                resource_id=str(user.id),
                success=True,
                details={"email": user.email},
            )
        )
        db.commit()
        print(f"Administrator created: {user.email}")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def seed_catalog(_: argparse.Namespace) -> int:
    """Synchronize the built-in demo catalog in place.

    Bundled catalog slugs stay stable (handle/compact), so running local-seed upgrades an
    existing development database instead of creating duplicates. Product data
    and bundled images are intentionally reset to the current bundled version.
    """
    db = SessionLocal()
    created = 0
    updated = 0
    replaced_images = 0
    stale_media_files: list[str] = []
    try:
        for item in CURRENT_PRODUCTS:
            product = db.scalar(select(Product).where(Product.slug == item["slug"]))
            if product:
                for key, value in item.items():
                    setattr(product, key, value)
                updated += 1
            else:
                product = Product(**item)
                db.add(product)
                db.flush()
                created += 1

            bundled_images = CURRENT_PRODUCT_IMAGES.get(item["slug"], [])
            if bundled_images:
                # local-seed is an explicit bundled-catalog synchronization command.
                # Replace stale development images so an existing local database
                # receives the current gallery without needing to delete the volume.
                for old_image in list(product.images):
                    if old_image.storage_name:
                        stale_media_files.append(old_image.storage_name)
                if product.images:
                    replaced_images += len(product.images)
                product.images.clear()
                db.flush()
                for sort_order, (image_url, alt_text, width, height) in enumerate(bundled_images):
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
        for storage_name in stale_media_files:
            delete_product_image_file(storage_name)
        print(
            f"Demo catalog synchronized. Created: {created}, updated: {updated}, "
            f"replaced images: {replaced_images}"
        )
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()



def configure_store(args: argparse.Namespace) -> int:
    db = SessionLocal()
    try:
        settings = db.get(StoreSettings, 1)
        if settings is None:
            settings = StoreSettings(id=1)
            db.add(settings)
        settings.store_name = args.name.strip()
        settings.phone = args.phone.strip()
        settings.email = args.email.strip().lower()
        settings.working_hours = args.hours.strip()
        settings.service_region = args.region.strip()
        db.commit()
        print("Store settings saved")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def generate_secret(_: argparse.Namespace) -> int:
    print(secrets.token_urlsafe(64))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    p_admin = sub.add_parser("create-admin")
    p_admin.add_argument("--email", required=True)
    p_admin.add_argument("--name", required=True)
    p_admin.add_argument("--password")
    p_admin.set_defaults(func=create_admin)

    p_seed = sub.add_parser("seed-catalog")
    p_seed.set_defaults(func=seed_catalog)

    p_store = sub.add_parser("configure-store")
    p_store.add_argument("--name", required=True)
    p_store.add_argument("--phone", required=True)
    p_store.add_argument("--email", required=True)
    p_store.add_argument("--hours", required=True)
    p_store.add_argument("--region", required=False, default="Worldwide")
    p_store.set_defaults(func=configure_store)

    p_secret = sub.add_parser("generate-secret")
    p_secret.set_defaults(func=generate_secret)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
