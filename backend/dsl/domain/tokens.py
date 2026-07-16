"""Token model for the Decision DSL lexer (RFC-0017 §Lexical Rules)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

KEYWORDS = frozenset(
    {
        "RULE",
        "WHEN",
        "THEN",
        "VERSION",
        "PRIORITY",
        "EXPLAIN",
        "TAG",
        "AND",
        "OR",
        "NOT",
        "TRUE",
        "FALSE",
        "NULL",
        "PROBABILITY",
        "CONFIDENCE",
        "UTILITY",
        "RISK",
        "RETURN",
        "STOP",
        "IGNORE",
        "WATCH",
        "IN",
        "BETWEEN",
        "LIKE",
    }
)

BUILTIN_FUNCTIONS = frozenset(
    {
        "ABS",
        "MIN",
        "MAX",
        "AVG",
        "COUNT",
        "SUM",
        "ROUND",
        "CEIL",
        "FLOOR",
        "EXISTS",
        "ISNULL",
        "TODAY",
        "NOW",
        "YEAR",
        "MONTH",
        "DAY",
    }
)


class TokenType(StrEnum):
    KEYWORD = "KEYWORD"
    IDENTIFIER = "IDENTIFIER"
    NUMBER = "NUMBER"
    STRING = "STRING"
    OPERATOR = "OPERATOR"
    ASSIGN = "ASSIGN"
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    EOF = "EOF"


@dataclass(frozen=True, slots=True)
class Token:
    type: TokenType
    value: str
    line: int
    column: int
