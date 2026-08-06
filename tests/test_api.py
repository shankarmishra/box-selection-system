from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from warehouse.models import Box, Order, OrderItem, Product

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def small_box():
    return Box.objects.create(
        code="S", name="Small", inner_length_mm=200, inner_width_mm=200, inner_height_mm=200,
        max_weight_g=5000, cost=Decimal("20.00"),
    )


@pytest.fixture
def mug():
    return Product.objects.create(
        sku="MUG-001", name="Mug", length_mm=50, width_mm=50, height_mm=50, weight_g=300,
    )


def test_health_endpoint(client):
    response = client.get("/api/v1/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_recommend_happy_path(client, small_box, mug):
    response = client.post(
        "/api/v1/recommend/",
        {"items": [{"sku": "MUG-001", "quantity": 1}]},
        format="json",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["strategy"] == "SINGLE_BOX"
    assert body["recommended_box"]["code"] == "S"
    assert len(body["evaluated"]) == 1
    assert body["evaluated"][0]["box"] == "S"


def test_recommend_unknown_sku_returns_400(client, small_box):
    response = client.post(
        "/api/v1/recommend/",
        {"items": [{"sku": "GHOST-999", "quantity": 1}]},
        format="json",
    )
    assert response.status_code == 400


def test_recommend_empty_items_returns_400(client):
    response = client.post("/api/v1/recommend/", {"items": []}, format="json")
    assert response.status_code == 400


def test_recommend_no_fit_returns_200_with_no_fit_strategy(mug):
    # No boxes exist at all.
    client = APIClient()
    response = client.post(
        "/api/v1/recommend/",
        {"items": [{"sku": "MUG-001", "quantity": 1}]},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["strategy"] == "NO_FIT"
    assert response.json()["recommended_box"] is None


def test_order_recommend_action_persists_and_updates_status(client, small_box, mug):
    order = Order.objects.create(reference="ORD-API-1")
    OrderItem.objects.create(order=order, product=mug, quantity=1)

    response = client.post(f"/api/v1/orders/{order.id}/recommend/")

    assert response.status_code == 200
    assert response.json()["strategy"] == "SINGLE_BOX"

    order.refresh_from_db()
    assert order.status == Order.Status.RECOMMENDED


def test_order_recommend_then_fetch_persisted_result(client, small_box, mug):
    order = Order.objects.create(reference="ORD-API-2")
    OrderItem.objects.create(order=order, product=mug, quantity=1)
    client.post(f"/api/v1/orders/{order.id}/recommend/")

    response = client.get(f"/api/v1/orders/{order.id}/recommendation/")

    assert response.status_code == 200
    assert response.json()["strategy"] == "SINGLE_BOX"


def test_order_recommend_with_no_items_returns_400(client):
    order = Order.objects.create(reference="ORD-API-3")
    response = client.post(f"/api/v1/orders/{order.id}/recommend/")
    assert response.status_code == 400


def test_fetching_recommendation_before_computing_returns_404(client):
    order = Order.objects.create(reference="ORD-API-4")
    response = client.get(f"/api/v1/orders/{order.id}/recommendation/")
    assert response.status_code == 404


def test_products_list_endpoint(client, mug):
    response = client.get("/api/v1/products/")
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_boxes_list_endpoint(client, small_box):
    response = client.get("/api/v1/boxes/")
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_openapi_schema_is_served(client):
    response = client.get("/api/schema/")
    assert response.status_code == 200
