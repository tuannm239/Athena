"""User-defined portfolio constraints (SPEC-03; SPEC-10, Supported Constraints)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from shared_kernel.measures import Percentage


@dataclass(frozen=True, slots=True)
class PortfolioConstraints:
    max_position_weight: Percentage | None = None
    max_sector_exposure: Percentage | None = None
    min_cash_reserve: Percentage | None = None
    liquidity_threshold: Decimal | None = None
    risk_budget: Decimal | None = None
    max_turnover: Percentage | None = None
