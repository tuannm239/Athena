"""Behavioral override — rule-based, logged, explainable."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class BiasKind(StrEnum):
    OVERTRADING = "OVERTRADING"
    LOSS_AVERSION = "LOSS_AVERSION"
    RECENCY = "RECENCY"
    CONCENTRATION = "CONCENTRATION"


@dataclass(frozen=True, slots=True)
class TriggeredOverride:
    bias: BiasKind
    rule_id: str
    rationale: str

    def __post_init__(self) -> None:
        if not self.rationale:
            raise ValueError("override must carry a human-readable rationale")
