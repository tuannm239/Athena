"""Risk report — must exist before any optimization (risk before return)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from shared_kernel.lineage import Lineage


@dataclass(frozen=True, slots=True)
class Exposure:
    dimension: str          # e.g. "sector:technology", "currency:USD"
    weight: Decimal         # fraction of portfolio value

    def __post_init__(self) -> None:
        if not self.dimension:
            raise ValueError("dimension must not be empty")


@dataclass(frozen=True)
class RiskReport:
    exposures: tuple[Exposure, ...]
    max_drawdown_estimate: Decimal   # fraction, e.g. 0.25
    concentration_flag: bool
    lineage: Lineage

    def __post_init__(self) -> None:
        if not (Decimal(0) <= self.max_drawdown_estimate <= Decimal(1)):
            raise ValueError("max_drawdown_estimate must be within [0, 1]")
