"""Decision aggregate — the only producer of final decisions.

Constitution guarantees encoded here:
- A Decision cannot exist without a RiskReport (risk before return).
- A Decision references full lineage (reproducibility).
- Overrides are recorded, never silently applied.
- This module has no dependency on any LLM gateway (enforced also in CI).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from behavior.domain.override import TriggeredOverride
from portfolio.domain.portfolio import TargetPortfolio
from risk.domain.risk_report import RiskReport
from shared_kernel.identifiers import DecisionId
from shared_kernel.lineage import Lineage


class DecisionIntegrityError(ValueError):
    """Raised when a decision would violate constitutional invariants."""


@dataclass(frozen=True)
class Decision:
    id: DecisionId
    target: TargetPortfolio
    risk_report: RiskReport
    overrides: tuple[TriggeredOverride, ...]
    lineage: Lineage
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self) -> None:
        if self.risk_report is None:  # defensive: typed, but guard anyway
            raise DecisionIntegrityError("decision requires a risk report")
        if self.target.lineage != self.lineage or self.risk_report.lineage != self.lineage:
            raise DecisionIntegrityError(
                "target and risk report must originate from the same run/snapshot"
            )
