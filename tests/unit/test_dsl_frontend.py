"""Unit tests — Decision DSL lexer, parser, AST, semantics (RFC-0017)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from dsl.domain.ast import (
    ActionTarget,
    BinaryExpressionNode,
    ConditionNode,
    LiteralKind,
    UnaryExpressionNode,
)
from dsl.domain.errors import (
    ConfidenceOutOfRangeError,
    DslError,
    DuplicateRuleError,
    InvalidActionError,
    InvalidEnumError,
    InvalidPropertyError,
    InvalidSyntaxError,
    InvalidTokenError,
    MissingThenError,
    MissingWhenError,
    ProbabilityOutOfRangeError,
    SemanticValidationError,
    TypeMismatchError,
    UnknownFunctionError,
    UnknownIdentifierError,
)
from dsl.domain.lexer import tokenize
from dsl.domain.parser import parse
from dsl.domain.semantic import SemanticAnalyzer
from dsl.domain.tokens import TokenType

GOLDEN = """
// RFC-0017 golden example
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
"""


def analyze(source: str) -> None:
    SemanticAnalyzer.default().analyze(parse(source))


class TestLexer:
    def test_golden_token_stream_is_deterministic(self) -> None:
        assert tokenize(GOLDEN) == tokenize(GOLDEN)
        kinds = {t.type for t in tokenize(GOLDEN)}
        assert TokenType.KEYWORD in kinds and TokenType.NUMBER in kinds

    def test_comments_are_skipped(self) -> None:
        src = '/* multi\nline */ RULE R // trailing\nWHEN Company.ROIC > 1 THEN TAG "x"'
        values = [t.value for t in tokenize(src) if t.type is TokenType.KEYWORD]
        assert values[0] == "RULE"

    def test_dotted_identifier_is_one_token(self) -> None:
        tokens = tokenize("Company.DebtToEquity")
        assert tokens[0].value == "Company.DebtToEquity"

    def test_invalid_character_is_dsl001(self) -> None:
        with pytest.raises(InvalidTokenError) as e:
            tokenize("RULE @")
        assert "DSL001" in str(e.value)

    def test_unterminated_string_and_comment(self) -> None:
        with pytest.raises(InvalidTokenError):
            tokenize('EXPLAIN "no end')
        with pytest.raises(InvalidTokenError):
            tokenize("/* forever")

    def test_malformed_number_and_identifier(self) -> None:
        with pytest.raises(InvalidTokenError):
            tokenize("Company.ROIC > 3.")
        with pytest.raises(InvalidTokenError):
            tokenize("Company..ROIC > 3")

    def test_source_locations(self) -> None:
        tokens = tokenize('RULE R\nWHEN Company.ROIC > 1 THEN TAG "t"')
        when = next(t for t in tokens if t.value == "WHEN")
        assert (when.line, when.column) == (2, 1)


class TestParser:
    def test_golden_ast(self) -> None:
        program = parse(GOLDEN)
        assert len(program.rules) == 1
        rule = program.rules[0]
        assert rule.name == "HighQualityCompounder"
        assert rule.metadata.version == "1.0"
        assert rule.metadata.priority == 100
        assert isinstance(rule.when, BinaryExpressionNode)
        assert [a.target for a in rule.actions] == [
            ActionTarget.PROBABILITY,
            ActionTarget.CONFIDENCE,
            ActionTarget.UTILITY,
            ActionTarget.RISK,
        ]
        assert rule.actions[3].assign == "-="
        assert [t.value for t in rule.tags] == ["Quality", "Growth"]
        assert rule.explain is not None
        assert rule.explain.text == "High quality compounder during expansion."

    def test_identical_source_identical_ast(self) -> None:
        assert parse(GOLDEN) == parse(GOLDEN)

    def test_or_not_and_parentheses_precedence(self) -> None:
        src = (
            "RULE R WHEN NOT (Market.Regime == Contraction) "
            'OR Company.ROIC > 20 AND Company.Beta < 1 THEN TAG "t"'
        )
        rule = parse(src).rules[0]
        assert isinstance(rule.when, BinaryExpressionNode) and rule.when.operator == "OR"
        assert isinstance(rule.when.left, UnaryExpressionNode)
        right = rule.when.right
        assert isinstance(right, BinaryExpressionNode) and right.operator == "AND"

    def test_symbolic_and_or(self) -> None:
        src = (
            "RULE R WHEN Company.ROIC > 1 && Company.Beta < 2 "
            '|| Company.PEPercentile < 50 THEN TAG "t"'
        )
        rule = parse(src).rules[0]
        assert isinstance(rule.when, BinaryExpressionNode) and rule.when.operator == "OR"

    def test_missing_when_is_dsl010(self) -> None:
        with pytest.raises(MissingWhenError):
            parse('RULE R THEN TAG "x"')

    def test_missing_then_is_dsl011(self) -> None:
        with pytest.raises(MissingThenError):
            parse('RULE R WHEN Company.ROIC > 1 EXPLAIN "x"')

    def test_empty_then_is_dsl012(self) -> None:
        with pytest.raises(InvalidActionError):
            parse('RULE R WHEN Company.ROIC > 1 THEN EXPLAIN "x"')

    def test_reserved_action_keywords_rejected(self) -> None:
        with pytest.raises(InvalidActionError):
            parse("RULE R WHEN Company.ROIC > 1 THEN STOP")

    def test_in_between_not_expressible(self) -> None:
        with pytest.raises(InvalidSyntaxError):
            parse('RULE R WHEN Sector.Name IN "tech" THEN TAG "t"')
        with pytest.raises(InvalidSyntaxError):
            parse('RULE R WHEN Company.ROIC BETWEEN 1 THEN TAG "t"')

    def test_priority_must_be_integer(self) -> None:
        with pytest.raises(InvalidSyntaxError):
            parse('RULE R VERSION "1" PRIORITY 1.5 WHEN Company.ROIC > 1 THEN TAG "t"')

    def test_negative_action_value_parses(self) -> None:
        rule = parse("RULE R WHEN Company.ROIC > 1 THEN UTILITY = -0.5").rules[0]
        assert rule.actions[0].value == Decimal("-0.5")

    def test_condition_literal_kinds(self) -> None:
        rule = parse(
            'RULE R WHEN Company.Ticker == "AAA" AND Market.Regime != Contraction THEN TAG "t"'
        ).rules[0]
        when = rule.when
        assert isinstance(when, BinaryExpressionNode)
        left, right = when.left, when.right
        assert isinstance(left, ConditionNode) and left.literal.kind is LiteralKind.STRING
        assert isinstance(right, ConditionNode) and right.literal.kind is LiteralKind.ENUM


class TestSemantics:
    def test_golden_is_valid(self) -> None:
        analyze(GOLDEN)

    def test_duplicate_rule_is_dsl008(self) -> None:
        src = GOLDEN + GOLDEN.replace("// RFC-0017 golden example", "")
        with pytest.raises(DuplicateRuleError):
            analyze(src)

    def test_unknown_root_is_dsl003(self) -> None:
        with pytest.raises(UnknownIdentifierError):
            analyze('RULE R WHEN Weather.Rain > 1 THEN TAG "t"')

    def test_unknown_property_is_dsl013(self) -> None:
        with pytest.raises(InvalidPropertyError):
            analyze('RULE R WHEN Company.Nonsense > 1 THEN TAG "t"')

    def test_bare_root_is_dsl013(self) -> None:
        with pytest.raises(InvalidPropertyError):
            analyze('RULE R WHEN Company == TRUE THEN TAG "t"')

    def test_function_in_condition_is_dsl004(self) -> None:
        with pytest.raises(UnknownFunctionError):
            analyze('RULE R WHEN ABS.Value > 1 THEN TAG "t"')

    def test_invalid_enum_is_dsl014(self) -> None:
        with pytest.raises(InvalidEnumError):
            analyze('RULE R WHEN Market.Regime == Moon THEN TAG "t"')

    def test_type_mismatches_are_dsl005(self) -> None:
        with pytest.raises(TypeMismatchError):
            analyze('RULE R WHEN Company.ROIC == "high" THEN TAG "t"')
        with pytest.raises(TypeMismatchError):
            analyze('RULE R WHEN Market.Regime > Expansion THEN TAG "t"')
        with pytest.raises(TypeMismatchError):
            analyze('RULE R WHEN Company.Ticker > "A" THEN TAG "t"')
        with pytest.raises(TypeMismatchError):
            analyze('RULE R WHEN Company.ROIC LIKE 5 THEN TAG "t"')

    def test_probability_range_is_dsl006(self) -> None:
        with pytest.raises(ProbabilityOutOfRangeError):
            analyze("RULE R WHEN Company.ROIC > 1 THEN PROBABILITY = 1.5")

    def test_confidence_range_is_dsl007(self) -> None:
        with pytest.raises(ConfidenceOutOfRangeError):
            analyze("RULE R WHEN Company.ROIC > 1 THEN CONFIDENCE += 2")

    def test_priority_positive_is_dsl015(self) -> None:
        with pytest.raises(SemanticValidationError):
            analyze('RULE R VERSION "1" PRIORITY 0 WHEN Company.ROIC > 1 THEN TAG "t"')

    def test_utility_and_risk_unbounded(self) -> None:
        analyze("RULE R WHEN Company.ROIC > 1 THEN UTILITY += 5 RISK -= 3")

    def test_boolean_property_rules(self) -> None:
        analyze('RULE R WHEN Behavior.BiasDetected == TRUE THEN TAG "t"')
        with pytest.raises(TypeMismatchError):
            analyze('RULE R WHEN Behavior.BiasDetected == 1 THEN TAG "t"')
        with pytest.raises(TypeMismatchError):
            analyze('RULE R WHEN Behavior.BiasDetected > TRUE THEN TAG "t"')

    def test_error_codes_embedded_in_messages(self) -> None:
        try:
            analyze('RULE R WHEN Market.Regime == Moon THEN TAG "t"')
        except DslError as e:
            assert "DSL014" in str(e)
        else:  # pragma: no cover
            raise AssertionError("expected DSL014")


class TestParserEdgeCases:
    def test_expected_rule_keyword(self) -> None:
        with pytest.raises(InvalidSyntaxError):
            parse('WHEN Company.ROIC > 1 THEN TAG "t"')

    def test_rule_name_cannot_be_dotted_or_missing(self) -> None:
        with pytest.raises(InvalidSyntaxError):
            parse('RULE Company.Bad WHEN Company.ROIC > 1 THEN TAG "t"')
        with pytest.raises(InvalidSyntaxError):
            parse('RULE 42 WHEN Company.ROIC > 1 THEN TAG "t"')

    def test_version_requires_string(self) -> None:
        with pytest.raises(InvalidSyntaxError):
            parse('RULE R VERSION 1 WHEN Company.ROIC > 1 THEN TAG "t"')

    def test_missing_closing_paren(self) -> None:
        with pytest.raises(InvalidSyntaxError):
            parse('RULE R WHEN (Company.ROIC > 1 THEN TAG "t"')

    def test_condition_requires_identifier_and_literal(self) -> None:
        with pytest.raises(InvalidSyntaxError):
            parse('RULE R WHEN 5 > 1 THEN TAG "t"')
        with pytest.raises(InvalidSyntaxError):
            parse('RULE R WHEN Company.ROIC > THEN TAG "t"')

    def test_action_requires_assign_and_number(self) -> None:
        with pytest.raises(InvalidActionError):
            parse("RULE R WHEN Company.ROIC > 1 THEN PROBABILITY 0.5")
        with pytest.raises(InvalidActionError):
            parse('RULE R WHEN Company.ROIC > 1 THEN PROBABILITY = "x"')

    def test_tag_requires_string(self) -> None:
        with pytest.raises(InvalidSyntaxError):
            parse("RULE R WHEN Company.ROIC > 1 THEN TAG 5")

    def test_multiple_rules_parse(self) -> None:
        two = parse(
            'RULE A WHEN Company.ROIC > 1 THEN TAG "a" RULE B WHEN Company.Beta < 1 THEN TAG "b"'
        )
        assert [r.name for r in two.rules] == ["A", "B"]


class TestSchemaRegistry:
    def test_with_features_registers_numeric_properties(self) -> None:
        from dsl.domain.schema import with_features

        schema = with_features(("quality.roe",))
        analyzer = SemanticAnalyzer(schema=schema)
        analyzer.analyze(parse('RULE R WHEN Feature.quality.roe > 0.15 THEN TAG "q"'))
        with pytest.raises(InvalidPropertyError):
            analyzer.analyze(parse('RULE R WHEN Feature.unknown > 1 THEN TAG "q"'))


class TestRemainingBranches:
    def test_not_in_rejected(self) -> None:
        with pytest.raises(InvalidSyntaxError):
            parse('RULE R WHEN Sector.Name NOT IN "tech" THEN TAG "t"')

    def test_null_literal_parses_and_mismatches(self) -> None:
        rule = parse('RULE R WHEN Company.ROIC != NULL THEN TAG "t"').rules[0]
        condition = rule.when
        assert isinstance(condition, ConditionNode)
        assert condition.literal.kind is LiteralKind.NULL
        with pytest.raises(TypeMismatchError):
            analyze('RULE R WHEN Company.ROIC != NULL THEN TAG "t"')

    def test_not_expression_semantics_checked(self) -> None:
        with pytest.raises(InvalidEnumError):
            analyze('RULE R WHEN NOT Market.Regime == Moon THEN TAG "t"')

    def test_enum_property_requires_enum_literal(self) -> None:
        with pytest.raises(TypeMismatchError):
            analyze('RULE R WHEN Market.Regime == "Expansion" THEN TAG "t"')

    def test_string_like_is_valid(self) -> None:
        analyze('RULE R WHEN Company.Ticker LIKE "A%" THEN TAG "t"')
