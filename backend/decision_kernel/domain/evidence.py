"""Evidence entity (ADR-0006 unified model).

Direction is an explicit property — never inferred from collection
membership. `reliability` grades the evidence itself; the decision's
own confidence is a separate concept (RFC-0026).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping

from shared_kernel.identifiers import EvidenceId
from shared_kernel.probability import Reliability


class EvidenceDirection(StrEnum):
    SUPPORTING = "SUPPORTING"
    CONTRADICTING = "CONTRADICTING"
    NEUTRAL = "NEUTRAL"


@dataclass(frozen=True)
class Evidence:
    source: str
    category: str
    reliability: Reliability
    direction: EvidenceDirection
    explanation: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Mapping[str, str] = field(default_factory=dict)
    id: EvidenceId = field(default_factory=EvidenceId)

    def __post_init__(self) -> None:
        if not self.source:
            raise ValueError("evidence source must not be empty")
        if not self.explanation:
            raise ValueError("evidence explanation must not be empty")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))
