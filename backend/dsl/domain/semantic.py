"""Decision DSL semantic analyzer (RFC-0017 §Semantic Rules).

Checks: probability/confidence ranges (DSL006/007), positive priority,
duplicate rule names (DSL008), unknown identifiers/roots (DSL003),
unknown functions (DSL004), unknown properties (DSL013), enum membership
(DSL014), and operand type compatibility (DSL005). Emits DSL015 when a
rule violates a structural semantic rule not covered by a closer code.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from dsl.domain.ast import (
    ActionNode,
    ActionTarget,
    BinaryExpressionNode,
    ConditionNode,
    ExpressionNode,
    LiteralKind,
    ProgramNode,
    RuleNode,
    UnaryExpressionNode,
)
from dsl.domain.errors import (
    ConfidenceOutOfRangeError,
    DuplicateRuleError,
    InvalidEnumError,
    InvalidPropertyError,
    ProbabilityOutOfRangeError,
    SemanticValidationError,
    TypeMismatchError,
    UnknownFunctionError,
    UnknownIdentifierError,
)
from dsl.domain.schema import DEFAULT_SCHEMA, ROOT_OBJECTS, PropertyKind, PropertySpec
from dsl.domain.tokens import BUILTIN_FUNCTIONS

_ZERO = Decimal(0)
_ONE = Decimal(1)

_RANGE_ERRORS = {
    ActionTarget.PROBABILITY: ProbabilityOutOfRangeError,
    ActionTarget.CONFIDENCE: ConfidenceOutOfRangeError,
}


@dataclass(frozen=True)
class SemanticAnalyzer:
    schema: dict[str, dict[str, PropertySpec]]

    @classmethod
    def default(cls) -> "SemanticAnalyzer":
        return cls(schema=DEFAULT_SCHEMA)

    def analyze(self, program: ProgramNode) -> ProgramNode:
        """Validate the program; returns it unchanged when sound."""
        seen: set[str] = set()
        for rule in program.rules:
            if rule.name in seen:
                raise DuplicateRuleError(
                    f"duplicate rule name {rule.name!r}",
                    line=rule.location.line,
                    column=rule.location.column,
                )
            seen.add(rule.name)
            self._check_rule(rule)
        return program

    def _check_rule(self, rule: RuleNode) -> None:
        if rule.metadata.priority is not None and rule.metadata.priority <= 0:
            raise SemanticValidationError(
                f"rule {rule.name}: PRIORITY must be a positive integer",
                line=rule.metadata.location.line,
                column=rule.metadata.location.column,
            )
        self._check_expression(rule.when)
        for action in rule.actions:
            self._check_action(rule, action)

    def _check_action(self, rule: RuleNode, action: ActionNode) -> None:
        error = _RANGE_ERRORS.get(action.target)
        if error is None:
            return  # UTILITY and RISK adjustments are unbounded (RFC-0017)
        value = abs(action.value) if action.assign in ("+=", "-=") else action.value
        if not (_ZERO <= value <= _ONE):
            raise error(
                f"rule {rule.name}: {action.target.value} value {action.value} outside 0..1",
                line=action.location.line,
                column=action.location.column,
            )

    def _check_expression(self, expression: ExpressionNode) -> None:
        if isinstance(expression, BinaryExpressionNode):
            self._check_expression(expression.left)
            self._check_expression(expression.right)
            return
        if isinstance(expression, UnaryExpressionNode):
            self._check_expression(expression.operand)
            return
        self._check_condition(expression)

    def _check_condition(self, condition: ConditionNode) -> None:
        line, column = condition.location.line, condition.location.column
        parts = condition.identifier.split(".")
        root = parts[0]
        if root in BUILTIN_FUNCTIONS:
            raise UnknownFunctionError(
                f"function calls are not valid in conditions: {root}", line=line, column=column
            )
        if root not in ROOT_OBJECTS:
            raise UnknownIdentifierError(f"unknown root object {root!r}", line=line, column=column)
        if len(parts) < 2 or (root != "Feature" and len(parts) != 2):
            raise InvalidPropertyError(
                f"expected Root.Property, got {condition.identifier!r}",
                line=line,
                column=column,
            )
        # Feature ids themselves contain dots (Feature.quality.roe).
        prop = self.schema.get(root, {}).get(".".join(parts[1:]))
        if prop is None:
            raise InvalidPropertyError(
                f"unknown property {condition.identifier!r}", line=line, column=column
            )
        self._check_types(condition, prop)

    def _check_types(self, condition: ConditionNode, prop: PropertySpec) -> None:
        line, column = condition.literal.location.line, condition.literal.location.column
        kind = condition.literal.kind

        if prop.kind is PropertyKind.ENUM:
            if condition.operator not in ("==", "!="):
                raise TypeMismatchError(
                    f"enum property {condition.identifier} supports only == and !=",
                    line=line,
                    column=column,
                )
            if kind is not LiteralKind.ENUM:
                raise TypeMismatchError(
                    f"{condition.identifier} requires an enum literal", line=line, column=column
                )
            assert prop.enum_values is not None
            if str(condition.literal.value) not in prop.enum_values:
                raise InvalidEnumError(
                    f"{condition.literal.value!r} is not a member of "
                    f"{condition.identifier} ({sorted(prop.enum_values)})",
                    line=line,
                    column=column,
                )
            return

        if prop.kind is PropertyKind.NUMBER:
            if kind is not LiteralKind.NUMBER:
                raise TypeMismatchError(
                    f"{condition.identifier} is numeric; got {kind.value}",
                    line=line,
                    column=column,
                )
            if condition.operator == "LIKE":
                raise TypeMismatchError(
                    "LIKE applies to string properties only", line=line, column=column
                )
            return

        if prop.kind is PropertyKind.STRING:
            if kind is not LiteralKind.STRING:
                raise TypeMismatchError(
                    f"{condition.identifier} is a string; got {kind.value}",
                    line=line,
                    column=column,
                )
            if condition.operator not in ("==", "!=", "LIKE"):
                raise TypeMismatchError(
                    f"string property {condition.identifier} supports ==, != and LIKE",
                    line=line,
                    column=column,
                )
            return

        if kind is not LiteralKind.BOOLEAN:
            raise TypeMismatchError(
                f"{condition.identifier} is boolean; got {kind.value}", line=line, column=column
            )
        if condition.operator not in ("==", "!="):
            raise TypeMismatchError(
                "boolean properties support only == and !=", line=line, column=column
            )
