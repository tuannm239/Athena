"""Backtest performance metrics (SPEC-09 §Outputs; ADR-0015 §4)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from shared_kernel.exceptions import DomainError

TRADING_DAYS = Decimal(252)
_ZERO = Decimal(0)
_ONE = Decimal(1)


class BacktestInputError(DomainError):
    """Raised when the simulation inputs are unusable."""


def _mean(values: tuple[Decimal, ...]) -> Decimal:
    return sum(values, _ZERO) / Decimal(len(values))


def _stdev(values: tuple[Decimal, ...]) -> Decimal:
    mean = _mean(values)
    return (sum(((v - mean) ** 2 for v in values), _ZERO) / Decimal(len(values))).sqrt()


@dataclass(frozen=True, slots=True)
class PerformanceMetrics:
    """The eleven SPEC-09 §Outputs metrics."""

    cagr: Decimal
    total_return: Decimal
    sharpe: Decimal
    sortino: Decimal
    calmar: Decimal
    max_drawdown: Decimal
    win_rate: Decimal
    profit_factor: Decimal
    turnover: Decimal
    alpha: Decimal
    beta: Decimal


def compute_metrics(
    period_returns: tuple[Decimal, ...],
    *,
    bars_per_period: int,
    turnover_per_period: tuple[Decimal, ...],
    benchmark_returns: tuple[Decimal, ...] | None = None,
) -> PerformanceMetrics:
    if len(period_returns) < 2:
        raise BacktestInputError("at least two rebalance periods are required")

    equity = _ONE
    peak = _ONE
    max_dd = _ZERO
    for r in period_returns:
        equity *= _ONE + r
        peak = max(peak, equity)
        max_dd = max(max_dd, (peak - equity) / peak)
    total_return = equity - _ONE

    periods_per_year = TRADING_DAYS / Decimal(bars_per_period)
    years = Decimal(len(period_returns)) / periods_per_year
    cagr = equity ** (_ONE / years) - _ONE if equity > 0 else Decimal(-1)

    stdev = _stdev(period_returns)
    mean = _mean(period_returns)
    ann = periods_per_year.sqrt()
    sharpe = (mean / stdev) * ann if stdev > 0 else _ZERO
    downside = _stdev(tuple(min(r, _ZERO) for r in period_returns))
    sortino = (mean / downside) * ann if downside > 0 else _ZERO
    calmar = cagr / max_dd if max_dd > 0 else _ZERO

    wins = tuple(r for r in period_returns if r > 0)
    losses = tuple(r for r in period_returns if r < 0)
    win_rate = Decimal(len(wins)) / Decimal(len(period_returns))
    gross_loss = -sum(losses, _ZERO)
    profit_factor = (sum(wins, _ZERO) / gross_loss) if gross_loss > 0 else _ZERO

    turnover = _mean(turnover_per_period) * periods_per_year if turnover_per_period else _ZERO

    alpha = _ZERO
    beta = _ZERO
    if benchmark_returns is not None:
        if len(benchmark_returns) != len(period_returns):
            raise BacktestInputError("benchmark series must match the period count")
        mean_b = _mean(benchmark_returns)
        var_b = sum(((b - mean_b) ** 2 for b in benchmark_returns), _ZERO) / Decimal(
            len(benchmark_returns)
        )
        cov = sum(
            (
                (p - mean) * (b - mean_b)
                for p, b in zip(period_returns, benchmark_returns, strict=True)
            ),
            _ZERO,
        ) / Decimal(len(period_returns))
        beta = cov / var_b if var_b > 0 else _ZERO
        alpha = (mean - beta * mean_b) * periods_per_year

    return PerformanceMetrics(
        cagr=cagr,
        total_return=total_return,
        sharpe=sharpe,
        sortino=sortino,
        calmar=calmar,
        max_drawdown=max_dd,
        win_rate=win_rate,
        profit_factor=profit_factor,
        turnover=turnover,
        alpha=alpha,
        beta=beta,
    )
