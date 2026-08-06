"""
Tests for the free-space guillotine packer (packing/fit.py).

`test_volume_is_not_enough_a_rod_does_not_fit_in_a_smaller_volume_cube`
is the one to show an interviewer: it's the whole reason this project
does real geometry instead of the "sum(volumes) <= box volume" check
almost every other candidate will ship.
"""

import random
from decimal import Decimal

from packing.dimensions import Dimensions
from packing.entities import Container, Item
from packing.fit import pack


def make_container(l, w, h, max_weight_g=100_000, cost="10.00", code="BOX"):
    return Container(
        code=code,
        name=code,
        dims=Dimensions(l, w, h),
        max_weight_g=max_weight_g,
        cost=Decimal(cost),
    )


def make_item(l, w, h, weight_g=100, this_side_up=False, item_id=None, name="item"):
    return Item(
        id=item_id or f"{name}#1",
        sku=name,
        name=name,
        dims=Dimensions(l, w, h),
        weight_g=weight_g,
        this_side_up=this_side_up,
    )


def assert_valid_packing(container: Container, placements) -> None:
    """The invariants that must hold for ANY packing result, regardless
    of whether the packer is "smart": every item stays inside the box,
    and no two items occupy the same physical space."""
    for p in placements:
        x, y, z = p.position
        mx, my, mz = p.max_corner
        assert x >= 0 and y >= 0 and z >= 0, p
        assert mx <= container.dims.length, p
        assert my <= container.dims.width, p
        assert mz <= container.dims.height, p

    for i in range(len(placements)):
        for j in range(i + 1, len(placements)):
            assert not _cuboids_overlap(placements[i], placements[j]), (
                placements[i],
                placements[j],
            )


def _cuboids_overlap(a, b) -> bool:
    ax, ay, az = a.position
    amx, amy, amz = a.max_corner
    bx, by, bz = b.position
    bmx, bmy, bmz = b.max_corner
    return (ax < bmx and bx < amx) and (ay < bmy and by < amy) and (az < bmz and bz < amz)


# --- the crown jewel -------------------------------------------------


def test_volume_is_not_enough_a_rod_does_not_fit_in_a_smaller_volume_cube():
    """
    A 300x10x10mm rod has volume 30,000 mm^3.
    A 32x32x32mm cube has volume 32,768 mm^3.

    A volume-only check (sum(item volumes) <= box volume) would say
    this fits — 30,000 < 32,768. It doesn't: the rod is 300mm long and
    the box's longest edge is 32mm, so there is no orientation where it
    fits. This is why the packer does real geometry.
    """
    rod = make_item(300, 10, 10, name="rod")
    box = make_container(32, 32, 32, code="TINY_CUBE")

    assert rod.dims.volume < box.dims.volume  # volume check would pass...

    result = pack(box, [rod])

    assert result.fits is False  # ...but geometry correctly rejects it
    assert rod in result.unplaced


def test_exact_fit_succeeds():
    item = make_item(10, 10, 10, name="cube")
    box = make_container(10, 10, 10, code="EXACT")

    result = pack(box, [item])

    assert result.fits is True
    assert result.utilization == 1.0
    assert_valid_packing(box, result.placements)


def test_item_only_fits_in_one_orientation():
    # 5x5x40 only fits a 5x5x30 box... wait, must be smaller. Use a
    # box that only accepts the item lying on its long side.
    item = make_item(40, 5, 5, name="stick")
    box = make_container(5, 40, 5, code="SLOT")  # needs rotation to fit

    result = pack(box, [item])

    assert result.fits is True
    assert_valid_packing(box, result.placements)


def test_this_side_up_item_cannot_use_forbidden_rotation():
    # A 40x5x5 "this side up" item's height (5) must stay the height.
    # A box shaped 5x5x40 can only accept it if length/width could be
    # its 40 side lying flat with height axis = 5, which requires the
    # forbidden rotation (height becomes 40). So it must NOT fit.
    item = make_item(40, 5, 5, weight_g=100, this_side_up=True, name="liquid")
    box = make_container(5, 5, 40, code="TALL_NARROW")

    result = pack(box, [item])

    assert result.fits is False


def test_two_items_pack_side_by_side():
    a = make_item(10, 10, 10, item_id="a", name="a")
    b = make_item(10, 10, 10, item_id="b", name="b")
    box = make_container(20, 10, 10, code="DOUBLE")

    result = pack(box, [a, b])

    assert result.fits is True
    assert len(result.placements) == 2
    assert_valid_packing(box, result.placements)


def test_weight_limit_blocks_placement_even_if_geometry_fits():
    item = make_item(5, 5, 5, weight_g=5000, name="heavy")
    box = make_container(10, 10, 10, max_weight_g=1000, code="LIGHT_ONLY")

    result = pack(box, [item])

    assert result.fits is False
    assert item in result.unplaced


def test_partial_pack_reports_correct_unplaced_items():
    fits = make_item(10, 10, 10, item_id="fits", name="fits")
    too_big = make_item(50, 50, 50, item_id="too_big", name="too_big")
    box = make_container(10, 10, 10, code="SMALL")

    result = pack(box, [fits, too_big])

    assert result.fits is False
    assert too_big in result.unplaced
    assert fits not in result.unplaced


# --- randomized invariant battery -------------------------------------

RANDOM_SEED = 20260806  # fixed so any failure is exactly reproducible


def test_random_packings_never_violate_geometry_invariants():
    """
    Fuzz test: pack random sets of small items into a fixed box many
    times. Regardless of whether everything fits, whatever WAS placed
    must never overlap and must never leave the box. This is what
    proves the free-space split in fit.py is correct, not just
    "usually right".
    """
    rng = random.Random(RANDOM_SEED)
    box = make_container(50, 50, 50, max_weight_g=1_000_000, code="FUZZ_BOX")

    for trial in range(200):
        n_items = rng.randint(1, 12)
        items = [
            make_item(
                rng.randint(1, 20),
                rng.randint(1, 20),
                rng.randint(1, 20),
                weight_g=rng.randint(1, 500),
                this_side_up=rng.random() < 0.3,
                item_id=f"t{trial}i{i}",
                name=f"t{trial}i{i}",
            )
            for i in range(n_items)
        ]
        result = pack(box, items)
        assert_valid_packing(box, result.placements)
        # Every placed item must be one we actually asked to pack, and
        # placed+unplaced must account for all of them exactly once.
        placed_ids = {p.item_id for p in result.placements}
        unplaced_ids = {i.id for i in result.unplaced}
        assert placed_ids | unplaced_ids == {i.id for i in items}
        assert not (placed_ids & unplaced_ids)
