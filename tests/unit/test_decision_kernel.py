"""Unit tests — Decision Kernel ALG-012 (SPEC-04; RFC-0020; ADR-0013)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from decision_kernel.application.kernel import DecisionKernel, KernelError, KernelInput
from decision_kernel.domain.decision import Decision
from decision_kernel.domain.evidence import Evidence, EvidenceDirection
from dsl.domain.compiler import COMPILER_VERSION, compile_rules
from risk.domain.risk_assessment import RiskAssessment, RiskLevel
from shared_kernel.probability import Confidence, Probability, Reliability

AS_OF = datetime(2026, 7, 16, tzinfo=timezone.utc)

RULESET = """
RULE HighQualityCompounder
PRIORITY 100
WHEN Market.Regime == Expansion AND Company.ROIC > 20
THEN PROBABILITY += 0.05 UTILITY += 0.1 RISK -= 0.02 TAG "Quality"
EXPLAIN "Quality compounding in expansion."

RULE ContractionCaution
PRIORITY 200
WHEN Market.Regime == Contraction
THEN PROBABILITY -= 0.10 TAG "Defensive"
EXPLAIN "Contraction regime."
"""


def evidence(direction: EvidenceDirection, text: str) -> Evidence:
    return Evidence(
        source="unit",
        category="fundamental",
        reliability=Reliability(Decimal("0.8")),
        direction=direction,
        explanation=text,
        timestamp=AS_OF - timedelta(days=30),
    )


def decision() -> Decision:
    d = Decision(
        hypothesis="Company X outperforms its sector over 12 months",
        probability=Probability(Decimal("0.55")),
        confidence=Confidence(Decimal("0.6")),
        expected_return=Decimal("0.2"),
        expected_drawdown=Decimal("0.1"),
        assumptions=("margins hold",),
        invalidation_conditions=("guidance cut",),
    )
    d.add_evidence(evidence(EvidenceDirection.SUPPORTING, "strong FCF"))
    d.add_evidence(evidence(EvidenceDirection.CONTRADICTING, "rich multiple"))
    return d


def risk() -> RiskAssessment:
    return RiskAssessment(
        var=Decimal("0.03"),
        cvar=Decimal("0.04"),
        max_drawdown=Decimal("0.2"),
        stress_score=Decimal("0.3"),
        liquidity_score=Decimal("0.2"),
        level=RiskLevel.MODERATE,
        confidence=Confidence(Decimal("0.9")),
    )


def kernel_input(**overrides: object) -> KernelInput:
    base: dict[str, object] = {
        "decision": decision(),
        "ruleset": compile_rules(RULESET),
        "facts": {"Market.Regime": "Expansion", "Company.ROIC": Decimal(25)},
        "as_of": AS_OF,
        "risk_assessment": risk(),
        "max_position_weight": Decimal("0.1"),
    }
    base.update(overrides)
    return KernelInput(**base)  # type: ignore[arg-type]


class TestKernelPipeline:
    def test_produces_complete_decision_object(self) -> None:
        obj = DecisionKernel().evaluate(kernel_input())
        assert obj.hypothesis.startswith("Company X")
        assert obj.matched_rules == ("HighQualityCompounder",)
        assert obj.tags == ("Quality",)
        assert obj.compiler_version == COMPILER_VERSION
        assert obj.evidence == ("strong FCF",)
        assert obj.counter_evidence == ("rich multiple",)
        assert Decimal(0) < obj.probability.value < Decimal(1)
        assert obj.expected_utility > Decimal(0)
        assert obj.risk_adjustment == Decimal("-0.02")
        assert Decimal(0) < obj.position_size <= Decimal("0.1")
        assert "target weight" in obj.portfolio_impact
        rendered = obj.explanation.render()
        assert "WHY:" in rendered and "KEY RISKS:" in rendered

    def test_deterministic(self) -> None:
        data = kernel_input()
        assert DecisionKernel().evaluate(data) == DecisionKernel().evaluate(data)

    def test_dsl_adjustments_apply_on_posterior(self) -> None:
        with_rules = DecisionKernel().evaluate(kernel_input())
        no_match = DecisionKernel().evaluate(kernel_input(facts={"Market.Regime": "Consolidation"}))
        assert with_rules.probability.value == no_match.probability.value + Decimal("0.05")
        assert no_match.matched_rules == ()
        assert no_match.tags == ()

    def test_contraction_rule_reduces_probability(self) -> None:
        contraction = DecisionKernel().evaluate(
            kernel_input(facts={"Market.Regime": "Contraction"})
        )
        neutral = DecisionKernel().evaluate(kernel_input(facts={"Market.Regime": "Consolidation"}))
        assert contraction.probability.value < neutral.probability.value
        assert "Defensive" in contraction.tags


class TestKernelBusinessRules:
    def test_supporting_evidence_required(self) -> None:
        d = Decision(
            hypothesis="X",
            probability=Probability(Decimal("0.5")),
            confidence=Confidence(Decimal("0.5")),
            invalidation_conditions=("y",),
        )
        d.add_evidence(evidence(EvidenceDirection.CONTRADICTING, "bear"))
        with pytest.raises(KernelError):
            DecisionKernel().evaluate(kernel_input(decision=d))

    def test_counter_evidence_required(self) -> None:
        d = Decision(
            hypothesis="X",
            probability=Probability(Decimal("0.5")),
            confidence=Confidence(Decimal("0.5")),
            invalidation_conditions=("y",),
        )
        d.add_evidence(evidence(EvidenceDirection.SUPPORTING, "bull"))
        with pytest.raises(KernelError):
            DecisionKernel().evaluate(kernel_input(decision=d))

    def test_invalidation_conditions_required(self) -> None:
        d = decision()
        d.invalidation_conditions = ()
        with pytest.raises(KernelError):
            DecisionKernel().evaluate(kernel_input(decision=d))

    def test_risk_assessment_required(self) -> None:
        with pytest.raises(KernelError):
            DecisionKernel().evaluate(kernel_input(risk_assessment=None))

    def test_kernel_has_no_llm_import_path(self) -> None:
        import decision_kernel.application.kernel as kernel_module

        forbidden = ("llm", "openai", "anthropic")
        source = open(kernel_module.__file__).read().lower()
        assert not any(f"import {name}" in source for name in forbidden)


class TestKernelWithoutSizingInputs:
    def test_missing_return_inputs_yield_zero_size(self) -> None:
        d = decision()
        d.expected_return = None
        d.expected_drawdown = None
        obj = DecisionKernel().evaluate(kernel_input(decision=d))
        assert obj.position_size == Decimal(0)
        assert obj.expected_utility == Decimal("0.1")  # DSL adjustment only
