"""Behavioral biases and reports (SPEC-12).

Behavioral feedback is advisory only; the Behavior Engine never
overrides the Decision Kernel (SPEC-12, Business Rules).
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class BiasKind(StrEnum):
    LOSS_AVERSION = "LOSS_AVERSION"
    CONFIRMATION_BIAS = "CONFIRMATION_BIAS"
    ANCHORING = "ANCHORING"
    OVERCONFIDENCE = "OVERCONFIDENCE"
    RECENCY = "RECENCY"
    DISPOSITION_EFFECT = "DISPOSITION_EFFECT"
    FOMO = "FOMO"
    HERDING = "HERDING"


@dataclass(frozen=True, slots=True)
class BehaviorReport:
    """Behavior Engine output (SPEC-12, Outputs). Recommendations must be explainable."""

    behavior_score: Decimal
    detected_biases: tuple[BiasKind, ...]
    confidence_calibration: Decimal
    recurring_patterns: tuple[str, ...]
    recommendations: tuple[str, ...]
    learning_actions: tuple[str, ...]
