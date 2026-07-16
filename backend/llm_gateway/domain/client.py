"""LLM client port — the single seam vendors plug into (ADR-0003 §1)."""

from __future__ import annotations

from typing import Protocol

from llm_gateway.domain.models import LlmCompletion


class LlmClient(Protocol):
    def complete(self, *, system: str, prompt: str) -> LlmCompletion: ...
