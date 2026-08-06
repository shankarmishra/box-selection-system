from decimal import Decimal

from packing.dimensions import Dimensions
from packing.entities import Container, Item
from packing.multibox import pack_multi_box


def box(code, l, w, h, max_weight_g=10_000, cost="10.00"):
    return Container(
        code=code,
        name=f"Box {code}",
        dims=Dimensions(l, w, h),
        max_weight_g=max_weight_g,
        cost=Decimal(cost),
    )


def item(sku, l, w, h, weight_g=100):
    return Item(id=f"{sku}#1", sku=sku, name=sku, dims=Dimensions(l, w, h), weight_g=weight_g)


def test_splits_across_multiple_boxes_when_none_hold_everything():
    small_box = [box("S", 10, 10, 10, cost="20.00")]
    # Three 10x10x10 cubes: no single S box (10x10x10) can hold more
    # than one, so this must resolve into 3 separate boxes.
    items = [item("a", 10, 10, 10), item("b", 10, 10, 10), item("c", 10, 10, 10)]

    result = pack_multi_box(small_box, items)

    assert result.fits is True
    assert len(result.units) == 3
    assert result.total_cost == Decimal("60.00")


def test_every_item_placed_exactly_once_across_units():
    catalogue = [box("S", 10, 10, 10, cost="20.00"), box("M", 20, 20, 20, cost="45.00")]
    items = [item(f"i{n}", 5, 5, 5) for n in range(20)]

    result = pack_multi_box(catalogue, items)

    all_placed_ids = [p.item_id for unit in result.units for p in unit.placements]
    assert sorted(all_placed_ids) == sorted(i.id for i in items)
    assert len(all_placed_ids) == len(set(all_placed_ids))  # no duplicates
    assert result.fits is True


def test_unresolved_items_reported_when_something_fits_no_box_at_all():
    catalogue = [box("S", 10, 10, 10, cost="20.00")]
    items = [item("fits", 5, 5, 5), item("too_big", 50, 50, 50)]

    result = pack_multi_box(catalogue, items)

    assert result.fits is False
    assert any(i.sku == "too_big" for i in result.unresolved_items)
    placed_skus = {p.sku for unit in result.units for p in unit.placements}
    assert "fits" in placed_skus


def test_respects_max_boxes_safety_cap():
    catalogue = [box("S", 10, 10, 10, cost="20.00")]
    items = [item(f"i{n}", 10, 10, 10) for n in range(100)]

    result = pack_multi_box(catalogue, items, max_boxes=5)

    assert len(result.units) == 5
    assert not result.fits
    assert len(result.unresolved_items) == 95
