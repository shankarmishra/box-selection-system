from decimal import Decimal

import pytest

from warehouse.models import Box, Order, OrderItem, Product
from warehouse.services import (
    cart_lines_to_domain_items,
    order_items_to_domain_items,
    recommend,
    recommend_for_order,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def small_box():
    return Box.objects.create(
        code="S", name="Small", inner_length_mm=100, inner_width_mm=100, inner_height_mm=100,
        max_weight_g=2000, cost=Decimal("20.00"),
    )


@pytest.fixture
def large_box():
    return Box.objects.create(
        code="L", name="Large", inner_length_mm=300, inner_width_mm=300, inner_height_mm=300,
        max_weight_g=20000, cost=Decimal("60.00"),
    )


@pytest.fixture
def mug():
    return Product.objects.create(
        sku="MUG", name="Mug", length_mm=50, width_mm=50, height_mm=50, weight_g=300,
    )


def test_order_items_to_domain_items_expands_quantity(mug):
    order = Order.objects.create(reference="ORD-1")
    OrderItem.objects.create(order=order, product=mug, quantity=3)

    items = order_items_to_domain_items(order.items.all())

    assert len(items) == 3
    assert {i.id for i in items} == {"MUG#0", "MUG#1", "MUG#2"}
    assert all(i.sku == "MUG" for i in items)


def test_cart_lines_to_domain_items_expands_quantity(mug):
    items = cart_lines_to_domain_items([{"sku": "MUG", "quantity": 2}])
    assert len(items) == 2


def test_cart_lines_raises_on_unknown_sku(mug):
    with pytest.raises(ValueError, match="Unknown SKU"):
        cart_lines_to_domain_items([{"sku": "GHOST", "quantity": 1}])


def test_recommend_for_order_persists_recommendation_and_updates_status(small_box, mug):
    order = Order.objects.create(reference="ORD-2")
    OrderItem.objects.create(order=order, product=mug, quantity=1)

    recommendation = recommend_for_order(order)

    order.refresh_from_db()
    assert order.status == Order.Status.RECOMMENDED
    assert recommendation.strategy == "SINGLE_BOX"
    assert recommendation.primary_box.code == "S"
    assert recommendation.order_id == order.id
    assert len(recommendation.trace) == 1


def test_recommend_for_order_sets_no_fit_status(mug):
    # No boxes in the catalogue at all -> nothing can ever fit.
    order = Order.objects.create(reference="ORD-3")
    OrderItem.objects.create(order=order, product=mug, quantity=1)

    recommendation = recommend_for_order(order)

    order.refresh_from_db()
    assert order.status == Order.Status.NO_FIT
    assert recommendation.strategy == "NO_FIT"


def test_recommend_for_order_is_idempotent_on_rerun(small_box, mug):
    order = Order.objects.create(reference="ORD-4")
    OrderItem.objects.create(order=order, product=mug, quantity=1)

    first = recommend_for_order(order)
    second = recommend_for_order(order)

    assert first.id == second.id  # update_or_create, not a duplicate row


def test_recommend_ignores_inactive_boxes(mug):
    Box.objects.create(
        code="INACTIVE", name="Retired", inner_length_mm=200, inner_width_mm=200,
        inner_height_mm=200, max_weight_g=10000, cost=Decimal("5.00"), is_active=False,
    )
    items = cart_lines_to_domain_items([{"sku": "MUG", "quantity": 1}])
    result = recommend(items)
    assert result.strategy == "NO_FIT"


def test_recommend_multi_box_when_no_single_box_fits(small_box, mug):
    # 10 mugs won't fit in one S box (volume-wise it might, but we pick
    # a case that clearly needs splitting): use weight to force it.
    Product.objects.create(
        sku="HEAVY", name="Heavy Mug", length_mm=50, width_mm=50, height_mm=50, weight_g=1900,
    )
    items = cart_lines_to_domain_items([{"sku": "HEAVY", "quantity": 3}])
    result = recommend(items)
    assert result.strategy == "MULTI_BOX"
    assert len(result.plan) >= 2
