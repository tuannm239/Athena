"""Probability Report — the engine's output contract (RFC-0018 §8)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from shared_kernel.probability import Confidence, Probability


@dataclass(frozen=True, slots=True)
class ProbabilityReport:
    hypothesis: str
    prior: Probability
    posterior: Probability
    confidence: Confidence
    evidence_summary: tuple[str, ...]
    assumptions: tuple[str, ...]
    uncertainty: Decimal
    expected_utility: Decimal | None
    calibration: str
    explanation: str

    def __post_init__(self) -> None:
        if not self.explanation:
            raise ValueError("every probability must include an explanation (RFC-0018 §9)")
