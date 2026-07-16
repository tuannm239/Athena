"""Unit tests — Decision Compiler and graph execution (RFC-0020; RFC-0017)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from dsl.domain.compiler import COMPILER_VERSION, compile_rules
from dsl.domain.errors import CircularDependencyError, DuplicateRuleError
from dsl.domain.evaluator import FactValue, evaluate
from dsl.domain.graph import build_graph
from dsl.domain.ir import DEFAULT_PRIORITY, RuleIR, lower_rule
from dsl.domain.parser import parse

RULESET = """
RULE HighQualityCompounder
VERSION "1.0"
PRIORITY 100
WHEN
    Market.Regime == Expansion
    AND Company.ROIC > 20
    AND Company.RevenueGrowth > 15
    AND Company.DebtToEquity < 0.50
THEN
    PROBABILITY += 0.08
    CONFIDENCE += 0.05
    UTILITY += 0.12
    RISK -= 0.04
    TAG "Quality"
    TAG "Growth"
EXPLAIN "High quality compounder during expansion."

RULE ContractionCaution
PRIORITY 200
WHEN Market.Regime == Contraction
THEN
    PROBABILITY -= 0.10
    RISK += 0.10
    TAG "Defensive"
EXPLAIN "Reduce conviction during contraction."

RULE ExpensiveValuation
WHEN Company.PEPercentile > 90
THEN
    UTILITY -= 0.05
    TAG "Expensive"
EXPLAIN "Valuation stretched versus history."
"""

EXPANSION_FACTS: dict[str, FactValue] = {
    "Market.Regime": "Expansion",
    "Company.ROIC": Decimal(25),
    "Company.RevenueGrowth": Decimal(18),
    "Company.DebtToEquity": Decimal("0.3"),
    "Company.PEPercentile": Decimal(95),
}


class TestCompiler:
    def test_deterministic_compilation(self) -> None:
        first = compile_rules(RULESET)
        second = compile_rules(RULESET)
        assert first == second
        assert first.compiler_version == COMPILER_VERSION

    def test_execution_order_priority_desc_then_name(self) -> None:
        compiled = compile_rules(RULESET)
        assert compiled.rule_ids == (
            "ContractionCaution",
            "HighQualityCompounder",
            "ExpensiveValuation",
        )
        assert compiled.rules[0].priority == 100
        assert compiled.graph.nodes[-1].priority == DEFAULT_PRIORITY

    def test_semantic_errors_propagate(self) -> None:
        with pytest.raises(DuplicateRuleError):
            compile_rules(RULESET + RULESET)

    def test_ir_carries_metadata_and_location(self) -> None:
        rule = compile_rules(RULESET).graph.nodes[1]
        assert isinstance(rule, RuleIR)
        assert rule.version == "1.0"
        assert rule.tags == ("Quality", "Growth")
        assert rule.explain and "compounder" in rule.explain
        assert rule.location.line > 0

    def test_cycle_guard_dsl009(self) -> None:
        import dataclasses

        base = lower_rule(parse('RULE A WHEN Company.ROIC > 1 THEN TAG "a"').rules[0])
        a = dataclasses.replace(base, rule_id="A", dependencies=("B",))
        b = dataclasses.replace(base, rule_id="B", dependencies=("A",))
        with pytest.raises(CircularDependencyError):
            build_graph((a, b))


class TestEvaluation:
    def test_golden_expansion_outcome(self) -> None:
        compiled = compile_rules(RULESET)
        outcome = evaluate(compiled.graph, EXPANSION_FACTS)
        assert [m.rule_id for m in outcome.matched] == [
            "HighQualityCompounder",
            "ExpensiveValuation",
        ]
        assert outcome.unmatched == ("ContractionCaution",)
        assert outcome.probability == Decimal("0.58")
        assert outcome.confidence == Decimal("0.55")
        assert outcome.utility == Decimal("0.07")
        assert outcome.risk_adjustment == Decimal("-0.04")
        assert outcome.tags == ("Quality", "Growth", "Expensive")
        assert len(outcome.explanations) == 2

    def test_reproducible_execution(self) -> None:
        compiled = compile_rules(RULESET)
        assert evaluate(compiled.graph, EXPANSION_FACTS) == evaluate(
            compiled.graph, EXPANSION_FACTS
        )

    def test_missing_facts_mean_no_match(self) -> None:
        compiled = compile_rules(RULESET)
        outcome = evaluate(compiled.graph, {})
        assert outcome.matched == ()
        assert outcome.probability == Decimal("0.5")

    def test_probability_clamped_to_unit_interval(self) -> None:
        source = (
            "RULE Up WHEN Company.ROIC > 1 THEN PROBABILITY += 0.9 "
            "RULE Up2 PRIORITY 2 WHEN Company.ROIC > 1 THEN PROBABILITY += 0.9"
        )
        compiled = compile_rules(source)
        outcome = evaluate(compiled.graph, {"Company.ROIC": Decimal(2)})
        assert outcome.probability == Decimal(1)

    def test_set_assignment_and_negative_utility(self) -> None:
        source = "RULE S WHEN Company.ROIC > 1 THEN PROBABILITY = 0.9 UTILITY = -0.5"
        outcome = evaluate(compile_rules(source).graph, {"Company.ROIC": Decimal(2)})
        assert outcome.probability == Decimal("0.9")
        assert outcome.utility == Decimal("-0.5")

    def test_not_or_and_like_semantics(self) -> None:
        source = (
            "RULE N WHEN NOT Market.Regime == Contraction "
            'AND (Company.Ticker LIKE "A%" OR Company.Ticker == "ZZZ") THEN TAG "n"'
        )
        graph = compile_rules(source).graph
        assert evaluate(graph, {"Market.Regime": "Expansion", "Company.Ticker": "AAA"}).matched
        assert not evaluate(
            graph, {"Market.Regime": "Contraction", "Company.Ticker": "AAA"}
        ).matched
        assert evaluate(graph, {"Market.Regime": "Recovery", "Company.Ticker": "ZZZ"}).matched

    def test_type_disagreement_never_matches(self) -> None:
        source = 'RULE T WHEN Company.ROIC > 1 THEN TAG "t"'
        outcome = evaluate(compile_rules(source).graph, {"Company.ROIC": "high"})
        assert outcome.matched == ()
