"""Deterministic fake LLM client for tests and offline development."""

from __future__ import annotations

from dataclasses import dataclass, field

from llm_gateway.domain.models import LlmCompletion


@dataclass
class FakeLlmClient:
    """Scripted responses consumed in order; echoes the prompt after that."""

    responses: tuple[str, ...] = ()
    model: str = "fake-llm"
    calls: list[tuple[str, str]] = field(default_factory=list)

    def complete(self, *, system: str, prompt: str) -> LlmCompletion:
        self.calls.append((system, prompt))
        index = len(self.calls) - 1
        if index < len(self.responses):
            return LlmCompletion(text=self.responses[index], model=self.model)
        return LlmCompletion(text=f"[fake] {prompt}", model=self.model)
