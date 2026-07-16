"""Decision DSL abstract syntax tree (RFC-0017 §AST Nodes).

All nodes are immutable; identical source produces an identical AST
(acceptance criterion 1).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


@dataclass(frozen=True, slots=True)
class SourceLocation:
    line: int
    column: int


class LiteralKind(StrEnum):
    NUMBER = "NUMBER"
    STRING = "STRING"
    BOOLEAN = "BOOLEAN"
    NULL = "NULL"
    ENUM = "ENUM"  # bare identifier literal, e.g. Expansion


@dataclass(frozen=True, slots=True)
class LiteralNode:
    kind: LiteralKind
    value: Decimal | str | bool | None
    location: SourceLocation


@dataclass(frozen=True, slots=True)
class ConditionNode:
    """condition ::= identifier operator literal (e.g. Company.ROIC > 20)."""

    identifier: str
    operator: str
    literal: LiteralNode
    location: SourceLocation


@dataclass(frozen=True, slots=True)
class UnaryExpressionNode:
    operator: str  # NOT
    operand: ExpressionNode
    location: SourceLocation


@dataclass(frozen=True, slots=True)
class BinaryExpressionNode:
    operator: str  # AND | OR
    left: ExpressionNode
    right: ExpressionNode
    location: SourceLocation


ExpressionNode = ConditionNode | UnaryExpressionNode | BinaryExpressionNode


class ActionTarget(StrEnum):
    PROBABILITY = "PROBABILITY"
    CONFIDENCE = "CONFIDENCE"
    UTILITY = "UTILITY"
    RISK = "RISK"


@dataclass(frozen=True, slots=True)
class ActionNode:
    """PROBABILITY/CONFIDENCE/UTILITY/RISK  (=|+=|-=)  number."""

    target: ActionTarget
    assign: str  # = | += | -=
    value: Decimal
    location: SourceLocation


@dataclass(frozen=True, slots=True)
class TagNode:
    value: str
    location: SourceLocation


@dataclass(frozen=True, slots=True)
class ExplainNode:
    text: str
    location: SourceLocation


@dataclass(frozen=True, slots=True)
class MetadataNode:
    version: str | None
    priority: int | None
    location: SourceLocation


@dataclass(frozen=True, slots=True)
class RuleNode:
    name: str
    metadata: MetadataNode
    when: ExpressionNode
    actions: tuple[ActionNode, ...]
    tags: tuple[TagNode, ...]
    explain: ExplainNode | None
    location: SourceLocation


@dataclass(frozen=True, slots=True)
class ProgramNode:
    rules: tuple[RuleNode, ...]
