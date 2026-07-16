"""Phase 2 Module 4 — LLM Gateway (ADR-0003)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping

import pytest

from llm_gateway.adapters import (
    AnthropicClient,
    GoogleClient,
    OpenAiCompatibleClient,
    create_client,
)
from llm_gateway.application.gateway import PROMPT_VERSION, LlmGateway
from llm_gateway.domain.models import (
    EvidenceDraft,
    LlmGatewayError,
    LlmLineage,
    LlmProviderError,
    LlmTask,
)
from llm_gateway.testing import FakeLlmClient

NOW = datetime(2026, 7, 16, 12, 0, tzinfo=timezone.utc)


def gateway(*responses: str) -> LlmGateway:
    return LlmGateway(client=FakeLlmClient(responses=responses), clock=lambda: NOW)


class TestLineage:
    def test_every_artifact_is_lineage_tagged(self) -> None:
        summary = gateway("A short summary.").summarize("Long research text.")
        assert summary.text == "A short summary."
        assert summary.lineage == LlmLineage(
            model="fake-llm",
            prompt_version=PROMPT_VERSION,
            task=LlmTask.SUMMARIZE,
            generated_at=NOW,
        )
        assert summary.lineage.source == "llm"

    def test_lineage_source_cannot_be_forged(self) -> None:
        with pytest.raises(LlmGatewayError):
            LlmLineage(
                model="m",
                prompt_version="v",
                task=LlmTask.SUMMARIZE,
                generated_at=NOW,
                source="human",
            )


class TestAllowedUses:
    def test_summarize_rejects_empty_input(self) -> None:
        with pytest.raises(LlmGatewayError):
            gateway().summarize("   ")

    def test_classify_enforces_label_set(self) -> None:
        result = gateway("negative").classify("Profit warning issued.", ("positive", "negative"))
        assert result.label == "negative"
        assert result.lineage.task is LlmTask.CLASSIFY
        with pytest.raises(LlmGatewayError):
            gateway("BUY THE STOCK").classify("text", ("positive", "negative"))

    def test_explain_requires_facts_and_passes_them_verbatim(self) -> None:
        with pytest.raises(LlmGatewayError):
            gateway().explain("the decision", {})
        client = FakeLlmClient(responses=("Because X and Y.",))
        explained = LlmGateway(client=client, clock=lambda: NOW).explain(
            "the decision", {"risk": "MODERATE"}
        )
        assert explained.lineage.task is LlmTask.EXPLAIN
        assert "- risk: MODERATE" in client.calls[-1][1]

    def test_report_preserves_lineage(self) -> None:
        report = gateway("# Report").generate_report("Q2", {"Summary": "content"})
        assert report.lineage.task is LlmTask.REPORT


class TestEvidenceExtraction:
    def test_parses_wellformed_lines_and_drops_noise(self) -> None:
        response = (
            "SUPPORTING|financial|Revenue grew 30% YoY\n"
            "garbage line without pipes\n"
            "SIDEWAYS|foo|not a direction\n"
            "CONTRADICTING|liquidity|Free float below exchange minimum"
        )
        drafts = gateway(response).extract_evidence("annual report text", source="report:2025")
        assert [d.direction for d in drafts] == ["SUPPORTING", "CONTRADICTING"]
        assert drafts[0] == EvidenceDraft(
            source="report:2025",
            category="financial",
            direction="SUPPORTING",
            explanation="Revenue grew 30% YoY",
            lineage=drafts[0].lineage,
        )
        assert drafts[0].lineage.task is LlmTask.EXTRACT_EVIDENCE

    def test_no_parseable_lines_is_an_error(self) -> None:
        with pytest.raises(LlmGatewayError):
            gateway("nothing useful").extract_evidence("doc", source="s")

    def test_invalid_direction_rejected_at_construction(self) -> None:
        lineage = LlmLineage(
            model="m", prompt_version="v", task=LlmTask.EXTRACT_EVIDENCE, generated_at=NOW
        )
        with pytest.raises(LlmGatewayError):
            EvidenceDraft("s", "c", "SIDEWAYS", "e", lineage)


class RecordingTransport:
    def __init__(self, response: Mapping[str, object]) -> None:
        self.response = response
        self.url = ""
        self.headers: Mapping[str, str] = {}
        self.payload: Mapping[str, object] = {}

    def post_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        payload: Mapping[str, object],
        timeout: float,
    ) -> Mapping[str, object]:
        self.url, self.headers, self.payload = url, headers, payload
        return self.response


class TestAdapters:
    def test_openai_compatible_contract(self) -> None:
        transport = RecordingTransport(
            {"choices": [{"message": {"content": "hello"}}]},
        )
        client = OpenAiCompatibleClient(
            "https://api.openai.com/v1", "sk-x", "gpt-4o-mini", transport
        )
        completion = client.complete(system="sys", prompt="hi")
        assert completion.text == "hello" and completion.model == "gpt-4o-mini"
        assert transport.url.endswith("/chat/completions")
        assert transport.headers["Authorization"] == "Bearer sk-x"
        messages = transport.payload["messages"]
        assert isinstance(messages, list) and messages[0]["role"] == "system"

    def test_anthropic_contract(self) -> None:
        transport = RecordingTransport({"content": [{"text": "hello"}]})
        client = AnthropicClient("key", "claude-sonnet-5", transport)
        completion = client.complete(system="sys", prompt="hi")
        assert completion.text == "hello"
        assert transport.url.endswith("/v1/messages")
        assert transport.headers["x-api-key"] == "key"
        assert transport.payload["system"] == "sys"

    def test_google_contract(self) -> None:
        transport = RecordingTransport(
            {"candidates": [{"content": {"parts": [{"text": "hello"}]}}]},
        )
        client = GoogleClient("key", "gemini-2.0-flash", transport)
        completion = client.complete(system="sys", prompt="hi")
        assert completion.text == "hello"
        assert ":generateContent" in transport.url
        assert transport.headers["x-goog-api-key"] == "key"

    def test_malformed_response_is_provider_error(self) -> None:
        transport = RecordingTransport({"unexpected": True})
        client = AnthropicClient("key", "claude-sonnet-5", transport)
        with pytest.raises(LlmProviderError):
            client.complete(system="s", prompt="p")

    def test_create_client_is_configuration_driven(self) -> None:
        transport = RecordingTransport({})
        openai = create_client("openai", api_key="k", transport=transport)
        assert isinstance(openai, OpenAiCompatibleClient)
        assert openai.base_url == "https://api.openai.com/v1"
        deepseek = create_client("deepseek", api_key="k", transport=transport)
        assert isinstance(deepseek, OpenAiCompatibleClient)
        assert deepseek.model == "deepseek-chat"
        local = create_client(
            "local", api_key="k", base_url="http://box:8080/v1", transport=transport
        )
        assert isinstance(local, OpenAiCompatibleClient)
        assert local.base_url == "http://box:8080/v1"
        assert isinstance(
            create_client("anthropic", api_key="k", transport=transport), AnthropicClient
        )
        assert isinstance(create_client("google", api_key="k", transport=transport), GoogleClient)
        with pytest.raises(LlmProviderError):
            create_client("mystery", api_key="k", transport=transport)
