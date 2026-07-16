"""Decision DSL recursive-descent parser (RFC-0017 §Grammar).

Expression precedence: OR < AND < NOT < parentheses. The v2 grammar's
`condition` takes exactly one literal, so IN / NOT IN / BETWEEN are not
expressible and are reported as DSL002 until a grammar revision adds
list/range literals.
"""

from __future__ import annotations

from decimal import Decimal

from dsl.domain.ast import (
    ActionNode,
    ActionTarget,
    BinaryExpressionNode,
    ConditionNode,
    ExplainNode,
    ExpressionNode,
    LiteralKind,
    LiteralNode,
    MetadataNode,
    ProgramNode,
    RuleNode,
    SourceLocation,
    TagNode,
    UnaryExpressionNode,
)
from dsl.domain.errors import (
    InvalidActionError,
    InvalidSyntaxError,
    MissingThenError,
    MissingWhenError,
)
from dsl.domain.lexer import tokenize
from dsl.domain.tokens import Token, TokenType

_CONDITION_OPERATORS = frozenset({"==", "!=", ">", ">=", "<", "<=", "LIKE"})
_UNSUPPORTED_OPERATORS = frozenset({"IN", "BETWEEN"})
_ACTION_TARGETS = frozenset(t.value for t in ActionTarget)


