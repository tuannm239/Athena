"""Research Copilot (Phase 2, Module 5).

The SPEC-01 research flow: Document → Evidence Extraction → Knowledge
Graph → Evidence Objects → Probability Update → Decision Review.

The copilot is research-side tooling for a human reviewer. It
summarizes documents, extracts *draft* evidence via the LLM Gateway,
records provenance in the knowledge graph, attaches evidence to an
existing decision only after human review (the reviewer sets the
reliability — the LLM never rates itself, ADR-0003), and produces
probability reports and narrated review material. It never creates,
approves, rejects, sizes or archives a decision (SPEC-00): no such
method exists, and the decision status is untouched by every flow.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Iterable

from decision_kernel.application.use_cases import (
    DecisionUseCases,
    EvidenceInput,
    UpdateDecisionInput,
)
from decision_kernel.domain.decision import Decision
from decision_kernel.domain.evidence import EvidenceDirection
from knowledge.application.use_cases import KnowledgeGraphUseCases
from knowledge.domain.graph import Edge, Node, NodeType, RelationType
from llm_gateway.application.gateway import LlmGateway
from llm_gateway.domain.models import EvidenceDraft, GeneratedText
from probability.application.use_cases import ProbabilityUseCases
from probability.domain.report import ProbabilityReport
from research.domain.repository import ResearchRepository
from research.domain.research_summary import ResearchSummary
from shared_kernel.exceptions import DomainError
from shared_kernel.identifiers import DecisionId

_DIRECTION_RELATIONS: dict[EvidenceDirection, RelationType] = {
    EvidenceDirection.SUPPORTING: RelationType.SUPPORTED_BY,
    EvidenceDirection.CONTRADICTING: RelationType.CONTRADICTED_BY,
    # NEUTRAL evidence gets a node but no edge: RFC-0019 §4 has no
    # neutral decision-evidence relation.
}


class ResearchError(DomainError):
    """Copilot misuse (nothing accepted, unknown inputs)."""


@dataclass(frozen=True, slots=True)
class ReviewedDraft:
    """A human's verdict on an LLM evidence draft (ADR-0003).

    The reviewer sets the reliability; a draft the reviewer does not
    accept never becomes Evidence.
    """

    draft: EvidenceDraft
    reliability: Decimal
    accepted: bool = True


@dataclass(frozen=True, slots=True)
class ResearchPacket:
    """Copilot output for human review — never a decision."""

    summary: ResearchSummary
    drafts: tuple[EvidenceDraft, ...]


@dataclass
class ResearchCopilot:
    gateway: LlmGateway
    decisions: DecisionUseCases
    probability: ProbabilityUseCases
    graph: KnowledgeGraphUseCases
    research: ResearchRepository

    # -- Document → Evidence Extraction → KG ---------------------------------

    def ingest_document(
        self,
        document: str,
        *,
        subject: str,
        source: str,
        ticker: str | None = None,
    ) -> ResearchPacket:
        """Summarize, extract draft evidence, record provenance in the KG."""
        summary_text = self.gateway.summarize(document)
        drafts = self.gateway.extract_evidence(document, source=source)
        summary = ResearchSummary(
            subject=subject,
            content=summary_text.text,
            sources=(
                source,
                f"llm:{summary_text.lineage.model}@{summary_text.lineage.prompt_version}",
            ),
        )
        self.research.save(summary)
        if ticker is not None:
            self._record_document_event(subject=subject, source=source, ticker=ticker)
        return ResearchPacket(summary=summary, drafts=drafts)

    # -- Evidence Objects (after human review) -------------------------------

    def attach_reviewed_evidence(
        self, decision_id: DecisionId, reviewed: Iterable[ReviewedDraft]
    ) -> Decision:
        """Turn accepted drafts into Evidence on an existing decision.

        Every attached item carries its LLM lineage in the evidence
        metadata (ADR-0003 §3) and lands in the knowledge graph as an
        EVIDENCE node linked SUPPORTED_BY / CONTRADICTED_BY.
        """
        accepted = [item for item in reviewed if item.accepted]
        if not accepted:
            raise ResearchError("no accepted drafts; nothing to attach")
        inputs = tuple(
            EvidenceInput(
                source=item.draft.source,
                category=item.draft.category,
                explanation=item.draft.explanation,
                reliability=item.reliability,
                direction=EvidenceDirection(item.draft.direction),
                metadata={
                    "source_type": "llm",
                    "model": item.draft.lineage.model,
                    "prompt_version": item.draft.lineage.prompt_version,
                    "task": item.draft.lineage.task.value,
                },
            )
            for item in accepted
        )
        decision = self.decisions.update(decision_id, UpdateDecisionInput(add_evidence=inputs))
        self._link_evidence(decision, inputs)
        return decision

    # -- Probability Update → Decision Review --------------------------------

    def probability_review(
        self, decision_id: DecisionId, *, as_of: datetime | None = None
    ) -> ProbabilityReport:
        """RFC-0026 report over the decision's own prior and evidence.

        The aggregate is not mutated — accepting the posterior is an
        explicit, human action through the decisions API.
        """
        return self.probability.evaluate_decision(decision_id, as_of=as_of)

    def decision_review(
        self, decision_id: DecisionId, *, as_of: datetime | None = None
    ) -> GeneratedText:
        """Narrated review material from structured facts (ADR-0003 §4)."""
        decision = self.decisions.get(decision_id)
        report = self.probability.evaluate_decision(decision_id, as_of=as_of)
        facts = {
            "hypothesis": decision.hypothesis,
            "status": decision.status.value,
            "prior probability": str(report.prior.value),
            "posterior probability": str(report.posterior.value),
            "confidence": str(report.confidence.value),
            "supporting evidence count": str(len(decision.supporting_evidence)),
            "contradicting evidence count": str(len(decision.contradicting_evidence)),
            "assumptions": "; ".join(decision.assumptions) or "none recorded",
            "invalidation conditions": "; ".join(decision.invalidation_conditions)
            or "none recorded",
        }
        return self.gateway.explain(f"decision {decision.id}", facts)

    # -- internals -------------------------------------------------------------

    def _record_document_event(self, *, subject: str, source: str, ticker: str) -> None:
        event_id = f"event.{source}"
        company_id = f"company.{ticker}"
        self.graph.add_node(Node(event_id, NodeType.EVENT, subject, {"source": source}))
        self.graph.add_node(Node(company_id, NodeType.COMPANY, ticker))
        self._connect_once(Edge(event_id, RelationType.AFFECTS, company_id, source))

    def _link_evidence(self, decision: Decision, attached: tuple[EvidenceInput, ...]) -> None:
        decision_node = f"decision.{decision.id}"
        self.graph.add_node(Node(decision_node, NodeType.DECISION, decision.hypothesis))
        keys = {(item.source, item.category, item.explanation) for item in attached}
        for evidence in decision.evidence:
            if (evidence.source, evidence.category, evidence.explanation) not in keys:
                continue
            evidence_node = f"evidence.{evidence.id}"
            self.graph.add_node(
                Node(
                    evidence_node,
                    NodeType.EVIDENCE,
                    evidence.explanation,
                    {"category": evidence.category, "source": evidence.source},
                )
            )
            relation = _DIRECTION_RELATIONS.get(evidence.direction)
            if relation is not None:
                self._connect_once(Edge(decision_node, relation, evidence_node, evidence.source))

    def _connect_once(self, edge: Edge) -> None:
        for existing in self.graph.snapshot().edges:
            if (
                existing.source_id == edge.source_id
                and existing.relation is edge.relation
                and existing.target_id == edge.target_id
            ):
                return
        self.graph.connect(edge)
