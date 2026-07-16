"""Property schema for semantic analysis (RFC-0017 §Root Objects).

RFC-0017 fixes the twelve root objects but leaves the property catalogue
to the platform; this registry is the extensible source of truth,
seeded from the engines' published outputs (RFC-0025 regimes, SPEC-06
factors, SPEC-10/11 state). Unknown roots → DSL003, unknown properties
→ DSL013, enum violations → DSL014.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

ROOT_OBJECTS = frozenset(
    {
        "Market",
        "Company",
        "Portfolio",
        "Risk",
        "Behavior",
        "Decision",
        "Evidence",
        "Feature",
        "Macro",
        "Sector",
        "Industry",
        "Country",
    }
)

REGIME_ENUM = frozenset({"Expansion", "Recovery", "Consolidation", "Contraction"})


class PropertyKind(StrEnum):
    NUMBER = "NUMBER"
    STRING = "STRING"
    BOOLEAN = "BOOLEAN"
    ENUM = "ENUM"


@dataclass(frozen=True, slots=True)
class PropertySpec:
    kind: PropertyKind
    enum_values: frozenset[str] | None = None


def _numbers(*names: str) -> dict[str, PropertySpec]:
    return {name: PropertySpec(PropertyKind.NUMBER) for name in names}


DEFAULT_SCHEMA: dict[str, dict[str, PropertySpec]] = {
    "Market": {
        "Regime": PropertySpec(PropertyKind.ENUM, REGIME_ENUM),
        **_numbers("Trend", "Breadth", "Liquidity", "Momentum", "Volatility", "Score"),
    },
    "Company": {
        "Ticker": PropertySpec(PropertyKind.STRING),
        "Sector": PropertySpec(PropertyKind.STRING),
        "Industry": PropertySpec(PropertyKind.STRING),
        **_numbers(
            "ROE",
            "ROIC",
            "GrossMargin",
            "OperatingMargin",
            "EarningsStability",
            "RevenueGrowth",
            "EPSGrowth",
            "FCFGrowth",
            "BookValueGrowth",
            "PEPercentile",
            "PBPercentile",
            "EVEBITDA",
            "FCFYield",
            "RelativeStrength",
            "PriceMomentum",
            "VolumeMomentum",
            "AverageDailyValue",
            "TurnoverRatio",
            "FreeFloat",
            "Beta",
            "Volatility",
            "Drawdown",
            "DownsideDeviation",
            "InsiderOwnership",
            "DebtToEquity",
            "QualityScore",
            "ValuationScore",
            "GrowthScore",
        ),
    },
    "Portfolio": _numbers("Cash", "Allocation", "Concentration", "PositionCount", "RiskBudget"),
    "Risk": _numbers("Score", "VaR", "CVaR", "Drawdown", "Volatility", "DaysToLiquidate"),
    "Behavior": {
        "BiasDetected": PropertySpec(PropertyKind.BOOLEAN),
        **_numbers("BehaviorScore", "CalibrationError"),
    },
    "Decision": {
        **_numbers("Probability", "Confidence", "ExpectedReturn", "ExpectedDrawdown"),
    },
    "Evidence": _numbers("Count", "SupportingCount", "ContradictingCount", "MeanReliability"),
    "Feature": {},  # feature ids are registered dynamically (Feature Store)
    "Macro": _numbers("InterestRate", "Inflation", "GDP", "PMI", "FXRate"),
    "Sector": {"Name": PropertySpec(PropertyKind.STRING), **_numbers("Strength", "Exposure")},
    "Industry": {"Name": PropertySpec(PropertyKind.STRING), **_numbers("Strength")},
    "Country": {"Code": PropertySpec(PropertyKind.STRING), **_numbers("RiskScore")},
}


def with_features(feature_ids: tuple[str, ...]) -> dict[str, dict[str, PropertySpec]]:
    """Schema copy with Feature.<id> numeric properties registered."""
    schema = {root: dict(props) for root, props in DEFAULT_SCHEMA.items()}
    schema["Feature"] = {fid: PropertySpec(PropertyKind.NUMBER) for fid in feature_ids}
    return schema
