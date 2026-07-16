"""LLM Gateway (Phase 2, Module 4; ADR-0003).

The only surface through which the platform talks to LLMs. The public
methods are exactly the SPEC-00 allowed uses — summarize, classify,
explain, extract evidence, generate reports. There is no method that
produces a decision, a probability, a position size or a capital
allocation; the gateway never imports the Decision Kernel or any other
guarded context (machine-enforced in tests/unit/test_architecture.py).

Every artifact leaving here carries `LlmLineage` (source ``llm``, model
id, prompt version, task, timestamp) per ADR-0003 §3.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Mapping

from llm_gateway.domain.client import LlmClient
from llm_gateway.domain.models import (
    EVIDENCE_DIRECTIONS,
    Classification,
    EvidenceDraft,
    GeneratedText,
    LlmGatewayError,
    LlmLineage,
    LlmTask,
)

PROMPT_VERSION = "athena-llm-prompts/1.0.0"

_SYSTEM = (
    "You are a research assistant inside a financial decision platform. "
    "You never make or imply investment decisions, never recommend buying "
    "or selling, and never allocate capital. Work only with the material "
    "you are given."
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class LlmGateway:
    """Allowed-use-only façade over an injected `LlmClient`."""

    client: LlmClient
    clock: Callable[[], datetime] = field(default=_utcnow)

    def summarize(self, text: str, *, max_words: int = 120) -> GeneratedText:
        if not text.strip():
            raise LlmGatewayError("nothing to summarize")
        prompt = f"Summarize the following in at most {max_words} words:\n\n{text}"
        completion = self.client.complete(system=_SYSTEM, prompt=prompt)
        return GeneratedText(completion.text, self._lineage(completion.model, LlmTask.SUMMARIZE))

    def classify(self, text: str, labels: tuple[str, ...]) -> Classification:
        """Pick one of the caller's labels; anything else is rejected."""
        if len(labels) < 2:
            raise LlmGatewayError("classification needs at least two labels")
        prompt = (
            f"Classify the following text with exactly one of these labels: "
            f"{', '.join(labels)}. Answer with the label only.\n\n{text}"
        )
        completion = self.client.complete(system=_SYSTEM, prompt=prompt)
        label = completion.text.strip()
        if label not in labels:
            raise LlmGatewayError(f"model returned a label outside the set: {label!r}")
        return Classification(label, self._lineage(completion.model, LlmTask.CLASSIFY))

    def explain(self, subject: str, facts: Mapping[str, str]) -> GeneratedText:
        """Narrate structured facts (ADR-0003 §4: facts in, prose out)."""
        if not facts:
            raise LlmGatewayError("an explanation requires structured facts")
        listed = "\n".join(f"- {key}: {value}" for key, value in sorted(facts.items()))
        prompt = (
            f"Explain {subject} using only the facts below. Do not add "
            f"claims that are not in the list.\n\n{listed}"
        )
        completion = self.client.complete(system=_SYSTEM, prompt=prompt)
        return GeneratedText(completion.text, self._lineage(completion.model, LlmTask.EXPLAIN))

    def extract_evidence(self, document: str, *, source: str) -> tuple[EvidenceDraft, ...]:
        """Turn a document into reviewable evidence drafts.

        The model answers one candidate per line as
        ``DIRECTION|category|explanation``; malformed lines are dropped,
        and a response with no usable line is an error (never silently
        empty evidence).
        """
        if not document.strip():
            raise LlmGatewayError("nothing to extract evidence from")
        prompt = (
            "Extract factual evidence from the document below. Answer one "
            "item per line, formatted exactly as DIRECTION|category|explanation "
            "where DIRECTION is SUPPORTING, CONTRADICTING or NEUTRAL. "
            "No other text.\n\n" + document
        )
        completion = self.client.complete(system=_SYSTEM, prompt=prompt)
        lineage = self._lineage(completion.model, LlmTask.EXTRACT_EVIDENCE)
        drafts: list[EvidenceDraft] = []
        for line in completion.text.splitlines():
            parts = [part.strip() for part in line.split("|", maxsplit=2)]
            if len(parts) != 3 or parts[0] not in EVIDENCE_DIRECTIONS or not parts[2]:
                continue
            drafts.append(
                EvidenceDraft(
                    source=source,
                    category=parts[1],
                    direction=parts[0],
                    explanation=parts[2],
                    lineage=lineage,
                )
            )
        if not drafts:
            raise LlmGatewayError("model produced no parseable evidence drafts")
        return tuple(drafts)

    def generate_report(self, title: str, sections: Mapping[str, str]) -> GeneratedText:
        if not sections:
            raise LlmGatewayError("a report requires at least one section")
        body = "\n\n".join(f"## {name}\n{content}" for name, content in sections.items())
        prompt = (
            f"Write a well-structured report titled '{title}' from the "
            f"section material below. Preserve all figures exactly.\n\n{body}"
        )
        completion = self.client.complete(system=_SYSTEM, prompt=prompt)
        return GeneratedText(completion.text, self._lineage(completion.model, LlmTask.REPORT))

    def _lineage(self, model: str, task: LlmTask) -> LlmLineage:
        return LlmLineage(
            model=model,
            prompt_version=PROMPT_VERSION,
            task=task,
            generated_at=self.clock(),
        )
