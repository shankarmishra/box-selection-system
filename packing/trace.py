"""
Explainability types.

The whole point of `selector.py` is that it doesn't just return a
winning box — it returns a verdict for EVERY box in the catalogue, with
a human-readable reason. This is what a warehouse operator (or an
interviewer) reads to understand why box S was skipped in favour of
box M.
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class Stage(str, Enum):
    """Which stage of the funnel produced this verdict. Ordered cheapest
    (fastest to check) to most expensive, matching the order selector.py
    actually runs them in."""

    WEIGHT = "weight"
    VOLUME = "volume"
    ITEM_TOO_LARGE = "item_too_large"
    GEOMETRY = "geometry"
    SELECTION = "selection"


class Verdict(str, Enum):
    SELECTED = "SELECTED"
    FITS_BUT_COSTLIER = "FITS_BUT_COSTLIER"
    FITS_BUT_LOWER_UTILIZATION = "FITS_BUT_LOWER_UTILIZATION"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class BoxVerdict:
    """One catalogue box's outcome for one order."""

    box_code: str
    box_name: str
    verdict: Verdict
    stage: Stage
    reason: str
    cost: Decimal | None = None
    utilization: float | None = None

    def to_dict(self) -> dict:
        return {
            "box": self.box_code,
            "box_name": self.box_name,
            "verdict": self.verdict.value,
            "stage": self.stage.value,
            "reason": self.reason,
            "cost": str(self.cost) if self.cost is not None else None,
            "utilization": self.utilization,
        }
