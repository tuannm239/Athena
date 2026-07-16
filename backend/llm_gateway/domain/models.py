"""LLM Gateway vocabulary (ADR-0003; SPEC-00 LLM Policy).

The task catalogue is the structural allow-list: SUMMARIZE, CLASSIFY,
EXPLAIN, EXTRACT_EVIDENCE and REPORT are the only operations the
gateway exposes. Decision-making tasks do not exist here, and every
artifact leaving the gateway carries lineage (source ``llm``, model id,
prompt version, task, timestamp) so LLM influence stays auditable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from shared_kernel.exceptions import DomainError

LLM_SOURCE = "llm"

EVIDENCE_DIRECTIONS = frozenset({"SUPPORTING", "CONTRADICTING", "NEUTRAL"})


class LlmGatewayError(DomainError):
    """Gateway misuse or unusable model output."""


class LlmProviderError(LlmGatewayError):
    """The upstream LLM API returned an unusable response."""


class LlmTask(StrEnum):
    """Everything an LLM may do here — and nothing else (SPEC-00)."""

    SUMMARIZE = "SUMMARIZE"
    CLASSIFY = "CLASSIFY"
    EXPLAIN = "EXPLAIN"
    EXTRACT_EVIDENCE = "EXTRACT_EVIDENCE"
    REPORT = "REPORT"


@dataclass(frozen=True, slots=True)
class LlmCompletion:
    """Raw model output as returned by an adapter."""

    text: str
    model: str


@dataclass(frozen=True, slots=True)
class LlmLineage:
    """ADR-0003 §3: every LLM-derived artifact is lineage-tagged."""

    model: str
    prompt_version: str
    task: LlmTask
    generated_at: datetime
    source: str = LLM_SOURCE

    def __post_init__(self) -> None:
        if self.source != LLM_SOURCE:
            raise LlmGatewayError("LLM lineage source must be 'llm'")


@dataclass(frozen=True, slots=True)
class GeneratedText:
    """A summary, explanation or report — always with its lineage."""

    text: str
    lineage: LlmLineage


@dataclass(frozen=True, slots=True)
class Classification:
    label: str
    lineage: LlmLineage


@dataclass(frozen=True, slots=True)
class EvidenceDraft:
    """Research input awaiting review — never a decision (SPEC-00).

    Drafts carry a direction as an explicit property (ADR-0006) and the
    LLM lineage; the Research Copilot converts reviewed drafts into
    Evidence objects with human-confirmed reliability.
    """

    source: str
    category: str
    direction: str
    explanation: str
    lineage: LlmLineage

    def __post_init__(self) -> None:
        if self.direction not in EVIDENCE_DIRECTIONS:
            raise LlmGatewayError(f"invalid evidence direction: {self.direction!r}")
        if not self.explanation:
            raise LlmGatewayError("evidence draft requires an explanation")
