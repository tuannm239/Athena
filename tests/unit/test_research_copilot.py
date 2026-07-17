"""Phase 2 Module 5 — Research Copilot (never produces decisions)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from decision_kernel.application.use_cases import CreateDecisionInput, DecisionUseCases
from decision_kernel.domain.decision import Decision, DecisionStatus
from decision_kernel.domain.repository import DecisionRepository
from infrastructure.db.base import Base
from infrastructure.db.repositories.graph_store import SqlGraphStore
from knowledge.application.use_cases import KnowledgeGraphUseCases
from knowledge.domain.graph import NodeType, RelationType
from llm_gateway.application.gateway import LlmGateway
from llm_gateway.testing import FakeLlmClient
from probability.application.use_cases import ProbabilityUseCases
from research.application.copilot import ResearchCopilot, ResearchError, ReviewedDraft
from research.domain.repository import ResearchRepository
from research.domain.research_summary import ResearchSummary
from shared_kernel.events import DomainEvent
from shared_kernel.identifiers import DecisionId

NOW = datetime(2026, 7, 16, 12, 0, tzinfo=timezone.utc)

EXTRACTION = (
    "SUPPORTING|financial|Revenue grew 30% YoY\n"
    "CONTRADICTING|liquidity|Free float below exchange minimum\n"
    "NEUTRAL|governance|Board unchanged since 2020"
)


class MemoryDecisions(DecisionRepository):
    def __init__(self) -> None:
        self.rows: dict[str, Decision] = {}

    def save(self, decision: Decision) -> None:
        self.rows[str(decision.id)] = decision

    def get(self, decision_id: DecisionId) -> Decision | None:
        return self.rows.get(str(decision_id))

    def list(
        self, *, limit: int, offset: int, status: DecisionStatus | None = None
    ) -> tuple[Decision, ...]:
        items = [d for d in self.rows.values() if status is None or d.status is status]
        return tuple(items[offset : offset + limit])

    def count(self, *, status: DecisionStatus | None = None) -> int:
        return len([d for d in self.rows.values() if status is None or d.status is status])


class MemoryResearch(ResearchRepository):
    def __init__(self) -> None:
        self.rows: dict[str, ResearchSummary] = {}

    def save(self, summary: ResearchSummary) -> None:
        self.rows[str(summary.id)] = summary

    def get(self, summary_id: object) -> ResearchSummary | None:
        return self.rows.get(str(summary_id))


class NullEvents:
    def publish(self, events: tuple[DomainEvent, ...]) -> None:
        del events


@pytest.fixture()
def graph() -> KnowledgeGraphUseCases:
    engine = create_engine(
        "sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return KnowledgeGraphUseCases(
        store=SqlGraphStore(sessionmaker(bind=engine, expire_on_commit=False))
    )


def build_copilot(
    graph: KnowledgeGraphUseCases, *responses: str
) -> tuple[ResearchCopilot, MemoryDecisions, MemoryResearch]:
    decisions_repo = MemoryDecisions()
    research_repo = MemoryResearch()
    decisions = DecisionUseCases(repository=decisions_repo, events=NullEvents())
    copilot = ResearchCopilot(
        gateway=LlmGateway(client=FakeLlmClient(responses=responses), clock=lambda: NOW),
        decisions=decisions,
        probability=ProbabilityUseCases(decisions=decisions_repo),
        graph=graph,
        research=research_repo,
    )
    return copilot, decisions_repo, research_repo


def draft_decision(copilot: ResearchCopilot) -> Decision:
    return copilot.decisions.create(
        CreateDecisionInput(
            hypothesis="HPG re-rates on steel cycle recovery",
            probability=Decimal("0.5"),
            confidence=Decimal("0.4"),
        )
    )


class TestIngestDocument:
    def test_summary_drafts_and_graph_provenance(self, graph: KnowledgeGraphUseCases) -> None:
        copilot, _, research_repo = build_copilot(graph, "Steel demand recovering.", EXTRACTION)
        packet = copilot.ingest_document(
            "Long annual report…",
            subject="HPG 2025 annual report",
            source="report:HPG-2025",
            ticker="HPG",
        )
        assert packet.summary.content == "Steel demand recovering."
        assert packet.summary.sources[0] == "report:HPG-2025"
        assert packet.summary.sources[1].startswith("llm:fake-llm@")
        assert [d.direction for d in packet.drafts] == [
            "SUPPORTING",
            "CONTRADICTING",
            "NEUTRAL",
        ]
        assert str(packet.summary.id) in research_repo.rows

        snapshot = graph.snapshot()
        assert snapshot.nodes["event.report:HPG-2025"].type is NodeType.EVENT
        assert snapshot.nodes["company.HPG"].type is NodeType.COMPANY
        assert any(
            e.source_id == "event.report:HPG-2025"
            and e.relation is RelationType.AFFECTS
            and e.target_id == "company.HPG"
            for e in snapshot.edges
        )

    def test_reingest_does_not_duplicate_edges(self, graph: KnowledgeGraphUseCases) -> None:
        copilot, _, _ = build_copilot(graph, "s1", EXTRACTION, "s2", EXTRACTION)
        copilot.ingest_document("doc", subject="s", source="report:X", ticker="HPG")
        version = graph.snapshot().version
        copilot.ingest_document("doc", subject="s", source="report:X", ticker="HPG")
        assert graph.snapshot().version == version


class TestAttachReviewedEvidence:
    def test_accepted_drafts_become_lineage_tagged_evidence(
        self, graph: KnowledgeGraphUseCases
    ) -> None:
        copilot, decisions_repo, _ = build_copilot(graph, "summary", EXTRACTION)
        decision = draft_decision(copilot)
        packet = copilot.ingest_document("doc", subject="s", source="report:HPG-2025")

        reviewed = (
            ReviewedDraft(packet.drafts[0], reliability=Decimal("0.8")),
            ReviewedDraft(packet.drafts[1], reliability=Decimal("0.7")),
            ReviewedDraft(packet.drafts[2], reliability=Decimal("0.5"), accepted=False),
        )
        updated = copilot.attach_reviewed_evidence(decision.id, reviewed)

        assert len(updated.evidence) == 2  # the rejected NEUTRAL draft never lands
        supporting = updated.supporting_evidence[0]
        assert supporting.reliability.value == Decimal("0.8")  # human-set, not LLM-set
        assert supporting.metadata["source_type"] == "llm"
        assert supporting.metadata["model"] == "fake-llm"
        assert supporting.metadata["task"] == "EXTRACT_EVIDENCE"

        snapshot = graph.snapshot()
        decision_node = f"decision.{updated.id}"
        assert snapshot.nodes[decision_node].type is NodeType.DECISION
        relations = {
            (e.relation, snapshot.nodes[e.target_id].attributes["category"])
            for e in snapshot.edges
            if e.source_id == decision_node
        }
        assert relations == {
            (RelationType.SUPPORTED_BY, "financial"),
            (RelationType.CONTRADICTED_BY, "liquidity"),
        }
        assert decisions_repo.get(updated.id) is not None

    def test_nothing_accepted_is_an_error(self, graph: KnowledgeGraphUseCases) -> None:
        copilot, _, _ = build_copilot(graph, "summary", EXTRACTION)
        decision = draft_decision(copilot)
        packet = copilot.ingest_document("doc", subject="s", source="r")
        with pytest.raises(ResearchError):
            copilot.attach_reviewed_evidence(
                decision.id,
                (ReviewedDraft(packet.drafts[0], Decimal("0.8"), accepted=False),),
            )


class TestReviewFlows:
    def test_probability_review_reports_without_mutation(
        self, graph: KnowledgeGraphUseCases
    ) -> None:
        copilot, decisions_repo, _ = build_copilot(graph, "summary", EXTRACTION)
        decision = draft_decision(copilot)
        packet = copilot.ingest_document("doc", subject="s", source="r")
        copilot.attach_reviewed_evidence(
            decision.id,
            tuple(ReviewedDraft(d, Decimal("0.8")) for d in packet.drafts[:2]),
        )
        report = copilot.probability_review(decision.id)
        assert report.prior.value == Decimal("0.5")
        assert Decimal(0) <= report.posterior.value <= Decimal(1)
        stored = decisions_repo.get(decision.id)
        assert stored is not None and stored.probability.value == Decimal("0.5")

    def test_decision_review_narrates_structured_facts(self, graph: KnowledgeGraphUseCases) -> None:
        copilot, _, _ = build_copilot(graph, "summary", EXTRACTION, "A narrated review.")
        decision = draft_decision(copilot)
        packet = copilot.ingest_document("doc", subject="s", source="r")
        copilot.attach_reviewed_evidence(
            decision.id,
            tuple(ReviewedDraft(d, Decimal("0.8")) for d in packet.drafts[:2]),
        )
        review = copilot.decision_review(decision.id)
        assert review.text == "A narrated review."
        client = copilot.gateway.client
        assert isinstance(client, FakeLlmClient)
        prompt = client.calls[-1][1]
        assert "- hypothesis: HPG re-rates on steel cycle recovery" in prompt
        assert "- posterior probability:" in prompt

    def test_copilot_never_changes_decision_state(self, graph: KnowledgeGraphUseCases) -> None:
        """SPEC-00: every copilot flow leaves the decision DRAFT and
        creates no new decision."""
        copilot, decisions_repo, _ = build_copilot(graph, "summary", EXTRACTION, "narrated review")
        decision = draft_decision(copilot)
        packet = copilot.ingest_document("doc", subject="s", source="r", ticker="HPG")
        copilot.attach_reviewed_evidence(
            decision.id,
            tuple(ReviewedDraft(d, Decimal("0.8")) for d in packet.drafts[:2]),
        )
        copilot.probability_review(decision.id)
        copilot.decision_review(decision.id)

        assert decisions_repo.count() == 1
        stored = decisions_repo.get(decision.id)
        assert stored is not None and stored.status is DecisionStatus.DRAFT
