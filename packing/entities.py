"""Plain-data entities shared across the packing engine.

None of these know about Django's ORM — `warehouse/services.py` is the
only place that converts model instances into these dataclasses and
back.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from packing.dimensions import Dimensions


@dataclass(frozen=True)
class Item:
    """One physical thing that needs to go in a box. If an order line
    has quantity=3, it gets expanded into 3 separate Items upstream —
    the packer only ever deals with individual, indivisible objects."""

    id: str  # unique per expanded unit, e.g. "SKU123#2"
    sku: str
    name: str
    dims: Dimensions
    weight_g: int
    this_side_up: bool = False
    fragile: bool = False


@dataclass(frozen=True)
class Container:
    """A candidate shipping box."""

    code: str
    name: str
    dims: Dimensions
    max_weight_g: int
    cost: Decimal


@dataclass(frozen=True)
class Placement:
    """Where one Item ended up inside a Container, after the fit engine
    picked an orientation and a slot for it."""

    item_id: str
    sku: str
    name: str
    position: tuple[int, int, int]  # (x, y, z) of the item's min corner
    placed_dims: Dimensions  # dims AFTER rotation

    @property
    def max_corner(self) -> tuple[int, int, int]:
        x, y, z = self.position
        return (
            x + self.placed_dims.length,
            y + self.placed_dims.width,
            z + self.placed_dims.height,
        )


@dataclass(frozen=True)
class FitResult:
    """Result of trying to pack a set of Items into one Container."""

    fits: bool
    placements: tuple[Placement, ...] = field(default_factory=tuple)
    unplaced: tuple[Item, ...] = field(default_factory=tuple)
    utilization: float = 0.0  # packed volume / container interior volume
