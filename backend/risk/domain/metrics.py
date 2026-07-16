"""Risk metric calculators — ALG-006 (RFC-0027 §1/§3; SPEC-11).

Pure, deterministic Decimal arithmetic over daily return series.
Definitions codified in RFC-0027: population standard deviation,
lower-interpolation quantile at 5%, annualization by √252.
"""

from __future__ import annotations

from decimal import Decimal

from shared_kernel.exceptions import DomainError

TRADING_DAYS = Decimal(252)
VAR_TAIL = Decimal("0.05")

_ZERO = Decimal(0)
_ONE = Decimal(1)


class RiskInputError(DomainError):
    """Raised when a return series or liquidity input is unusable."""


def _require_returns(returns: tuple[Decimal, ...]) -> None:
    if len(returns) < 2:
        raise RiskInputError("at least two return observations are required")


def _stdev(values: tuple[Decimal, ...]) -> Decimal:
    n = Decimal(len(values))
    mean = sum(values, _ZERO) / n
    variance = sum(((v - mean) ** 2 for v in values), _ZERO) / n
    return variance.sqrt()


def historical_volatility(returns: tuple[Decimal, ...]) -> Decimal:
    """Annualized population volatility: stdev(returns) × √252."""
    _require_returns(returns)
    return _stdev(returns) * TRADING_DAYS.sqrt()


def _tail(returns: tuple[Decimal, ...]) -> tuple[Decimal, ...]:
    ordered = tuple(sorted(returns))
    index = int(VAR_TAIL * (len(ordered) - 1))
    quantile = ordered[index]
    return tuple(r for r in ordered if r <= quantile)


def var_95(returns: tuple[Decimal, ...]) -> Decimal:
    """Historical 95% VaR as a positive daily loss fraction."""
    _require_returns(returns)
    ordered = tuple(sorted(returns))
    quantile = ordered[int(VAR_TAIL * (len(ordered) - 1))]
    return max(_ZERO, -quantile)


def cvar_95(returns: tuple[Decimal, ...]) -> Decimal:
    """Mean loss beyond the 95% VaR threshold, as a positive fraction."""
    _require_returns(returns)
    tail = _tail(returns)
    mean_tail = sum(tail, _ZERO) / Decimal(len(tail))
    return max(_ZERO, -mean_tail)


def max_drawdown(returns: tuple[Decimal, ...]) -> Decimal:
    """Maximum peak-to-trough decline of the cumulative return curve."""
    _require_returns(returns)
    value = _ONE
    peak = _ONE
    worst = _ZERO
    for r in returns:
        value *= _ONE + r
        peak = max(peak, value)
        worst = max(worst, (peak - value) / peak)
    return worst


def downside_deviation(returns: tuple[Decimal, ...]) -> Decimal:
    """Annualized deviation of negative returns only (tail risk proxy)."""
    _require_returns(returns)
    downside = tuple(min(r, _ZERO) for r in returns)
    return _stdev(downside) * TRADING_DAYS.sqrt()


def days_to_liquidate(position_value: Decimal, average_daily_value: Decimal) -> Decimal:
    """Liquidity risk: position value over tradable value per day."""
    if average_daily_value <= 0:
        raise RiskInputError("average_daily_value must be positive")
    if position_value < 0:
        raise RiskInputError("position_value must be non-negative")
    return position_value / average_daily_value
