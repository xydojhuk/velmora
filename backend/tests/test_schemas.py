import os

import pytest
from pydantic import ValidationError

os.environ.setdefault("JWT_SECRET", 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_!@#$%^&*()')
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///./test_schemas.db")

from app.schemas.orders import PublicOrderCreate
from app.schemas.products import ProductCreate


def test_product_slug_validation():
    with pytest.raises(ValidationError):
        ProductCreate(
            slug="Bad Slug",
            sku="x",
            model="x",
            name="x",
            title="x",
            price_minor=100,
        )


def test_order_requires_item():
    with pytest.raises(ValidationError):
        PublicOrderCreate(customer_name="Test User", customer_phone="+380000000000", items=[])


def test_store_settings_allows_disabled_notification_without_recipient():
    from app.schemas.settings import StoreSettingsUpdate
    payload = StoreSettingsUpdate(notification_email_enabled=False, notification_email_to="")
    assert payload.notification_email_to == ""


def test_login_accepts_local_bootstrap_email():
    from app.schemas.auth import AuthUser, LoginRequest
    from app.enums import UserRole
    import uuid

    payload = LoginRequest(email=" admin@velmora.local ", password=" Strong-Test-Password-2026! ")
    assert payload.email == "admin@velmora.local"
    assert payload.password == " Strong-Test-Password-2026! "
    user = AuthUser(id=uuid.uuid4(), email="admin@velmora.local", display_name="Administrator", role=UserRole.ADMIN, is_active=True)
    assert user.email == "admin@velmora.local"


def test_store_settings_accepts_structured_business_hours():
    from app.schemas.settings import StoreSettingsUpdate
    from app.store_defaults import default_business_hours

    payload = StoreSettingsUpdate(business_hours=default_business_hours(), timezone="Europe/Podgorica")
    assert len(payload.business_hours) == 7
    assert payload.timezone == "Europe/Podgorica"


def test_store_settings_rejects_duplicate_business_days():
    from app.schemas.settings import StoreSettingsUpdate
    from app.store_defaults import default_business_hours

    hours = default_business_hours()
    hours[-1]["day"] = "sat"
    with pytest.raises(ValidationError):
        StoreSettingsUpdate(business_hours=hours)


def test_store_settings_rejects_unknown_timezone():
    from app.schemas.settings import StoreSettingsUpdate

    with pytest.raises(ValidationError):
        StoreSettingsUpdate(timezone="Mars/Olympus")


def test_business_hours_summary_groups_matching_days():
    from app.services.store import format_business_hours
    from app.store_defaults import default_business_hours

    assert format_business_hours(default_business_hours(), "UTC") == "Mon–Sat · 09:00–18:00 · UTC"


def test_storefront_config_accepts_bundled_defaults():
    from app.schemas.settings import StorefrontConfig
    from app.store_defaults import default_storefront

    payload = StorefrontConfig.model_validate(default_storefront())
    assert payload.header.show_hours is False
    assert payload.branding.logo_url == "/img/logo.png"
    assert payload.hero.primary_action.action == "catalog"


def test_storefront_config_rejects_css_injection_color():
    from app.schemas.settings import StorefrontConfig
    from app.store_defaults import default_storefront

    data = default_storefront()
    data["theme"]["accent"] = "red; background:url(javascript:alert(1))"
    with pytest.raises(ValidationError):
        StorefrontConfig.model_validate(data)


def test_storefront_config_rejects_unsafe_url():
    from app.schemas.settings import StorefrontConfig
    from app.store_defaults import default_storefront

    data = default_storefront()
    data["hero"]["primary_action"] = {"enabled": True, "label": "Click", "action": "url", "url": "javascript:alert(1)"}
    with pytest.raises(ValidationError):
        StorefrontConfig.model_validate(data)


def test_storefront_navigation_keys_must_be_unique():
    from app.schemas.settings import StorefrontConfig
    from app.store_defaults import default_storefront

    data = default_storefront()
    data["header"]["nav"].append({"key": "home", "label": "Again", "enabled": True})
    with pytest.raises(ValidationError):
        StorefrontConfig.model_validate(data)


def test_storefront_normalizer_merges_partial_legacy_config():
    from app.services.store import normalize_storefront

    merged = normalize_storefront({"modals": {"contacts": {"title": "Legacy support"}}})
    assert merged["modals"]["contacts"]["title"] == "Legacy support"
    assert merged["header"]["show_hours"] is False
    assert merged["hero"]["image_url"] == ""  # neutral core no longer forces legacy FPV banner
