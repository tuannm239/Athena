"""Risk assessment — required on every approved Decision (SPEC-03, SPEC-11).

Every assessment carries a confidence score (SPEC-11, Risk Levels).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from shared_kernel.probability import Confidence


class RiskLevel(StrEnum):
    """Five levels mapped from the 0–100 risk score (RFC-0027 §2)."""

    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    var: Decimal
    cvar: Decimal
    max_drawdown: Decimal
    stress_score: Decimal
    liquidity_score: Decimal
    level: RiskLevel
    confidence: Confidence
