import io

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from warehouse.models import Box, Order, Product

pytestmark = pytest.mark.django_db


def test_seed_demo_data_creates_catalogue_and_orders():
    call_command("seed_demo_data", stdout=io.StringIO())

    assert Box.objects.count() == 7
    assert Product.objects.count() == 11
    assert Order.objects.count() == 5
    assert set(Order.objects.values_list("reference", flat=True)) == {
        "DEMO-001", "DEMO-002", "DEMO-003", "DEMO-004", "DEMO-005",
    }


def test_seed_demo_data_is_idempotent():
    call_command("seed_demo_data", stdout=io.StringIO())
    call_command("seed_demo_data", stdout=io.StringIO())  # run again, no duplicates

    assert Box.objects.count() == 7
    assert Product.objects.count() == 11
    assert Order.objects.count() == 5


def test_seed_demo_data_flush_rebuilds_from_scratch():
    call_command("seed_demo_data", stdout=io.StringIO())
    call_command("seed_demo_data", "--flush", stdout=io.StringIO())

    assert Box.objects.count() == 7
    assert Order.objects.count() == 5


def test_recommend_box_prints_trace_for_known_order():
    call_command("seed_demo_data", stdout=io.StringIO())
    out = io.StringIO()

    call_command("recommend_box", "--order", "DEMO-001", stdout=out)

    output = out.getvalue()
    assert "Order DEMO-001" in output
    assert "SINGLE_BOX" in output
    assert "SELECTED" in output


def test_recommend_box_multi_box_order():
    call_command("seed_demo_data", stdout=io.StringIO())
    out = io.StringIO()

    call_command("recommend_box", "--order", "DEMO-004", stdout=out)

    assert "MULTI_BOX" in out.getvalue()


def test_recommend_box_no_fit_order():
    call_command("seed_demo_data", stdout=io.StringIO())
    out = io.StringIO()

    call_command("recommend_box", "--order", "DEMO-005", stdout=out)

    assert "No box (or combination) fits" in out.getvalue()


def test_recommend_box_unknown_order_raises_command_error():
    with pytest.raises(CommandError, match="No order with reference"):
        call_command("recommend_box", "--order", "GHOST-999", stdout=io.StringIO())
