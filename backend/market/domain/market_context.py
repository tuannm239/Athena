"""Market context — the Market Engine's output contract (SPEC-05, Outputs).

Business rule (SPEC-05): market regime must be deterministic; every
regime carries a confidence value.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from shared_kernel.probability import Confidence


class Regime(StrEnum):
    """Market regimes (SPEC-05, Market Regimes)."""

    EXPANSION = "EXPANSION"
    RECOVERY = "RECOVERY"
    CONSOLIDATION = "CONSOLIDATION"
    CONTRACTION = "CONTRACTION"


@dataclass(frozen=True, slots=True)
class MarketContext:
    regime: Regime
    confidence: Confidence
    liquidity_score: Decimal
    breadth_score: Decimal
    volatility_score: Decimal
    rotation_score: Decimal
    timestamp: datetime
