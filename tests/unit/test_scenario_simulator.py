"""Unit tests — Scenario Simulator ALG-015 (SPEC-11; ADR-0016)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from risk.domain.scenario import (
    Scenario,
    ScenarioError,
    StressPosition,
    builtin_scenarios,
    stress_test,
)


def positions() -> tuple[StressPosition, ...]:
    return (
        StressPosition(
            ticker="BANK",
            sector="Financials",
            weight=Decimal("0.4"),
            position_value=Decimal(4000),
            average_daily_value=Decimal(1000),
        ),
        StressPosition(
            ticker="TECH",
            sector="Technology",
            weight=Decimal("0.3"),
            position_value=Decimal(3000),
            average_daily_value=Decimal(3000),
        ),
    )


class TestScenarios:
    def test_builtin_families_cover_spec11(self) -> None:
        names = {s.name for s in builtin_scenarios()}
        assert names == {
            "interest_rate_shock",
            "market_crash",
            "sector_rotation",
            "liquidity_contraction",
        }

    def test_scenario_validation(self) -> None:
        with pytest.raises(ScenarioError):
            Scenario(name="", market_shock=Decimal(0))
        with pytest.raises(ScenarioError):
            Scenario(name="x", market_shock=Decimal(0), liquidity_haircut=Decimal(1))

    def test_user_defined_scenario_supported(self) -> None:
        custom = Scenario(
            name="fx_shock",
            market_shock=Decimal("-0.03"),
            sector_shocks={"Exporters": Decimal("0.05")},
        )
        result = stress_test(positions(), custom)
        assert result.scenario == "fx_shock"


class TestStressTest:
    def test_interest_rate_shock_math(self) -> None:
        scenario = builtin_scenarios()[0]
        result = stress_test(positions(), scenario)
        # BANK: 0.4 * (-0.08 - 0.15) = -0.092 ; TECH: 0.3 * (-0.08) = -0.024
        assert result.portfolio_return == Decimal("-0.116")
        assert result.worst_position == "BANK"
        bank = next(i for i in result.impacts if i.ticker == "BANK")
        assert bank.stressed_days_to_liquidate == Decimal(4) / Decimal("0.8")
        assert "interest_rate_shock" in result.explanation

    def test_liquidity_haircut_scales_days(self) -> None:
        result = stress_test(positions(), builtin_scenarios()[3])
        tech = next(i for i in result.impacts if i.ticker == "TECH")
        assert tech.stressed_days_to_liquidate == Decimal(2)  # 1 day / (1-0.5)

    def test_deterministic(self) -> None:
        scenario = builtin_scenarios()[1]
        assert stress_test(positions(), scenario) == stress_test(positions(), scenario)

    def test_empty_portfolio(self) -> None:
        result = stress_test((), builtin_scenarios()[1])
        assert result.portfolio_return == Decimal(0)
        assert result.worst_position is None
