from decimal import Decimal

from packing.dimensions import Dimensions
from packing.entities import Container, Item
from packing.selector import select_box
from packing.trace import Stage, Verdict


def box(code, l, w, h, max_weight_g=10_000, cost="10.00"):
    return Container(
        code=code,
        name=f"Box {code}",
        dims=Dimensions(l, w, h),
        max_weight_g=max_weight_g,
        cost=Decimal(cost),
    )


def item(sku, l, w, h, weight_g=100, this_side_up=False):
    return Item(
        id=f"{sku}#1",
        sku=sku,
        name=sku,
        dims=Dimensions(l, w, h),
        weight_g=weight_g,
        this_side_up=this_side_up,
    )


CATALOGUE = [
    box("S", 10, 10, 10, max_weight_g=2000, cost="20.00"),
    box("M", 20, 20, 20, max_weight_g=5000, cost="45.00"),
    box("L", 40, 40, 40, max_weight_g=10000, cost="80.00"),
]


def test_selects_cheapest_box_that_fits():
    result = select_box(CATALOGUE, [item("mug", 8, 8, 8, weight_g=300)])

    assert result.strategy == "SINGLE_BOX"
    assert result.recommended_box.code == "S"

    selected = [v for v in result.verdicts if v.verdict == Verdict.SELECTED]
    assert len(selected) == 1
    assert selected[0].box_code == "S"


def test_rejects_boxes_too_small_by_weight_before_running_geometry():
    result = select_box(CATALOGUE, [item("weight", 5, 5, 5, weight_g=3000)])

    s_verdict = next(v for v in result.verdicts if v.box_code == "S")
    assert s_verdict.verdict == Verdict.REJECTED
    assert s_verdict.stage == Stage.WEIGHT
    assert result.recommended_box.code == "M"


def test_rejects_box_when_item_too_large_for_any_rotation():
    result = select_box(CATALOGUE, [item("pole", 35, 2, 2, weight_g=100)])

    s_verdict = next(v for v in result.verdicts if v.box_code == "S")
    m_verdict = next(v for v in result.verdicts if v.box_code == "M")
    assert s_verdict.stage == Stage.ITEM_TOO_LARGE
    assert m_verdict.stage == Stage.ITEM_TOO_LARGE
    assert result.recommended_box.code == "L"


def test_trace_includes_every_box_in_catalogue():
    result = select_box(CATALOGUE, [item("mug", 8, 8, 8, weight_g=300)])
    assert {v.box_code for v in result.verdicts} == {"S", "M", "L"}


def test_no_fit_when_nothing_in_catalogue_can_hold_the_order():
    result = select_box(CATALOGUE, [item("giant", 100, 100, 100, weight_g=100)])
    assert result.strategy == "NO_FIT"
    assert result.recommended_box is None
    assert all(v.verdict == Verdict.REJECTED for v in result.verdicts)


def test_tie_break_prefers_higher_utilization_at_equal_cost():
    same_cost = [
        box("A", 10, 10, 10, cost="30.00"),
        box("B", 20, 20, 20, cost="30.00"),
    ]
    # Item fills box A almost completely but only a fraction of box B.
    result = select_box(same_cost, [item("cube", 9, 9, 9, weight_g=100)])
    assert result.recommended_box.code == "A"


def test_geometric_rejection_when_items_individually_fit_but_not_together():
    # Two 6x6x6 cubes: each individually fits a 10x10x6 box (trivially,
    # 6 <= 10 on every axis), and their combined volume (432 mm^3) is
    # well under the box's 600 mm^3 interior. But two cubes side by
    # side need 12mm on some axis, and the box's largest axis is only
    # 10mm — there is no way to arrange both at once. This is what the
    # ITEM_TOO_LARGE and VOLUME stages CAN'T catch; only the geometric
    # simulation can.
    tight_box = [box("TIGHT", 10, 10, 6, max_weight_g=10_000, cost="15.00")]
    items = [item("cube_a", 6, 6, 6), item("cube_b", 6, 6, 6)]

    result = select_box(tight_box, items)

    tight_verdict = result.verdicts[0]
    assert tight_verdict.verdict == Verdict.REJECTED
    assert tight_verdict.stage == Stage.GEOMETRY
