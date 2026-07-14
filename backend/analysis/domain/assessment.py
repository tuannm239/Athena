"""Probabilistic assessments with explainable drivers.

Explainability rule: an assessment without drivers is invalid —
black-box outputs cannot enter the pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from shared_kernel.identifiers import InstrumentId
from shared_kernel.lineage import Lineage
from shared_kernel.probability import Probability


@dataclass(frozen=True, slots=True)
class Driver:
    """A named contribution to an assessment (e.g. SHAP-style attribution)."""

    name: str
    contribution: Decimal

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("driver name must not be empty")


@dataclass(frozen=True)
class CompanyAssessment:
    instrument_id: InstrumentId
    outperformance_probability: Probability
    drivers: tuple[Driver, ...]
    lineage: Lineage

    def __post_init__(self) -> None:
        if not self.drivers:
            raise ValueError("assessment requires at least one driver (explainability)")
