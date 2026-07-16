"""Position sizing — ALG-007 (RFC-0027 §5).

PositionSize = KellyFraction × RiskBudget × LiquidityFactor × Confidence
             × PortfolioConstraintCap
KellyFraction = max(0, p − (1−p)/b), b = expected_return/expected_drawdown.
"""

from __future__ import annotations

from decimal import Decimal

from shared_kernel.exceptions import DomainError
from shared_kernel.measures import PositionSize
from shared_kernel.probability import Confidence, Probability

_ZERO = Decimal(0)
_ONE = Decimal(1)


class SizingError(DomainError):
    """Raised when sizing inputs are unusable."""


def kelly_fraction(
    posterior: Probability, expected_return: Decimal, expected_drawdown: Decimal
) -> Decimal:
    """max(0, p − (1−p)/b) with b = expected_return/expected_drawdown."""
    if expected_return <= 0 or expected_drawdown <= 0:
        raise SizingError("expected_return and expected_drawdown must be positive")
    b = expected_return / expected_drawdown
    p = posterior.value
    return max(_ZERO, p - (_ONE - p) / b)


def position_size(
    *,
    posterior: Probability,
    expected_return: Decimal,
    expected_drawdown: Decimal,
    risk_budget: Decimal,
    liquidity_factor: Decimal,
    confidence: Confidence,
    max_position_weight: Decimal | None = None,
) -> PositionSize:
    """RFC-0027 §5 chain; every factor is a fraction in [0, 1]."""
    for name, value in (("risk_budget", risk_budget), ("liquidity_factor", liquidity_factor)):
        if not (_ZERO <= value <= _ONE):
            raise SizingError(f"{name} must be in [0, 1], got {value}")
    size = (
        kelly_fraction(posterior, expected_return, expected_drawdown)
        * risk_budget
        * liquidity_factor
        * confidence.value
    )
    if max_position_weight is not None:
        size = min(size, max_position_weight)
    return PositionSize(size)
