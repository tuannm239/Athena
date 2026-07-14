"""Research summary entity.

SPEC-03 names the Research context and its repository without detailing
entities; fields here follow SPEC-01 (Functional Requirements, Research:
"Generate structured research summaries") and stay minimal until a
dedicated spec exists. LLM-derived content must carry its sources.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True, slots=True)
class ResearchSummary:
    subject: str
    content: str
    sources: tuple[str, ...]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    id: uuid.UUID = field(default_factory=uuid.uuid4)

    def __post_init__(self) -> None:
        if not self.subject:
            raise ValueError("research summary requires a subject")
        if not self.sources:
            raise ValueError("research summary requires sources (provenance)")
