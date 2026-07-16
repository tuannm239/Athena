"""Decision Object — the kernel's output contract (RFC-0020 §6; directive).

Deterministic, reproducible, explainable. Decision types remain
evaluation outcomes assigned by humans or rules — never trading
instructions (SPEC-04).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from risk.domain.risk_assessment import RiskAssessment
from shared_kernel.identifiers import DecisionId
from shared_kernel.probability import Confidence, Probability


@dataclass(frozen=True, slots=True)
class KernelExplanation:
    """SPEC-04 §Explainability: the six mandatory facets."""

    why: tuple[str, ...]
    why_not: tuple[str, ...]
    assumptions: tuple[str, ...]
    missing_information: tuple[str, ...]
    key_risks: tuple[str, ...]
    alternative_scenarios: tuple[str, ...]

    def render(self) -> str:
        parts = [
            "WHY: " + ("; ".join(self.why) or "—"),
            "WHY NOT: " + ("; ".join(self.why_not) or "—"),
            "ASSUMPTIONS: " + ("; ".join(self.assumptions) or "—"),
            "MISSING: " + ("; ".join(self.missing_information) or "—"),
            "KEY RISKS: " + ("; ".join(self.key_risks) or "—"),
            "ALTERNATIVES: " + ("; ".join(self.alternative_scenarios) or "—"),
        ]
        return " | ".join(parts)


@dataclass(frozen=True, slots=True)
class DecisionObject:
    decision_id: DecisionId
    hypothesis: str
    evidence: tuple[str, ...]
    counter_evidence: tuple[str, ...]
    matched_rules: tuple[str, ...]
    probability: Probability
    confidence: Confidence
    expected_return: Decimal | None
    expected_drawdown: Decimal | None
    expected_utility: Decimal
    risk_adjustment: Decimal
    risk_assessment: RiskAssessment
    portfolio_impact: str
    position_size: Decimal
    tags: tuple[str, ...]
    assumptions: tuple[str, ...]
    invalidation_conditions: tuple[str, ...]
    compiler_version: str
    explanation: KernelExplanation

    def __post_init__(self) -> None:
        if not self.hypothesis:
            raise ValueError("decision object requires a hypothesis")
