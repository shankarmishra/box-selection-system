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
