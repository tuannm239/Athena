"""Market Regime Detection — ALG-001 (RFC-0025; SPEC-05).

Deterministic: identical inputs produce identical regime, score and
confidence. Missing indicators reduce confidence (SPEC-05) while the
score is computed over renormalized weights of the present inputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from market.domain.market_context import MarketContext, Regime
from shared_kernel.exceptions import DomainError
from shared_kernel.probability import Confidence

_HUNDRED = Decimal(100)
_ONE = Decimal(1)

WEIGHTS: dict[str, Decimal] = {
    "trend": Decimal("0.30"),
    "breadth": Decimal("0.20"),
    "liquidity": Decimal("0.20"),
    "momentum": Decimal("0.15"),
    "volatility": Decimal("0.15"),  # enters as (100 − volatility)
}


class RegimeInputError(DomainError):
    """Raised when regime inputs are invalid (out of range or all missing)."""


@dataclass(frozen=True, slots=True)
class RegimeInputs:
    """Indicator scores in 0..100 (RFC-0025 §1); None = indicator missing."""

    trend: Decimal | None = None
    breadth: Decimal | None = None
    liquidity: Decimal | None = None
    momentum: Decimal | None = None
    volatility: Decimal | None = None

    def __post_init__(self) -> None:
        for name, value in self.components().items():
            if value is not None and not (Decimal(0) <= value <= _HUNDRED):
                raise RegimeInputError(f"{name} must be in 0..100, got {value}")
        if all(value is None for value in self.components().values()):
            raise RegimeInputError("at least one indicator is required")

    def components(self) -> dict[str, Decimal | None]:
        return {
            "trend": self.trend,
            "breadth": self.breadth,
            "liquidity": self.liquidity,
            "momentum": self.momentum,
            "volatility": self.volatility,
        }

    def adjusted(self) -> dict[str, Decimal]:
        """Present components as they enter the score (volatility inverted)."""
        result: dict[str, Decimal] = {}
        for name, value in self.components().items():
            if value is None:
                continue
            result[name] = _HUNDRED - value if name == "volatility" else value
        return result


def market_score(inputs: RegimeInputs) -> Decimal:
    """RFC-0025 §2 weighted score, weights renormalized over present inputs."""
    adjusted = inputs.adjusted()
    total_weight = sum((WEIGHTS[name] for name in adjusted), Decimal(0))
    return sum(
        (WEIGHTS[name] / total_weight * value for name, value in adjusted.items()),
        Decimal(0),
    )


def classify(score: Decimal) -> Regime:
    """RFC-0025 §3 bands (inclusive lower bounds)."""
    if score >= Decimal(80):
        return Regime.EXPANSION
    if score >= Decimal(60):
        return Regime.RECOVERY
    if score >= Decimal(40):
        return Regime.CONSOLIDATION
    return Regime.CONTRACTION


def regime_confidence(inputs: RegimeInputs, score: Decimal) -> Confidence:
    """RFC-0025 §4: WeightedConsistency × DataCompleteness, in 0..1."""
    adjusted = inputs.adjusted()
    total_weight = sum((WEIGHTS[name] for name in adjusted), Decimal(0))
    deviation = sum(
        (WEIGHTS[name] / total_weight * abs(value - score) for name, value in adjusted.items()),
        Decimal(0),
    )
    consistency = max(Decimal(0), _ONE - deviation / _HUNDRED)
    completeness = Decimal(len(adjusted)) / Decimal(5)
    return Confidence(consistency * completeness)


def evaluate_regime(inputs: RegimeInputs, as_of: datetime) -> MarketContext:
    """ALG-001: inputs → MarketContext (scores stored as 0..1 fractions)."""
    score = market_score(inputs)

    def fraction(value: Decimal | None) -> Decimal:
        return (value or Decimal(0)) / _HUNDRED

    return MarketContext(
        regime=classify(score),
        confidence=regime_confidence(inputs, score),
        liquidity_score=fraction(inputs.liquidity),
        breadth_score=fraction(inputs.breadth),
        volatility_score=fraction(inputs.volatility),
        rotation_score=fraction(inputs.momentum),
        timestamp=as_of,
    )
