from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from warehouse.models import Box, Order, OrderItem, Product

pytestmark = pytest.mark.django_db


def make_product(**overrides):
    defaults = dict(
        sku="TEST-001", name="Test Product", length_mm=10, width_mm=10, height_mm=10,
        weight_g=100,
    )
    defaults.update(overrides)
    return Product(**defaults)


def make_box(**overrides):
    defaults = dict(
        code="TESTBOX", name="Test Box", inner_length_mm=100, inner_width_mm=100,
        inner_height_mm=100, max_weight_g=5000, cost=Decimal("10.00"),
    )
    defaults.update(overrides)
    return Box(**defaults)


def test_product_rejects_non_positive_dimensions():
    product = make_product(length_mm=0)
    with pytest.raises(ValidationError):
        product.full_clean()


def test_product_rejects_zero_weight():
    product = make_product(weight_g=0)
    with pytest.raises(ValidationError):
        product.full_clean()


def test_box_rejects_non_positive_dimensions():
    box = make_box(inner_height_mm=-5)
    with pytest.raises(ValidationError):
        box.full_clean()


def test_product_sku_must_be_unique():
    make_product(sku="DUP").save()
    with pytest.raises(IntegrityError):
        make_product(sku="DUP").save()


def test_box_code_must_be_unique():
    make_box(code="DUP").save()
    with pytest.raises(IntegrityError):
        make_box(code="DUP").save()


def test_volume_properties():
    product = make_product(length_mm=2, width_mm=3, height_mm=4)
    assert product.volume_mm3 == 24
    box = make_box(inner_length_mm=2, inner_width_mm=3, inner_height_mm=4)
    assert box.volume_mm3 == 24


def test_order_item_unique_per_product_per_order():
    order = Order.objects.create(reference="ORD-1")
    product = make_product()
    product.save()
    OrderItem.objects.create(order=order, product=product, quantity=1)
    with pytest.raises(IntegrityError):
        OrderItem.objects.create(order=order, product=product, quantity=2)


def test_order_default_status_is_pending():
    order = Order.objects.create(reference="ORD-2")
    assert order.status == Order.Status.PENDING
