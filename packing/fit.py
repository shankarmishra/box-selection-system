"""
The free-space (guillotine) 3D bin-packing engine.

This is the piece that separates this project from "does the volume
add up?" — see docs/ALGORITHM.md for the full write-up with diagrams.
The short version:

1. Start with ONE free cuboid: the whole container interior.
2. For each item (largest first), try every free cuboid x every
   allowed rotation, and place it in whichever (space, rotation)
   combination wastes the least volume.
3. Placing an item always uses the free space's minimum corner. That
   lets us split the *remaining* volume of that space into exactly 3
   new non-overlapping cuboids (see `_split`) — so the free-space list
   never contains overlapping regions, which is what stops the packer
   from ever reporting two items in the same physical spot.
4. Anything that can't be placed anywhere is returned as `unplaced`.

This is a "first-fit, best-leftover" guillotine packer, not an optimal
3D bin-packer (that's NP-hard). It is deliberately conservative: it can
under-pack (reject a box that a cleverer algorithm could still fit
items into) but it can never over-pack (claim a fit that's physically
impossible). See docs/ALGORITHM.md for why that asymmetry is the right
one for a warehouse tool.
"""

from dataclasses import dataclass

from packing.dimensions import Dimensions, rotations
from packing.entities import Container, FitResult, Item, Placement


@dataclass(frozen=True)
class _FreeSpace:
    """A candidate empty cuboid inside the container, anchored at
    (x, y, z) with size (dims)."""

    x: int
    y: int
    z: int
    dims: Dimensions


def _split(space: _FreeSpace, placed: Dimensions) -> list[_FreeSpace]:
    """
    Partition `space` minus the `placed` cuboid (placed at space's own
    min corner) into up to 3 disjoint free cuboids.

    Proof this never overlaps and never double-counts volume: label the
    original space's size (L, W, H) and the placed item's size (l, w, h).

        A (x-remainder): origin (x+l, y,   z),   size (L-l, W,   H)
        B (y-remainder): origin (x,   y+w, z),   size (l,   W-w, H)
        C (z-remainder): origin (x,   y,   z+h), size (l,   w,   H-h)

    A's x-range is [x+l, x+L) — entirely outside where B and C live.
    B's y-range is [y+w, y+W) — entirely outside where C lives.
    So A, B, C, and the placed block are pairwise disjoint, and their
    volumes sum to exactly L*W*H (expand it — the cross terms cancel).
    Degenerate (zero-volume) regions are dropped.
    """
    x, y, z = space.x, space.y, space.z
    bigL, bigW, bigH = space.dims.length, space.dims.width, space.dims.height
    l, w, h = placed.length, placed.width, placed.height

    out = []
    if bigL - l > 0:
        out.append(_FreeSpace(x + l, y, z, Dimensions(bigL - l, bigW, bigH)))
    if bigW - w > 0:
        out.append(_FreeSpace(x, y + w, z, Dimensions(l, bigW - w, bigH)))
    if bigH - h > 0:
        out.append(_FreeSpace(x, y, z + h, Dimensions(l, w, bigH - h)))
    return out


def pack(
    container: Container,
    items: list[Item],
    max_weight_g: int | None = None,
) -> FitResult:
    """
    Try to place every item inside one `container`.

    `max_weight_g` defaults to `container.max_weight_g`; callers doing
    multi-box splitting can pass a smaller *remaining* capacity so the
    packer also respects a partially-filled box's leftover weight budget.
    """
    weight_limit = container.max_weight_g if max_weight_g is None else max_weight_g

    ordered = sorted(items, key=lambda it: it.dims.volume, reverse=True)

    free_spaces: list[_FreeSpace] = [
        _FreeSpace(0, 0, 0, container.dims),
    ]
    placements: list[Placement] = []
    unplaced: list[Item] = []
    used_weight = 0
    placed_volume = 0

    for item in ordered:
        if used_weight + item.weight_g > weight_limit:
            unplaced.append(item)
            continue

        best = None  # (leftover_volume, space_index, rotated_dims)
        for idx, space in enumerate(free_spaces):
            for rotated in rotations(item.dims, item.this_side_up):
                if rotated.fits_within(space.dims):
                    leftover = space.dims.volume - rotated.volume
                    if best is None or leftover < best[0]:
                        best = (leftover, idx, rotated)

        if best is None:
            unplaced.append(item)
            continue

        _, idx, rotated = best
        space = free_spaces.pop(idx)
        placements.append(
            Placement(
                item_id=item.id,
                sku=item.sku,
                name=item.name,
                position=(space.x, space.y, space.z),
                placed_dims=rotated,
            )
        )
        used_weight += item.weight_g
        placed_volume += rotated.volume
        free_spaces.extend(_split(space, rotated))

    utilization = placed_volume / container.dims.volume if container.dims.volume else 0.0

    return FitResult(
        fits=not unplaced,
        placements=tuple(placements),
        unplaced=tuple(unplaced),
        utilization=round(utilization, 4),
    )
