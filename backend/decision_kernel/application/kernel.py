"""Decision Kernel — ALG-012 (SPEC-04; RFC-0020; ADR-0013).

The SPEC-04 pipeline:
1 validate input · 2 build hypothesis · 3 collect supporting evidence ·
4 collect counter evidence · 5 estimate probability · 6 estimate
confidence · 7 evaluate portfolio impact · 8 evaluate risk ·
9 calculate expected utility · 10 generate explanation ·
11 produce decision object.

Deterministic and non-LLM (SPEC-00; ADR-0003): identical inputs produce
an identical Decision Object. Engines are injected behind Protocols
(ADR-0013) with the platform implementations as defaults.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Mapping, Protocol

from decision_kernel.domain.decision import Decision
from decision_kernel.domain.decision_object import DecisionObject, KernelExplanation
from decision_kernel.domain.evidence import Evidence
from dsl.domain.compiler import CompiledRuleset
from dsl.domain.evaluator import EvaluationOutcome, FactValue
from dsl.domain.evaluator import evaluate as evaluate_graph
from dsl.domain.graph import DecisionGraph
from portfolio.domain.sizing import position_size
from probability.domain.engine import ProbabilityEngine, expected_utility
from probability.domain.report import ProbabilityReport
from risk.domain.risk_assessment import RiskAssessment
from shared_kernel.exceptions import DomainError
from shared_kernel.probability import Confidence, Probability

_kernel_log = logging.getLogger("athena.decision_kernel")


class KernelError(DomainError):
    """Raised when SPEC-04 business rules block kernel evaluation."""


class ProbabilityPort(Protocol):
    def __call__(
        self,
        *,
        hypothesis: str,
        prior: Probability,
        evidence: tuple[Evidence, ...],
        as_of: datetime,
        expected_return: Decimal | None,
        expected_drawdown: Decimal | None,
        assumptions: tuple[str, ...],
    ) -> ProbabilityReport: ...


class GraphExecutionPort(Protocol):
    def __call__(
        self,
        graph: DecisionGraph,
        facts: Mapping[str, FactValue],
        *,
        base_probability: Decimal,
        base_confidence: Decimal,
    ) -> EvaluationOutcome: ...


class SizingPort(Protocol):
    def __call__(
        self,
        *,
        posterior: Probability,
        expected_return: Decimal,
        expected_drawdown: Decimal,
        risk_budget: Decimal,
        liquidity_factor: Decimal,
        confidence: Confidence,
        max_position_weight: Decimal | None,
    ) -> object: ...


def _default_probability(**kwargs: object) -> ProbabilityReport:
    return ProbabilityEngine().evaluate(**kwargs)  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class KernelInput:
    """Everything the kernel needs; no hidden state (ADR-0013)."""

    decision: Decision
    ruleset: CompiledRuleset
    facts: Mapping[str, FactValue]
    as_of: datetime
    risk_assessment: RiskAssessment | None = None
    risk_budget: Decimal = Decimal(1)
    liquidity_factor: Decimal = Decimal(1)
    max_position_weight: Decimal | None = None


@dataclass(frozen=True)
class DecisionKernel:
    """SPEC-04 evaluation pipeline over injected engine ports."""

    probability_port: ProbabilityPort = field(default=_default_probability)
    graph_port: GraphExecutionPort = field(default=evaluate_graph)

    def evaluate(self, data: KernelInput) -> DecisionObject:
        decision = data.decision

        # 1–4: validate input and evidence (SPEC-04 Business Rules).
        if not decision.hypothesis:
            raise KernelError("no decision without a hypothesis")
        if not decision.supporting_evidence:
            raise KernelError("no decision without evidence (SPEC-04)")
        if not decision.contradicting_evidence:
            raise KernelError("counter evidence is mandatory (SPEC-04)")
        if not decision.invalidation_conditions:
            raise KernelError("every decision must define invalidation conditions (SPEC-04)")
        risk = data.risk_assessment or decision.risk_assessment
        if risk is None:
            raise KernelError("risk before return: a risk assessment is required (SPEC-11)")

        # 5–6: probability and confidence (RFC-0026 pipeline).
        report = self.probability_port(
            hypothesis=decision.hypothesis,
            prior=decision.probability,
            evidence=decision.evidence,
            as_of=data.as_of,
            expected_return=decision.expected_return,
            expected_drawdown=decision.expected_drawdown,
            assumptions=decision.assumptions,
        )

        # Rule adjustments on top of the Bayesian posterior (RFC-0020 order).
        outcome = self.graph_port(
            data.ruleset.graph,
            data.facts,
            base_probability=report.posterior.value,
            base_confidence=report.confidence.value,
        )
        probability = Probability(outcome.probability)
        confidence = Confidence(outcome.confidence)

        # 9: expected utility at the final probability + DSL adjustments.
        base_utility = expected_utility(
            probability, decision.expected_return, decision.expected_drawdown
        )
        total_utility = (base_utility or Decimal(0)) + outcome.utility

        # 7: portfolio impact via ALG-007 sizing (RFC-0027 §5).
        if decision.expected_return is not None and decision.expected_drawdown is not None:
            size = position_size(
                posterior=probability,
                expected_return=decision.expected_return,
                expected_drawdown=decision.expected_drawdown,
                risk_budget=data.risk_budget,
                liquidity_factor=data.liquidity_factor,
                confidence=confidence,
                max_position_weight=data.max_position_weight,
            ).value
        else:
            size = Decimal(0)
        impact = (
            f"target weight {size} of portfolio value under risk budget "
            f"{data.risk_budget} (liquidity factor {data.liquidity_factor})"
        )

        # 10: SPEC-04 §Explainability — six facets, every claim traceable.
        explanation = self._explain(decision, report, outcome, risk)

        # 11: the Decision Object (RFC-0020 §6) — logged for decision-trace.
        _kernel_log.info(
            "decision evaluated",
            extra={
                "decision_id": str(decision.id),
                "request_id": None,
            },
        )
        return DecisionObject(
            decision_id=decision.id,
            hypothesis=decision.hypothesis,
            evidence=tuple(e.explanation for e in decision.supporting_evidence),
            counter_evidence=tuple(e.explanation for e in decision.contradicting_evidence),
            matched_rules=tuple(m.rule_id for m in outcome.matched),
            probability=probability,
            confidence=confidence,
            expected_return=decision.expected_return,
            expected_drawdown=decision.expected_drawdown,
            expected_utility=total_utility,
            risk_adjustment=outcome.risk_adjustment,
            risk_assessment=risk,
            portfolio_impact=impact,
            position_size=size,
            tags=outcome.tags,
            assumptions=decision.assumptions,
            invalidation_conditions=decision.invalidation_conditions,
            compiler_version=data.ruleset.compiler_version,
            explanation=explanation,
        )

    @staticmethod
    def _explain(
        decision: Decision,
        report: ProbabilityReport,
        outcome: EvaluationOutcome,
        risk: RiskAssessment,
    ) -> KernelExplanation:
        why = tuple(e.explanation for e in decision.supporting_evidence) + outcome.explanations
        why_not = tuple(e.explanation for e in decision.contradicting_evidence) + tuple(
            f"rule {rule_id} did not match" for rule_id in outcome.unmatched
        )
        missing = () if decision.evidence else ("no evidence recorded",)
        key_risks = (
            f"risk level {risk.level.value} "
            f"(VaR95={risk.var}, CVaR95={risk.cvar}, maxDD={risk.max_drawdown})",
        ) + tuple(decision.invalidation_conditions)
        alternatives = (
            f"posterior would revert toward prior {report.prior.value} "
            "if supporting evidence decays (freshness horizon 365d)",
            "regime change re-triggers rule evaluation (RFC-0025)",
        )
        return KernelExplanation(
            why=why,
            why_not=why_not,
            assumptions=decision.assumptions,
            missing_information=missing,
            key_risks=key_risks,
            alternative_scenarios=alternatives,
        )
