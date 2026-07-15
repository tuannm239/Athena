"""Risk report — the Risk Engine's output contract (SPEC-11, Outputs).

Risk management always takes precedence over return optimization
(Constitution, Product Principle 2).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from risk.domain.risk_assessment import RiskLevel


@dataclass(frozen=True, slots=True)
class RiskReport:
    overall_risk: RiskLevel
    var: Decimal
    cvar: Decimal
    drawdown: Decimal
    liquidity: Decimal
    violations: tuple[str, ...]
    recommendations: tuple[str, ...]
    explanation: str

    def __post_init__(self) -> None:
        if not self.explanation:
            raise ValueError("risk report requires an explanation (explainability)")
