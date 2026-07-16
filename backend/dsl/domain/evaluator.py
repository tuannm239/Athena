"""Deterministic Decision Graph execution (RFC-0020 §4; RFC-0017).

Evaluates compiled rules against a fact context and accumulates the
THEN-action adjustments. Semantics codified here:

- Facts map fully-qualified properties (``Company.ROIC``) to values.
- A condition over a missing fact evaluates to False (the rule simply
  does not match; the outcome records it as unmatched).
- ``=`` sets, ``+=`` adds, ``-=`` subtracts; PROBABILITY and CONFIDENCE
  are clamped to [0, 1] after every action (their per-action literals
  are already range-checked by DSL006/007).
- ``LIKE`` matches strings with ``%`` wildcards, case-sensitively.
- Rules execute in graph order (priority desc, rule id asc); identical
  facts and graph produce identical outcomes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping

from dsl.domain.ast import (
    ActionTarget,
    BinaryExpressionNode,
    ConditionNode,
    ExpressionNode,
    LiteralKind,
    UnaryExpressionNode,
)
from dsl.domain.graph import DecisionGraph

FactValue = Decimal | str | bool
_ZERO = Decimal(0)
_ONE = Decimal(1)


@dataclass(frozen=True, slots=True)
class RuleMatch:
    rule_id: str
    tags: tuple[str, ...]
    explain: str | None


@dataclass(frozen=True, slots=True)
class EvaluationOutcome:
    """Aggregated adjustments from all matched rules."""

    matched: tuple[RuleMatch, ...]
    unmatched: tuple[str, ...]
    probability: Decimal
    confidence: Decimal
    utility: Decimal
    risk_adjustment: Decimal
    tags: tuple[str, ...]
    explanations: tuple[str, ...]


def _like(value: str, pattern: str) -> bool:
    regex = "^" + ".*".join(re.escape(part) for part in pattern.split("%")) + "$"
    return re.match(regex, value) is not None


def _condition_holds(condition: ConditionNode, facts: Mapping[str, FactValue]) -> bool:
    fact = facts.get(condition.identifier)
    if fact is None:
        return False
    literal = condition.literal
    operator = condition.operator

    if literal.kind is LiteralKind.NUMBER and isinstance(fact, Decimal):
        assert isinstance(literal.value, Decimal)
        return _compare(fact, operator, literal.value)
    if literal.kind is LiteralKind.ENUM and isinstance(fact, str):
        return (fact == literal.value) if operator == "==" else (fact != literal.value)
    if literal.kind is LiteralKind.STRING and isinstance(fact, str):
        assert isinstance(literal.value, str)
        if operator == "LIKE":
            return _like(fact, literal.value)
        return (fact == literal.value) if operator == "==" else (fact != literal.value)
    if literal.kind is LiteralKind.BOOLEAN and isinstance(fact, bool):
        return (fact is literal.value) if operator == "==" else (fact is not literal.value)
    return False  # NULL literals and fact/literal type disagreements never match


def _compare(left: Decimal, operator: str, right: Decimal) -> bool:
    if operator == "==":
        return left == right
    if operator == "!=":
        return left != right
    if operator == ">":
        return left > right
    if operator == ">=":
        return left >= right
    if operator == "<":
        return left < right
    return left <= right


def _matches(expression: ExpressionNode, facts: Mapping[str, FactValue]) -> bool:
    if isinstance(expression, BinaryExpressionNode):
        if expression.operator == "AND":
            return _matches(expression.left, facts) and _matches(expression.right, facts)
        return _matches(expression.left, facts) or _matches(expression.right, facts)
    if isinstance(expression, UnaryExpressionNode):
        return not _matches(expression.operand, facts)
    return _condition_holds(expression, facts)


def _clamp01(value: Decimal) -> Decimal:
    return min(max(value, _ZERO), _ONE)


def evaluate(
    graph: DecisionGraph,
    facts: Mapping[str, FactValue],
    *,
    base_probability: Decimal = Decimal("0.5"),
    base_confidence: Decimal = Decimal("0.5"),
) -> EvaluationOutcome:
    """Execute the graph over facts; reproducible for identical inputs."""
    probability = base_probability
    confidence = base_confidence
    utility = _ZERO
    risk = _ZERO
    matched: list[RuleMatch] = []
    unmatched: list[str] = []
    tags: list[str] = []
    explanations: list[str] = []

    for node in graph.nodes:
        if not _matches(node.condition, facts):
            unmatched.append(node.rule_id)
            continue
        matched.append(RuleMatch(rule_id=node.rule_id, tags=node.tags, explain=node.explain))
        for action in node.actions:
            current = {
                ActionTarget.PROBABILITY: probability,
                ActionTarget.CONFIDENCE: confidence,
                ActionTarget.UTILITY: utility,
                ActionTarget.RISK: risk,
            }[action.target]
            if action.assign == "=":
                updated = action.value
            elif action.assign == "+=":
                updated = current + action.value
            else:
                updated = current - action.value
            if action.target in (ActionTarget.PROBABILITY, ActionTarget.CONFIDENCE):
                updated = _clamp01(updated)
            if action.target is ActionTarget.PROBABILITY:
                probability = updated
            elif action.target is ActionTarget.CONFIDENCE:
                confidence = updated
            elif action.target is ActionTarget.UTILITY:
                utility = updated
            else:
                risk = updated
        for tag in node.tags:
            if tag not in tags:
                tags.append(tag)
        if node.explain:
            explanations.append(f"{node.rule_id}: {node.explain}")

    return EvaluationOutcome(
        matched=tuple(matched),
        unmatched=tuple(unmatched),
        probability=probability,
        confidence=confidence,
        utility=utility,
        risk_adjustment=risk,
        tags=tuple(tags),
        explanations=tuple(explanations),
    )
