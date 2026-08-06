"""
Integer-millimetre cuboid dimensions and their rotations.

Everything in this package is measured in **integer millimetres** (and
integer grams for weight). That's a deliberate choice over floats: box
fit comparisons are pure `<=` on whole numbers, so there's no epsilon
fuzz anywhere in the geometry. See docs/DESIGN_DECISIONS.md.
"""

from dataclasses import dataclass
from itertools import permutations


@dataclass(frozen=True, order=True)
class Dimensions:
    """A cuboid's size in millimetres. Order doesn't matter for equality
    of *shape* (10x5x2 is the same shape as 2x5x10) but this class keeps
    the axes as given — callers ask for `rotations()` to enumerate the
    ways it can be turned."""

    length: int
    width: int
    height: int

    def __post_init__(self):
        if self.length <= 0 or self.width <= 0 or self.height <= 0:
            raise ValueError(
                f"Dimensions must be positive, got "
                f"({self.length}, {self.width}, {self.height})"
            )

    @property
    def volume(self) -> int:
        return self.length * self.width * self.height

    def fits_within(self, other: "Dimensions") -> bool:
        """True if this cuboid fits inside `other` with NO rotation."""
        return (
            self.length <= other.length
            and self.width <= other.width
            and self.height <= other.height
        )


def rotations(dims: Dimensions, this_side_up: bool = False) -> tuple[Dimensions, ...]:
    """
    Every distinct axis-aligned orientation of `dims`.

    - Free items may be rotated onto any of their 6 faces (all
      permutations of length/width/height).
    - `this_side_up` items (liquids, fragile-and-marked items) may only
      be spun around the vertical axis — the height stays the height,
      only length and width can swap. That's 2 orientations, not 6.

    Duplicate shapes (e.g. a cube, or a box with two equal sides)
    collapse naturally since we dedupe — this keeps the fit search from
    wasting time on orientations that are geometrically identical.
    """
    if this_side_up:
        raw = [
            (dims.length, dims.width, dims.height),
            (dims.width, dims.length, dims.height),
        ]
    else:
        raw = list(permutations((dims.length, dims.width, dims.height)))

    seen: set[tuple[int, int, int]] = set()
    result = []
    for l, w, h in raw:
        if (l, w, h) not in seen:
            seen.add((l, w, h))
            result.append(Dimensions(l, w, h))
    return tuple(result)
