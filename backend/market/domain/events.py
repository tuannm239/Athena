"""Market domain events (SPEC-05, Domain Events)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from market.domain.market_context import Regime
from shared_kernel.events import DomainEvent


@dataclass(frozen=True, slots=True)
class MarketRegimeChanged(DomainEvent):
    regime: Regime


@dataclass(frozen=True, slots=True)
class LiquidityChanged(DomainEvent):
    liquidity_score: Decimal


@dataclass(frozen=True, slots=True)
class BreadthChanged(DomainEvent):
    breadth_score: Decimal


@dataclass(frozen=True, slots=True)
class VolatilityChanged(DomainEvent):
    volatility_score: Decimal
