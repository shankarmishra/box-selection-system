"""
Multi-box fallback: what to do when no single catalogue box can hold
the whole order.

Optimal multi-bin packing is NP-hard and overkill for a warehouse tool,
so this uses a greedy heuristic that's easy to explain out loud:

    Repeat: figure out, for each box type, how much of the REMAINING
    items it could pack (a full geometric simulation, not a guess).
    Use one of whichever box type packs the most volume per rupee of
    cost. Remove those items. Repeat until nothing is left, or a round
    packs nothing (meaning some item literally fits no box at all).

This is the standard "best-fit-decreasing over bin types" heuristic
adapted to run the real 3D packer as its scoring function instead of a
1D volume estimate — so it inherits the same false-positive-proof
guarantee as the single-box path.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from packing.entities import Container, Item, Placement
from packing.fit import pack


@dataclass(frozen=True)
class BoxUnit:
    """One physical box used in a multi-box shipment."""

    container: Container
    placements: tuple[Placement, ...]
    utilization: float


@dataclass(frozen=True)
class MultiBoxResult:
    units: tuple[BoxUnit, ...] = field(default_factory=tuple)
    unresolved_items: tuple[Item, ...] = field(default_factory=tuple)

    @property
    def total_cost(self) -> Decimal:
        return sum((unit.container.cost for unit in self.units), Decimal("0"))

    @property
    def fits(self) -> bool:
        return not self.unresolved_items

    def to_dict(self) -> dict:
        return {
            "strategy": "MULTI_BOX",
            "box_count": len(self.units),
            "total_cost": str(self.total_cost),
            "boxes": [
                {
                    "box": unit.container.code,
                    "box_name": unit.container.name,
                    "cost": str(unit.container.cost),
                    "utilization": unit.utilization,
                    "items": [p.sku for p in unit.placements],
                }
                for unit in self.units
            ],
            "unresolved_items": [item.sku for item in self.unresolved_items],
        }


def pack_multi_box(
    containers: list[Container],
    items: list[Item],
    max_boxes: int = 25,
) -> MultiBoxResult:
    remaining = list(items)
    units: list[BoxUnit] = []

    while remaining and len(units) < max_boxes:
        best_round: tuple[float, Container, object] | None = None  # (value, box, fit_result)

        for container in containers:
            fit_result = pack(container, remaining)
            packed_count = len(fit_result.placements)
            if packed_count == 0:
                continue
            packed_volume = sum(p.placed_dims.volume for p in fit_result.placements)
            value = packed_volume / float(container.cost) if container.cost else packed_volume
            # Prefer highest value-per-cost; tie-break on packing more items
            # in this single box (fewer boxes shipped overall).
            score = (value, packed_count)
            if best_round is None or score > (best_round[0], len(best_round[2].placements)):
                best_round = (value, container, fit_result)

        if best_round is None:
            # Nothing packed a single item this round — whatever's left
            # doesn't fit in ANY box, in any combination.
            break

        _, chosen_container, chosen_fit = best_round
        units.append(
            BoxUnit(
                container=chosen_container,
                placements=chosen_fit.placements,
                utilization=chosen_fit.utilization,
            )
        )
        placed_ids = {p.item_id for p in chosen_fit.placements}
        remaining = [item for item in remaining if item.id not in placed_ids]

    return MultiBoxResult(units=tuple(units), unresolved_items=tuple(remaining))
