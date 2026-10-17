"""Part 2 safety regressions. Full locking semantics require PostgreSQL E2E."""
import os
from types import SimpleNamespace
from pathlib import Path

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

os.environ.setdefault("JWT_SECRET", "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_!@#$%^&*()")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///./test_inventory.db")

from app.schemas.categories import CategoryCreate, CategoryUpdate
from app.schemas.orders import PublicOrderCreate, PublicOrderItemCreate
from app.services.orders import _build_items, _check_idempotency, _order_fingerprint
from app.version import get_version


class FakeResult:
    def __init__(self, values):
        self.values = values
    def all(self):
        return self.values


class FakeSession:
    def __init__(self, products):
        self.products = products
    def scalars(self, _):
        return FakeResult(self.products)


def order_payload(qty=1, phone='+3821234567'):
    return PublicOrderCreate(customer_name='Example Client', customer_phone=phone, items=[PublicOrderItemCreate(product_slug='product-one', quantity=qty)], shipping_method='pickup', payment_method='cash')


def product(slug, currency):
    return SimpleNamespace(id=slug, slug=slug, currency=currency, stock_quantity=3, track_inventory=True, price_minor=100, title=slug, model='test', name='base', sku=slug, primary_image='')


def test_request_fingerprint_is_stable_and_sensitive_to_content():
    a = order_payload()
    assert _order_fingerprint(a) == _order_fingerprint(order_payload())
    assert _order_fingerprint(a) != _order_fingerprint(order_payload(qty=2))
    assert _order_fingerprint(a) != _order_fingerprint(order_payload(phone='+3829999999'))
    assert len(_order_fingerprint(a)) == 64


def test_idempotency_key_cannot_replay_different_payload_or_unfingerprinted_legacy():
    fingerprint = _order_fingerprint(order_payload())
    _check_idempotency(SimpleNamespace(idempotency_fingerprint=fingerprint), fingerprint)
    for bad in ('', None, _order_fingerprint(order_payload(qty=3))):
        with pytest.raises(HTTPException) as caught:
            _check_idempotency(SimpleNamespace(idempotency_fingerprint=bad), fingerprint)
        assert caught.value.status_code == 409


def test_mixed_currency_rejected_before_stock_is_decremented():
    a, b = product('product-one', 'EUR'), product('product-two', 'USD')
    with pytest.raises(HTTPException) as caught:
        _build_items(FakeSession([a, b]), [PublicOrderItemCreate(product_slug='product-one', quantity=2), PublicOrderItemCreate(product_slug='product-two', quantity=1)])
    assert caught.value.status_code == 400
    assert (a.stock_quantity, b.stock_quantity) == (3, 3)


def test_category_schema_and_immutable_slug():
    category = CategoryCreate(slug='home-accessories', name='Home accessories')
    assert category.is_active
    assert CategoryUpdate(name='Updated').name == 'Updated'
    assert 'slug' not in CategoryUpdate.model_fields
    for unsafe in ('Bad Caps', '../escape', 'a--b'):
        with pytest.raises(ValidationError):
            CategoryCreate(slug=unsafe, name='Invalid')


def test_backend_version_reads_root_file():
    assert get_version() == (Path(__file__).resolve().parents[2] / 'VERSION').read_text().strip()
