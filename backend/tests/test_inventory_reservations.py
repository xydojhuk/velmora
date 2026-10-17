"""Business logic checks without a PostgreSQL instance; does not replace concurrency E2E."""
from types import SimpleNamespace
from fastapi import HTTPException
from app.schemas.orders import PublicOrderItemCreate
from app.services.orders import _build_items


class FakeResult:
    def __init__(self, rows): self.rows = rows
    def all(self): return self.rows


class FakeSession:
    def __init__(self, products): self.products = products
    def scalars(self, _query): return FakeResult(self.products)


def product(stock, tracking=True):
    return SimpleNamespace(
        id='fake', slug='test-product', sku='SKU', model='Standard', name='Example',
        title='Test product', price_minor=1599, currency='EUR', stock_quantity=stock,
        track_inventory=tracking, primary_image=''
    )


def test_inventory_decrements_and_marks_order_snapshot():
    p = product(4)
    items, subtotal, currency = _build_items(FakeSession([p]), [PublicOrderItemCreate(product_slug='test-product', quantity=3)])
    assert p.stock_quantity == 1
    assert subtotal == 4797
    assert currency == 'EUR'
    assert items[0].snapshot['inventory_reserved'] is True


def test_duplicate_items_do_not_oversell():
    p = product(2)
    inputs = [PublicOrderItemCreate(product_slug='test-product', quantity=2), PublicOrderItemCreate(product_slug='test-product', quantity=1)]
    try:
        _build_items(FakeSession([p]), inputs)
    except HTTPException as ex:
        assert ex.status_code == 409
    else:
        raise AssertionError('Expected stock conflict')
    assert p.stock_quantity == 2


def test_stock_ignored_for_services():
    p = product(0, tracking=False)
    _build_items(FakeSession([p]), [PublicOrderItemCreate(product_slug='test-product', quantity=2)])
    assert p.stock_quantity == 0
