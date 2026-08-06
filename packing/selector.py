"""
The box-selection funnel.

`select_box()` is the single entry point the rest of the system calls.
It runs every candidate box through 4 cheap-to-expensive stages, keeps
a verdict for every one of them (see trace.py), and picks a winner.

Stage order matters and is deliberate: cheap O(1) checks (weight,
total volume, "does this one item even fit any box") run first and
reject the obviously-impossible boxes before we pay for the expensive
geometric simulation. See docs/ALGORITHM.md.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from packing.dimensions import rotations
from packing.entities import Container, FitResult, Item
from packing.fit import pack
from packing.trace import BoxVerdict, Stage, Verdict


@dataclass(frozen=True)
class SelectionResult:
    strategy: str  # "SINGLE_BOX" | "NO_FIT" (multi-box handled in multibox.py)
    recommended_box: Container | None
    fit_result: FitResult | None
    verdicts: tuple[BoxVerdict, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "strategy": self.strategy,
            "recommended": (
                {
                    "box": self.recommended_box.code,
                    "box_name": self.recommended_box.name,
                    "cost": str(self.recommended_box.cost),
                    "utilization": self.fit_result.utilization,
                }
                if self.recommended_box and self.fit_result
                else None
            ),
            "evaluated": [v.to_dict() for v in self.verdicts],
        }


def _item_fits_any_rotation(item: Item, container: Container) -> bool:
    return any(
        rotated.fits_within(container.dims)
        for rotated in rotations(item.dims, item.this_side_up)
    )


def evaluate_box(container: Container, items: list[Item]) -> tuple[BoxVerdict, FitResult | None]:
    """Run one box through the funnel. Returns its verdict, and the
    FitResult if geometry was actually simulated (None otherwise —
    no point simulating a box we already know is too small)."""

    total_weight = sum(item.weight_g for item in items)
    if total_weight > container.max_weight_g:
        return (
            BoxVerdict(
                box_code=container.code,
                box_name=container.name,
                verdict=Verdict.REJECTED,
                stage=Stage.WEIGHT,
                reason=(
                    f"Order weighs {total_weight / 1000:.2f} kg; "
                    f"box {container.code} holds {container.max_weight_g / 1000:.2f} kg"
                ),
            ),
            None,
        )

    total_item_volume = sum(item.dims.volume for item in items)
    if total_item_volume > container.dims.volume:
        return (
            BoxVerdict(
                box_code=container.code,
                box_name=container.name,
                verdict=Verdict.REJECTED,
                stage=Stage.VOLUME,
                reason=(
                    f"Items total {total_item_volume:,} mm³; "
                    f"box {container.code} interior is only {container.dims.volume:,} mm³"
                ),
            ),
            None,
        )

    for item in items:
        if not _item_fits_any_rotation(item, container):
            return (
                BoxVerdict(
                    box_code=container.code,
                    box_name=container.name,
                    verdict=Verdict.REJECTED,
                    stage=Stage.ITEM_TOO_LARGE,
                    reason=(
                        f"'{item.name}' ({item.dims.length}x{item.dims.width}x"
                        f"{item.dims.height} mm) fits in no orientation inside "
                        f"box {container.code} "
                        f"({container.dims.length}x{container.dims.width}x"
                        f"{container.dims.height} mm)"
                    ),
                ),
                None,
            )

    fit_result = pack(container, items)
    if not fit_result.fits:
        unplaced_names = ", ".join(sorted({i.name for i in fit_result.unplaced}))
        return (
            BoxVerdict(
                box_code=container.code,
                box_name=container.name,
                verdict=Verdict.REJECTED,
                stage=Stage.GEOMETRY,
                reason=(
                    f"All items individually fit, and total volume fits, but "
                    f"they can't be simultaneously arranged inside box "
                    f"{container.code} — no space left for: {unplaced_names}"
                ),
            ),
            fit_result,
        )

    return (
        BoxVerdict(
            box_code=container.code,
            box_name=container.name,
            verdict=Verdict.FITS_BUT_COSTLIER,  # provisional; selector.py fixes up the winner
            stage=Stage.SELECTION,
            reason="Fits. Not selected — see recommended box.",
            cost=container.cost,
            utilization=fit_result.utilization,
        ),
        fit_result,
    )


def select_box(containers: list[Container], items: list[Item]) -> SelectionResult:
    """Evaluate every catalogue box and pick the cheapest that
    physically fits everything. Tie-break: highest utilization (tighter
    pack = less wasted dimensional weight), then box code, so results
    are 100% deterministic."""

    verdicts: list[BoxVerdict] = []
    feasible: list[tuple[Container, FitResult, BoxVerdict]] = []

    for container in sorted(containers, key=lambda c: c.code):
        verdict, fit_result = evaluate_box(container, items)
        verdicts.append(verdict)
        if verdict.verdict != Verdict.REJECTED and fit_result is not None:
            feasible.append((container, fit_result, verdict))

    if not feasible:
        return SelectionResult(
            strategy="NO_FIT",
            recommended_box=None,
            fit_result=None,
            verdicts=tuple(verdicts),
        )

    def sort_key(entry: tuple[Container, FitResult, BoxVerdict]) -> tuple[Decimal, float, str]:
        container, fit_result, _ = entry
        return (container.cost, -fit_result.utilization, container.code)

    feasible.sort(key=sort_key)
    winner_container, winner_fit, _ = feasible[0]

    final_verdicts = []
    for verdict in verdicts:
        if verdict.box_code == winner_container.code:
            final_verdicts.append(
                BoxVerdict(
                    box_code=verdict.box_code,
                    box_name=verdict.box_name,
                    verdict=Verdict.SELECTED,
                    stage=Stage.SELECTION,
                    reason=(
                        f"Cheapest box that fits everything "
                        f"(cost={winner_container.cost}, "
                        f"utilization={winner_fit.utilization:.0%})"
                    ),
                    cost=verdict.cost,
                    utilization=verdict.utilization,
                )
            )
        elif verdict.verdict == Verdict.FITS_BUT_COSTLIER and verdict.cost == winner_container.cost:
            final_verdicts.append(
                BoxVerdict(
                    box_code=verdict.box_code,
                    box_name=verdict.box_name,
                    verdict=Verdict.FITS_BUT_LOWER_UTILIZATION,
                    stage=Stage.SELECTION,
                    reason=(
                        f"Same cost as the selected box but packs less "
                        f"tightly ({verdict.utilization:.0%} vs "
                        f"{winner_fit.utilization:.0%} utilization)"
                    ),
                    cost=verdict.cost,
                    utilization=verdict.utilization,
                )
            )
        else:
            final_verdicts.append(verdict)

    return SelectionResult(
        strategy="SINGLE_BOX",
        recommended_box=winner_container,
        fit_result=winner_fit,
        verdicts=tuple(final_verdicts),
    )
