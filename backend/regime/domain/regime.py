"""Market regime assessment.

Invariant (SPEC-03 §5): downstream analysis must condition on a
RegimeAssessment; the assessment always carries lineage.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from shared_kernel.lineage import Lineage
from shared_kernel.probability import ProbabilityDistribution


class Regime(StrEnum):
    RISK_ON = "RISK_ON"
    RISK_OFF = "RISK_OFF"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    TRANSITION = "TRANSITION"


@dataclass(frozen=True, slots=True)
class RegimeAssessment:
    distribution: ProbabilityDistribution
    lineage: Lineage

    def __post_init__(self) -> None:
        valid = {r.value for r in Regime}
        unknown = set(self.distribution.masses) - valid
        if unknown:
            raise ValueError(f"unknown regime labels: {unknown}")

    @property
    def dominant(self) -> Regime:
        return Regime(self.distribution.mode())
