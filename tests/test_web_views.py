from decimal import Decimal

import pytest
from django.test import Client

from warehouse.models import Box, Order, OrderItem, Product

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def small_box():
    return Box.objects.create(
        code="S", name="Small", inner_length_mm=300, inner_width_mm=300, inner_height_mm=300,
        max_weight_g=5000, cost=Decimal("20.00"),
    )


@pytest.fixture
def mug():
    return Product.objects.create(
        sku="MUG-001", name="Mug", length_mm=50, width_mm=50, height_mm=50, weight_g=300,
    )


def test_home_page_lists_orders(client, small_box, mug):
    order = Order.objects.create(reference="ORD-WEB-1")
    OrderItem.objects.create(order=order, product=mug, quantity=1)

    response = client.get("/")

    assert response.status_code == 200
    assert "ORD-WEB-1" in response.content.decode()


def test_home_page_empty_state(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "seed_demo_data" in response.content.decode()


def test_visualize_computes_recommendation_on_first_view(client, small_box, mug):
    order = Order.objects.create(reference="ORD-WEB-2")
    OrderItem.objects.create(order=order, product=mug, quantity=1)
    assert not hasattr(order, "recommendation") or order.recommendation is None

    response = client.get(f"/visualize/{order.id}/")

    assert response.status_code == 200
    order.refresh_from_db()
    assert order.recommendation.strategy == "SINGLE_BOX"


def test_visualize_reuses_existing_recommendation(client, small_box, mug):
    order = Order.objects.create(reference="ORD-WEB-3")
    OrderItem.objects.create(order=order, product=mug, quantity=1)
    client.get(f"/visualize/{order.id}/")  # computes it
    first_id = order.recommendation.id

    client.get(f"/visualize/{order.id}/")  # should reuse, not recompute

    order.refresh_from_db()
    assert order.recommendation.id == first_id


def test_visualize_renders_svgs_for_single_box(client, small_box, mug):
    order = Order.objects.create(reference="ORD-WEB-4")
    OrderItem.objects.create(order=order, product=mug, quantity=1)

    response = client.get(f"/visualize/{order.id}/")

    body = response.content.decode()
    assert body.count("<svg") >= 4  # isometric + top + front + side


def test_visualize_shows_utilization_as_a_correct_percentage(client):
    # Item volume is exactly 25% of the box's interior volume. This is a
    # regression test: Django's `floatformat:0` filter does NOT multiply
    # by 100, so `0.25|floatformat:0` renders "0", not "25" — silently
    # showing every order as ~0% utilized regardless of the real value.
    # The fix uses `{% widthratio %}` instead. See git history for the
    # visual bug this caught (a screenshot showing "0%" next to a table
    # row that correctly said 0.08 utilization).
    Box.objects.create(
        code="QUARTER", name="Quarter Box", inner_length_mm=20, inner_width_mm=10,
        inner_height_mm=10, max_weight_g=5000, cost=Decimal("10.00"),
    )
    product = Product.objects.create(
        sku="BLOCK", name="Block", length_mm=10, width_mm=10, height_mm=5, weight_g=100,
    )
    order = Order.objects.create(reference="ORD-WEB-UTIL")
    OrderItem.objects.create(order=order, product=product, quantity=1)

    response = client.get(f"/visualize/{order.id}/")

    body = response.content.decode()
    assert "25%" in body
    # Guard against the specific regression, not against "100%" width=""
    # SVG attributes elsewhere on the page (which legitimately contain "0%").
    assert '<div class="stat">0%</div>' not in body


def test_visualize_no_fit_order_renders_without_error(client, mug):
    # No boxes in the catalogue at all.
    order = Order.objects.create(reference="ORD-WEB-5")
    OrderItem.objects.create(order=order, product=mug, quantity=1)

    response = client.get(f"/visualize/{order.id}/")

    assert response.status_code == 200
    assert "No box in the active catalogue" in response.content.decode()


def test_visualize_multi_box_order_renders_one_card_per_box(client, mug):
    tiny_box = Box.objects.create(
        code="TINY", name="Tiny", inner_length_mm=60, inner_width_mm=60, inner_height_mm=60,
        max_weight_g=400, cost=Decimal("5.00"),
    )
    order = Order.objects.create(reference="ORD-WEB-6")
    OrderItem.objects.create(order=order, product=mug, quantity=3)  # 900g > 400g -> needs 3 boxes

    response = client.get(f"/visualize/{order.id}/")

    assert response.status_code == 200
    order.refresh_from_db()
    assert order.recommendation.strategy == "MULTI_BOX"
    assert response.content.decode().count(f"Box {tiny_box.code}") == 3


def test_visualize_unknown_order_returns_404(client):
    response = client.get("/visualize/999999/")
    assert response.status_code == 404