class _Parser:
    def __init__(self, tokens: tuple[Token, ...]) -> None:
        self._tokens = tokens
        self._pos = 0

    # -- token plumbing ------------------------------------------------------

    def _peek(self) -> Token:
        return self._tokens[self._pos]

    def _next(self) -> Token:
        token = self._tokens[self._pos]
        self._pos += 1
        return token

    def _at_keyword(self, *values: str) -> bool:
        token = self._peek()
        return token.type is TokenType.KEYWORD and token.value in values

    def _expect_keyword(self, value: str) -> Token:
        token = self._next()
        if token.type is not TokenType.KEYWORD or token.value != value:
            raise InvalidSyntaxError(
                f"expected {value}, got {token.value!r}", line=token.line, column=token.column
            )
        return token

    @staticmethod
    def _loc(token: Token) -> SourceLocation:
        return SourceLocation(line=token.line, column=token.column)

    # -- grammar -------------------------------------------------------------

    def parse_program(self) -> ProgramNode:
        rules: list[RuleNode] = []
        while self._peek().type is not TokenType.EOF:
            rules.append(self._parse_rule())
        return ProgramNode(rules=tuple(rules))

    def _parse_rule(self) -> RuleNode:
        start = self._expect_keyword("RULE")
        name_token = self._next()
        if name_token.type is not TokenType.IDENTIFIER or "." in name_token.value:
            raise InvalidSyntaxError(
                f"expected rule name, got {name_token.value!r}",
                line=name_token.line,
                column=name_token.column,
            )
        metadata = self._parse_metadata()

        if not self._at_keyword("WHEN"):
            token = self._peek()
            raise MissingWhenError(
                f"rule {name_token.value} requires a WHEN block",
                line=token.line,
                column=token.column,
            )
        self._next()
        when = self._parse_expression()

        if not self._at_keyword("THEN"):
            token = self._peek()
            raise MissingThenError(
                f"rule {name_token.value} requires a THEN block",
                line=token.line,
                column=token.column,
            )
        self._next()
        actions, tags = self._parse_actions(name_token.value)

        explain: ExplainNode | None = None
        if self._at_keyword("EXPLAIN"):
            keyword = self._next()
            text = self._expect_string("EXPLAIN")
            explain = ExplainNode(text=text, location=self._loc(keyword))

        return RuleNode(
            name=name_token.value,
            metadata=metadata,
            when=when,
            actions=actions,
            tags=tags,
            explain=explain,
            location=self._loc(start),
        )

    def _parse_metadata(self) -> MetadataNode:
        token = self._peek()
        location = self._loc(token)
        version: str | None = None
        priority: int | None = None
        if self._at_keyword("VERSION"):
            self._next()
            version = self._expect_string("VERSION")
        if self._at_keyword("PRIORITY"):
            self._next()
            number = self._next()
            if number.type is not TokenType.NUMBER or "." in number.value:
                raise InvalidSyntaxError(
                    "PRIORITY requires an integer", line=number.line, column=number.column
                )
            priority = int(number.value)
        return MetadataNode(version=version, priority=priority, location=location)

    def _expect_string(self, context: str) -> str:
        token = self._next()
        if token.type is not TokenType.STRING:
            raise InvalidSyntaxError(
                f"{context} requires a string literal", line=token.line, column=token.column
            )
        return token.value

    # expression ::= or_expr ; or_expr ::= and_expr (OR and_expr)* ;
    # and_expr ::= unary (AND unary)* ; unary ::= NOT unary | primary
    def _parse_expression(self) -> ExpressionNode:
        return self._parse_or()

    def _parse_or(self) -> ExpressionNode:
        left = self._parse_and()
        while self._at_keyword("OR") or self._peek().value == "||":
            op_token = self._next()
            right = self._parse_and()
            left = BinaryExpressionNode(
                operator="OR", left=left, right=right, location=self._loc(op_token)
            )
        return left

    def _parse_and(self) -> ExpressionNode:
        left = self._parse_unary()
        while self._at_keyword("AND") or self._peek().value == "&&":
            op_token = self._next()
            right = self._parse_unary()
            left = BinaryExpressionNode(
                operator="AND", left=left, right=right, location=self._loc(op_token)
            )
        return left

    def _parse_unary(self) -> ExpressionNode:
        token = self._peek()
        if self._at_keyword("NOT") or token.value == "!":
            op_token = self._next()
            return UnaryExpressionNode(
                operator="NOT", operand=self._parse_unary(), location=self._loc(op_token)
            )
        if token.type is TokenType.LPAREN:
            self._next()
            inner = self._parse_expression()
            closing = self._next()
            if closing.type is not TokenType.RPAREN:
                raise InvalidSyntaxError("expected ')'", line=closing.line, column=closing.column)
            return inner
        return self._parse_condition()

    def _parse_condition(self) -> ConditionNode:
        ident = self._next()
        if ident.type is not TokenType.IDENTIFIER:
            raise InvalidSyntaxError(
                f"expected identifier, got {ident.value!r}", line=ident.line, column=ident.column
            )
        op = self._next()
        operator = op.value
        if operator == "NOT" and self._at_keyword("IN"):
            self._next()
            operator = "NOT IN"
        if operator in _UNSUPPORTED_OPERATORS or operator == "NOT IN":
            raise InvalidSyntaxError(
                f"operator {operator} needs list/range literals, "
                "which the RFC-0017 v2 grammar does not define",
                line=op.line,
                column=op.column,
            )
        if operator not in _CONDITION_OPERATORS:
            raise InvalidSyntaxError(
                f"invalid condition operator {operator!r}", line=op.line, column=op.column
            )
        return ConditionNode(
            identifier=ident.value,
            operator=operator,
            literal=self._parse_literal(),
            location=self._loc(ident),
        )

    def _parse_literal(self) -> LiteralNode:
        token = self._next()
        location = self._loc(token)
        if token.type is TokenType.NUMBER:
            return LiteralNode(LiteralKind.NUMBER, Decimal(token.value), location)
        if token.type is TokenType.STRING:
            return LiteralNode(LiteralKind.STRING, token.value, location)
        if token.type is TokenType.KEYWORD and token.value in ("TRUE", "FALSE"):
            return LiteralNode(LiteralKind.BOOLEAN, token.value == "TRUE", location)
        if token.type is TokenType.KEYWORD and token.value == "NULL":
            return LiteralNode(LiteralKind.NULL, None, location)
        if token.type is TokenType.IDENTIFIER and "." not in token.value:
            return LiteralNode(LiteralKind.ENUM, token.value, location)
        raise InvalidSyntaxError(
            f"expected literal, got {token.value!r}", line=token.line, column=token.column
        )

    def _parse_actions(self, rule_name: str) -> tuple[tuple[ActionNode, ...], tuple[TagNode, ...]]:
        actions: list[ActionNode] = []
        tags: list[TagNode] = []
        while True:
            token = self._peek()
            if token.type is TokenType.KEYWORD and token.value in _ACTION_TARGETS:
                self._next()
                assign = self._next()
                if assign.type is not TokenType.ASSIGN:
                    raise InvalidActionError(
                        f"{token.value} requires =, += or -=",
                        line=assign.line,
                        column=assign.column,
                    )
                negative = False
                number = self._next()
                if number.type is TokenType.OPERATOR and number.value == "-":
                    negative = True
                    number = self._next()
                if number.type is not TokenType.NUMBER:
                    raise InvalidActionError(
                        f"{token.value} requires a number",
                        line=number.line,
                        column=number.column,
                    )
                value = Decimal(number.value)
                actions.append(
                    ActionNode(
                        target=ActionTarget(token.value),
                        assign=assign.value,
                        value=-value if negative else value,
                        location=self._loc(token),
                    )
                )
                continue
            if token.type is TokenType.KEYWORD and token.value == "TAG":
                keyword = self._next()
                tags.append(TagNode(value=self._expect_string("TAG"), location=self._loc(keyword)))
                continue
            if token.type is TokenType.KEYWORD and token.value in (
                "RETURN",
                "STOP",
                "IGNORE",
                "WATCH",
            ):
                raise InvalidActionError(
                    f"{token.value} is reserved but not a valid THEN action in RFC-0017 v2",
                    line=token.line,
                    column=token.column,
                )
            break
        if not actions and not tags:
            token = self._peek()
            raise InvalidActionError(
                f"rule {rule_name}: THEN requires at least one action",
                line=token.line,
                column=token.column,
            )
        return tuple(actions), tuple(tags)


def parse(source: str) -> ProgramNode:
    """Deterministic parse: identical source ⇒ identical AST."""
    return _Parser(tokenize(source)).parse_program()
