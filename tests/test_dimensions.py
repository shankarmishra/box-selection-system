import pytest

from packing.dimensions import Dimensions, rotations


def test_dimensions_rejects_non_positive():
    with pytest.raises(ValueError):
        Dimensions(0, 5, 5)
    with pytest.raises(ValueError):
        Dimensions(5, -1, 5)


def test_volume():
    assert Dimensions(2, 3, 4).volume == 24


def test_fits_within_no_rotation():
    assert Dimensions(2, 3, 4).fits_within(Dimensions(2, 3, 4))
    assert Dimensions(2, 3, 4).fits_within(Dimensions(5, 5, 5))
    assert not Dimensions(2, 3, 4).fits_within(Dimensions(2, 3, 3))


def test_free_item_has_six_rotations_when_all_sides_differ():
    dims = Dimensions(1, 2, 3)
    assert len(rotations(dims)) == 6
    assert set(rotations(dims)) == {
        Dimensions(1, 2, 3),
        Dimensions(1, 3, 2),
        Dimensions(2, 1, 3),
        Dimensions(2, 3, 1),
        Dimensions(3, 1, 2),
        Dimensions(3, 2, 1),
    }


def test_cube_has_exactly_one_distinct_rotation():
    # All 6 permutations of a cube collapse to the same shape.
    dims = Dimensions(5, 5, 5)
    assert rotations(dims) == (Dimensions(5, 5, 5),)


def test_this_side_up_restricts_to_two_rotations():
    dims = Dimensions(1, 2, 3)
    rots = rotations(dims, this_side_up=True)
    assert set(rots) == {Dimensions(1, 2, 3), Dimensions(2, 1, 3)}
    # height (3) must never move to a different axis
    assert all(r.height == 3 for r in rots)


def test_this_side_up_cube_base_has_one_rotation():
    dims = Dimensions(4, 4, 7)
    rots = rotations(dims, this_side_up=True)
    assert rots == (Dimensions(4, 4, 7),)
