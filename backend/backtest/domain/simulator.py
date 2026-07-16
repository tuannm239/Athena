"""Historical simulator — ALG-013 (SPEC-09; ADR-0015).

Execution pipeline: load dataset → build simulation universe → apply
Decision-DSL rules → generate simulated decisions → rebalance portfolio
→ record trades → calculate metrics → produce report. Deterministic;
no look-ahead (decisions at bar t see only data ≤ t and earn the
t → t+1 return); no survivorship bias (the universe at t is exactly
the tickers priced at t).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Callable, Mapping

from backtest.domain.metrics import BacktestInputError, PerformanceMetrics, compute_metrics
from dsl.domain.compiler import CompiledRuleset
from dsl.domain.evaluator import FactValue
from dsl.domain.evaluator import evaluate as evaluate_graph

_ZERO = Decimal(0)
_ONE = Decimal(1)

FactProvider = Callable[[date, str], Mapping[str, FactValue]]
"""Point-in-time facts for (as_of, ticker); must never expose future data."""


class SimulationMode(StrEnum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"


_BARS: dict[SimulationMode, int] = {
    SimulationMode.DAILY: 1,
    SimulationMode.WEEKLY: 5,
    SimulationMode.MONTHLY: 21,
}


@dataclass(frozen=True, slots=True)
class DailyBar:
    day: date
    close: Decimal

    def __post_init__(self) -> None:
        if self.close <= 0:
            raise BacktestInputError(f"price must be positive on {self.day}")


@dataclass(frozen=True, slots=True)
class BacktestConfig:
    ruleset: CompiledRuleset
    mode: SimulationMode
    max_position_weight: Decimal = Decimal("0.2")
    utility_threshold: Decimal = _ZERO


@dataclass(frozen=True, slots=True)
class Trade:
    day: date
    ticker: str
    weight_change: Decimal


@dataclass(frozen=True, slots=True)
class BacktestReport:
    """SPEC-09 §Reports."""

    metrics: PerformanceMetrics
    equity_curve: tuple[tuple[date, Decimal], ...]
    drawdown_curve: tuple[tuple[date, Decimal], ...]
    monthly_returns: tuple[tuple[str, Decimal], ...]
    trades: tuple[Trade, ...]
    decision_evaluations: int
    decisions_matched: int
    failure_analysis: tuple[str, ...]


@dataclass(frozen=True)
class BacktestEngine:
    """Deterministic DSL-driven simulation (weights ∝ clamped rule utility)."""

    config: BacktestConfig
    facts: FactProvider = field(default=lambda _day, _ticker: {})

    def run(
        self,
        prices: Mapping[str, tuple[DailyBar, ...]],
        *,
        benchmark: tuple[Decimal, ...] | None = None,
    ) -> BacktestReport:
        days = sorted({bar.day for bars in prices.values() for bar in bars})
        if len(days) < 2:
            raise BacktestInputError("at least two bars are required")
        step = _BARS[self.config.mode]

        closes: dict[str, dict[date, Decimal]] = {
            ticker: {bar.day: bar.close for bar in bars} for ticker, bars in prices.items()
        }

        weights: dict[str, Decimal] = {}
        equity = _ONE
        equity_curve: list[tuple[date, Decimal]] = [(days[0], equity)]
        period_returns: list[Decimal] = []
        period_turnover: list[Decimal] = []
        trades: list[Trade] = []
        evaluations = 0
        matched = 0

        for index in range(0, len(days) - 1, step):
            day = days[index]
            next_day = days[min(index + step, len(days) - 1)]
            universe = sorted(t for t, series in closes.items() if day in series)

            # Decision stage: DSL over point-in-time facts (no look-ahead).
            utilities: dict[str, Decimal] = {}
            for ticker in universe:
                outcome = evaluate_graph(self.config.ruleset.graph, self.facts(day, ticker))
                evaluations += 1
                if outcome.matched:
                    matched += 1
                if outcome.utility > self.config.utility_threshold:
                    utilities[ticker] = outcome.utility

            # Rebalance: weights proportional to utility, capped per position.
            target: dict[str, Decimal] = {}
            total_utility = sum(utilities.values(), _ZERO)
            if total_utility > 0:
                for ticker, utility in sorted(utilities.items()):
                    target[ticker] = min(utility / total_utility, self.config.max_position_weight)

            turnover = _ZERO
            for ticker in sorted(set(weights) | set(target)):
                delta = target.get(ticker, _ZERO) - weights.get(ticker, _ZERO)
                if delta != 0:
                    trades.append(Trade(day=day, ticker=ticker, weight_change=delta))
                    turnover += abs(delta)
            period_turnover.append(turnover / 2)
            weights = target

            # Earn the t -> t+step return on the held weights.
            period_return = _ZERO
            for ticker, weight in weights.items():
                series = closes[ticker]
                if day in series and next_day in series:
                    period_return += weight * (series[next_day] / series[day] - _ONE)
            period_returns.append(period_return)
            equity *= _ONE + period_return
            equity_curve.append((next_day, equity))

        metrics = compute_metrics(
            tuple(period_returns),
            bars_per_period=step,
            turnover_per_period=tuple(period_turnover),
            benchmark_returns=benchmark,
        )

        peak = _ZERO
        drawdowns: list[tuple[date, Decimal]] = []
        for day, value in equity_curve:
            peak = max(peak, value)
            drawdowns.append((day, (peak - value) / peak if peak > 0 else _ZERO))

        monthly: dict[str, Decimal] = {}
        for (start, _), r in zip(equity_curve[:-1], period_returns, strict=True):
            key = f"{start.year}-{start.month:02d}"
            monthly[key] = (_ONE + monthly.get(key, _ZERO)) * (_ONE + r) - _ONE
        worst = sorted(
            zip((d for d, _ in equity_curve[1:]), period_returns, strict=True),
            key=lambda item: item[1],
        )[:3]
        failure = tuple(f"{day}: period return {r}" for day, r in worst if r < 0)

        return BacktestReport(
            metrics=metrics,
            equity_curve=tuple(equity_curve),
            drawdown_curve=tuple(drawdowns),
            monthly_returns=tuple(sorted(monthly.items())),
            trades=tuple(trades),
            decision_evaluations=evaluations,
            decisions_matched=matched,
            failure_analysis=failure,
        )
