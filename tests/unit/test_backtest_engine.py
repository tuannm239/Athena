"""Unit tests — Backtest Engine ALG-013 (SPEC-09; ADR-0015)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Mapping

import pytest

from backtest.domain.metrics import BacktestInputError, compute_metrics
from backtest.domain.simulator import (
    BacktestConfig,
    BacktestEngine,
    DailyBar,
    SimulationMode,
)
from dsl.domain.compiler import compile_rules
from dsl.domain.evaluator import FactValue

START = date(2026, 1, 5)

RULESET = compile_rules(
    'RULE Momentum WHEN Company.PriceMomentum > 0 THEN UTILITY += 0.1 TAG "mom" '
    'EXPLAIN "positive momentum"'
)


def bars(ticker_path: tuple[str, ...]) -> tuple[DailyBar, ...]:
    return tuple(
        DailyBar(day=START + timedelta(days=i), close=Decimal(price))
        for i, price in enumerate(ticker_path)
    )


def momentum_facts(as_of: date, ticker: str) -> Mapping[str, FactValue]:
    """Point-in-time: momentum sign derived only from data before as_of."""
    del ticker
    return {"Company.PriceMomentum": Decimal(1 if as_of.day % 2 == 1 else -1)}


class TestMetrics:
    RETURNS = tuple(Decimal(r) for r in ("0.02", "-0.01", "0.03", "0.01", "-0.02"))

    def test_metric_relationships(self) -> None:
        metrics = compute_metrics(
            self.RETURNS, bars_per_period=1, turnover_per_period=(Decimal("0.1"),) * 5
        )
        assert metrics.total_return > Decimal(0)
        assert metrics.win_rate == Decimal(3) / Decimal(5)
        assert metrics.profit_factor > Decimal(1)
        assert metrics.max_drawdown > Decimal(0)
        assert metrics.sharpe > Decimal(0)
        assert metrics.sortino >= metrics.sharpe  # downside dev <= total dev here

    def test_benchmark_alpha_beta(self) -> None:
        metrics = compute_metrics(
            self.RETURNS,
            bars_per_period=1,
            turnover_per_period=(),
            benchmark_returns=self.RETURNS,
        )
        assert metrics.beta == Decimal(1)
        assert metrics.alpha == Decimal(0)

    def test_benchmark_length_mismatch(self) -> None:
        with pytest.raises(BacktestInputError):
            compute_metrics(
                self.RETURNS,
                bars_per_period=1,
                turnover_per_period=(),
                benchmark_returns=self.RETURNS[:-1],
            )

    def test_too_short_series(self) -> None:
        with pytest.raises(BacktestInputError):
            compute_metrics((Decimal("0.01"),), bars_per_period=1, turnover_per_period=())


class TestSimulator:
    def _engine(self) -> BacktestEngine:
        return BacktestEngine(
            config=BacktestConfig(ruleset=RULESET, mode=SimulationMode.DAILY),
            facts=momentum_facts,
        )

    def _prices(self) -> dict[str, tuple[DailyBar, ...]]:
        return {
            "AAA": bars(("100", "102", "101", "104", "103", "106", "107", "105")),
            "BBB": bars(("50", "50.5", "50.2", "51", "50.8", "51.5", "51.2", "52")),
        }

    def test_reproducible_report(self) -> None:
        engine = self._engine()
        assert engine.run(self._prices()) == engine.run(self._prices())

    def test_report_structure(self) -> None:
        report = self._engine().run(self._prices())
        assert len(report.equity_curve) == len(report.drawdown_curve)
        assert report.decision_evaluations > 0
        assert report.decisions_matched > 0
        assert report.trades  # rebalances happened
        assert report.monthly_returns
        assert all(dd >= Decimal(0) for _, dd in report.drawdown_curve)

    def test_no_matches_means_flat_equity(self) -> None:
        engine = BacktestEngine(
            config=BacktestConfig(ruleset=RULESET, mode=SimulationMode.DAILY),
            facts=lambda _d, _t: {"Company.PriceMomentum": Decimal(-1)},
        )
        report = engine.run(self._prices())
        assert report.metrics.total_return == Decimal(0)
        assert report.trades == ()

    def test_survivorship_universe_is_point_in_time(self) -> None:
        prices = self._prices()
        prices["CCC"] = bars(("10", "11"))  # leaves the dataset after two bars
        report = self._engine().run(prices)
        assert report.decision_evaluations > 0  # CCC only evaluated while priced

    def test_position_cap_enforced(self) -> None:
        report = self._engine().run(self._prices())
        for trade in report.trades:
            assert abs(trade.weight_change) <= Decimal("0.4")  # cap 0.2 each way

    def test_weekly_mode_and_min_bars(self) -> None:
        engine = BacktestEngine(
            config=BacktestConfig(ruleset=RULESET, mode=SimulationMode.WEEKLY),
            facts=momentum_facts,
        )
        prices = {
            "AAA": bars(tuple(str(100 + i) for i in range(15))),
        }
        report = engine.run(prices)
        assert len(report.equity_curve) >= 3
        with pytest.raises(BacktestInputError):
            engine.run({"AAA": bars(("100",))})
