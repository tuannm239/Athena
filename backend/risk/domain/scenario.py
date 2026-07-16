"""Scenario Simulator — ALG-015 (SPEC-11 §Scenario Analysis; ADR-0016).

Deterministic linear stress testing: macro shock, sector shocks and a
liquidity haircut applied to portfolio position weights.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from types import MappingProxyType
from typing import Mapping

from risk.domain.metrics import days_to_liquidate
from shared_kernel.exceptions import DomainError

_ZERO = Decimal(0)
_ONE = Decimal(1)


class ScenarioError(DomainError):
    """Raised when a scenario or stress input is invalid."""


@dataclass(frozen=True)
class Scenario:
    """A named shock parameter set (ADR-0016); user-defined scenarios welcome."""

    name: str
    market_shock: Decimal
    sector_shocks: Mapping[str, Decimal] = field(default_factory=dict)
    liquidity_haircut: Decimal = _ZERO
    description: str = ""

    def __post_init__(self) -> None:
        if not self.name:
            raise ScenarioError("scenario requires a name")
        if not (_ZERO <= self.liquidity_haircut < _ONE):
            raise ScenarioError("liquidity_haircut must be in [0, 1)")
        object.__setattr__(self, "sector_shocks", MappingProxyType(dict(self.sector_shocks)))


def builtin_scenarios() -> tuple[Scenario, ...]:
    """ADR-0016 default parameter sets (overridable by constructing Scenario)."""
    return (
        Scenario(
            name="interest_rate_shock",
            market_shock=Decimal("-0.08"),
            sector_shocks={"Financials": Decimal("-0.15"), "Real Estate": Decimal("-0.12")},
            liquidity_haircut=Decimal("0.20"),
            description="Central-bank tightening shock (SPEC-11)",
        ),
        Scenario(
            name="market_crash",
            market_shock=Decimal("-0.20"),
            liquidity_haircut=Decimal("0.40"),
            description="Broad market crash (SPEC-11)",
        ),
        Scenario(
            name="sector_rotation",
            market_shock=_ZERO,
            sector_shocks={"Technology": Decimal("-0.10"), "Energy": Decimal("0.10")},
            description="Rotation out of growth into cyclicals (SPEC-11)",
        ),
        Scenario(
            name="liquidity_contraction",
            market_shock=Decimal("-0.05"),
            liquidity_haircut=Decimal("0.50"),
            description="Market-wide liquidity contraction (SPEC-11)",
        ),
    )


@dataclass(frozen=True, slots=True)
class StressPosition:
    ticker: str
    sector: str
    weight: Decimal
    position_value: Decimal
    average_daily_value: Decimal

    def __post_init__(self) -> None:
        if not (_ZERO <= self.weight <= _ONE):
            raise ScenarioError(f"{self.ticker}: weight must be in [0, 1]")


@dataclass(frozen=True, slots=True)
class PositionImpact:
    ticker: str
    shocked_return: Decimal
    contribution: Decimal
    stressed_days_to_liquidate: Decimal


@dataclass(frozen=True, slots=True)
class StressResult:
    """Portfolio stress test output (SPEC-11 §Scenario Analysis)."""

    scenario: str
    portfolio_return: Decimal
    impacts: tuple[PositionImpact, ...]
    worst_position: str | None
    explanation: str


def stress_test(positions: tuple[StressPosition, ...], scenario: Scenario) -> StressResult:
    """Apply the scenario linearly to weights; deterministic and explainable."""
    impacts: list[PositionImpact] = []
    total = _ZERO
    for position in sorted(positions, key=lambda p: p.ticker):
        shocked = scenario.market_shock + scenario.sector_shocks.get(position.sector, _ZERO)
        contribution = position.weight * shocked
        total += contribution
        base_days = days_to_liquidate(position.position_value, position.average_daily_value)
        stressed_days = base_days / (_ONE - scenario.liquidity_haircut)
        impacts.append(
            PositionImpact(
                ticker=position.ticker,
                shocked_return=shocked,
                contribution=contribution,
                stressed_days_to_liquidate=stressed_days,
            )
        )
    worst = min(impacts, key=lambda i: i.contribution).ticker if impacts else None
    explanation = (
        f"Scenario {scenario.name}: market {scenario.market_shock:+}, "
        f"{len(scenario.sector_shocks)} sector shock(s), liquidity haircut "
        f"{scenario.liquidity_haircut}; portfolio return {total:+}. "
        f"Worst contributor: {worst or 'n/a'}."
    )
    return StressResult(
        scenario=scenario.name,
        portfolio_return=total,
        impacts=tuple(impacts),
        worst_position=worst,
        explanation=explanation,
    )
