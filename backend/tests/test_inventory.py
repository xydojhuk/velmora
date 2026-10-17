"""Validation regressions for the optional inventory feature.

Database concurrency is covered by separate PostgreSQL integration checks.
"""
import os
import pytest
from pydantic import ValidationError

os.environ.setdefault("JWT_SECRET", "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_!@#$%^&*()")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///./test_inventory.db")
from app.schemas.products import ProductCreate, ProductUpdate


def item(**kwargs):
    return ProductCreate(slug="sample-item", sku="ITEM-1", model="base", name="Base", title="Example", price_minor=1500, **kwargs)


def test_inventory_is_opt_in_for_existing_catalog():
    obj = item()
    assert obj.track_inventory is False and obj.stock_quantity == 0 and obj.category_slug == "general"


def test_stock_cannot_be_negative():
    with pytest.raises(ValidationError): item(track_inventory=True, stock_quantity=-1)
    with pytest.raises(ValidationError): ProductUpdate(low_stock_threshold=-2)


@pytest.mark.parametrize("slug", ["MixedCase", "../evil", "two spaces", "", "a--b"])
def test_category_slug_is_safe(slug):
    with pytest.raises(ValidationError): item(category_slug=slug)


def test_valid_custom_category():
    assert item(category_slug="home-accessories").category_slug == "home-accessories"
