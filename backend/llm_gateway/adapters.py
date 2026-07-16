"""LLM provider adapters (Phase 2, Module 4; ADR-0003 §1).

This module is the only place in the platform that knows vendor HTTP
contracts. Adapters implement the `LlmClient` port over an injectable
`HttpTransport`, so every adapter is testable without network access
and vendors swap via configuration only (`create_client`).

Supported: OpenAI, DeepSeek and local OpenAI-compatible servers
(one chat-completions dialect), Anthropic Messages, Google Gemini.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol

import httpx

from llm_gateway.domain.models import LlmCompletion, LlmProviderError

OPENAI_BASE_URL = "https://api.openai.com/v1"
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
ANTHROPIC_BASE_URL = "https://api.anthropic.com"
GOOGLE_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
LOCAL_BASE_URL = "http://localhost:11434/v1"

ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_TIMEOUT = 60.0
DEFAULT_MAX_TOKENS = 2048


class HttpTransport(Protocol):
    def post_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        payload: Mapping[str, object],
        timeout: float,
    ) -> Mapping[str, object]: ...


class HttpxTransport:
    """Production transport; raises `LlmProviderError` on HTTP failure."""

    def post_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        payload: Mapping[str, object],
        timeout: float,
    ) -> Mapping[str, object]:
        try:
            response = httpx.post(url, headers=dict(headers), json=dict(payload), timeout=timeout)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as error:
            raise LlmProviderError(f"LLM API call failed: {error}") from error
        if not isinstance(data, dict):
            raise LlmProviderError("LLM API returned a non-object body")
        return data


def _extract(data: object, *path: str | int) -> object:
    node = data
    for step in path:
        try:
            node = node[step]  # type: ignore[index]
        except (KeyError, IndexError, TypeError) as error:
            raise LlmProviderError(f"unexpected LLM response shape at {step!r}") from error
    return node


@dataclass(frozen=True)
class OpenAiCompatibleClient:
    """OpenAI / DeepSeek / local servers speaking chat-completions."""

    base_url: str
    api_key: str
    model: str
    transport: HttpTransport
    timeout: float = DEFAULT_TIMEOUT

    def complete(self, *, system: str, prompt: str) -> LlmCompletion:
        data = self.transport.post_json(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            payload={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=self.timeout,
        )
        text = _extract(data, "choices", 0, "message", "content")
        return LlmCompletion(text=str(text), model=self.model)


@dataclass(frozen=True)
class AnthropicClient:
    api_key: str
    model: str
    transport: HttpTransport
    base_url: str = ANTHROPIC_BASE_URL
    timeout: float = DEFAULT_TIMEOUT

    def complete(self, *, system: str, prompt: str) -> LlmCompletion:
        data = self.transport.post_json(
            f"{self.base_url}/v1/messages",
            headers={"x-api-key": self.api_key, "anthropic-version": ANTHROPIC_VERSION},
            payload={
                "model": self.model,
                "max_tokens": DEFAULT_MAX_TOKENS,
                "system": system,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=self.timeout,
        )
        text = _extract(data, "content", 0, "text")
        return LlmCompletion(text=str(text), model=self.model)


@dataclass(frozen=True)
class GoogleClient:
    api_key: str
    model: str
    transport: HttpTransport
    base_url: str = GOOGLE_BASE_URL
    timeout: float = DEFAULT_TIMEOUT

    def complete(self, *, system: str, prompt: str) -> LlmCompletion:
        data = self.transport.post_json(
            f"{self.base_url}/models/{self.model}:generateContent",
            headers={"x-goog-api-key": self.api_key},
            payload={
                "system_instruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            },
            timeout=self.timeout,
        )
        text = _extract(data, "candidates", 0, "content", "parts", 0, "text")
        return LlmCompletion(text=str(text), model=self.model)


_DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "deepseek": "deepseek-chat",
    "anthropic": "claude-sonnet-5",
    "google": "gemini-2.0-flash",
    "local": "llama3",
}


def create_client(
    provider: str,
    *,
    api_key: str,
    model: str | None = None,
    base_url: str | None = None,
    transport: HttpTransport | None = None,
) -> OpenAiCompatibleClient | AnthropicClient | GoogleClient:
    """Configuration-driven vendor selection (mirrors the ProviderRegistry)."""
    chosen = model or _DEFAULT_MODELS.get(provider)
    if chosen is None:
        raise LlmProviderError(f"unknown LLM provider: {provider!r}")
    http = transport or HttpxTransport()
    if provider == "openai":
        return OpenAiCompatibleClient(base_url or OPENAI_BASE_URL, api_key, chosen, http)
    if provider == "deepseek":
        return OpenAiCompatibleClient(base_url or DEEPSEEK_BASE_URL, api_key, chosen, http)
    if provider == "local":
        return OpenAiCompatibleClient(base_url or LOCAL_BASE_URL, api_key, chosen, http)
    if provider == "anthropic":
        return AnthropicClient(api_key, chosen, http, base_url=base_url or ANTHROPIC_BASE_URL)
    return GoogleClient(api_key, chosen, http, base_url=base_url or GOOGLE_BASE_URL)
