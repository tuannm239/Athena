"""Evidence entity (SPEC-03, Entities).

Evidence is objective information supporting or contradicting a
hypothesis (SPEC-03, Ubiquitous Language).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from shared_kernel.identifiers import EvidenceId
from shared_kernel.probability import Confidence


@dataclass(frozen=True, slots=True)
class Evidence:
    source: str
    category: str
    description: str
    confidence: Confidence
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    id: EvidenceId = field(default_factory=EvidenceId)

    def __post_init__(self) -> None:
        if not self.source:
            raise ValueError("evidence source must not be empty")
        if not self.description:
            raise ValueError("evidence description must not be empty")
