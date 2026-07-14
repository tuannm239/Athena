"""Portfolio aggregate and candidate target portfolios.

Invariant: target weights are non-negative and sum to 1.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping

from shared_kernel.identifiers import InstrumentId
from shared_kernel.lineage import Lineage

_TOL = Decimal("0.000001")


class WeightError(ValueError):
    """Raised when target weights violate portfolio invariants."""


@dataclass(frozen=True)
class TargetPortfolio:
    weights: Mapping[InstrumentId, Decimal]
    lineage: Lineage

    def __post_init__(self) -> None:
        if not self.weights:
            raise WeightError("target portfolio must not be empty")
        if any(w < 0 for w in self.weights.values()):
            raise WeightError("weights must be non-negative (long-only v1)")
        total = sum(self.weights.values())
        if abs(total - Decimal(1)) > _TOL:
            raise WeightError(f"weights must sum to 1, got {total}")
