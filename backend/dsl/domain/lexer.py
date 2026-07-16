"""Decision DSL lexer (RFC-0017): deterministic tokenizer.

Case sensitive; `//` and `/* */` comments; dotted identifiers
(`Company.ROIC`) are a single IDENTIFIER token; source locations are
preserved on every token (DSL001 on lexical errors).
"""

from __future__ import annotations

from dsl.domain.errors import InvalidTokenError
from dsl.domain.tokens import KEYWORDS, Token, TokenType

_MULTI_OPERATORS = ("==", "!=", ">=", "<=", "&&", "||")
_MULTI_ASSIGN = ("+=", "-=")
_SINGLE_OPERATORS = set(">|<|+|-|*|/|%|!".split("|"))


def tokenize(source: str) -> tuple[Token, ...]:
    """Produce the token stream; identical source ⇒ identical tokens."""
    tokens: list[Token] = []
    pos = 0
    line = 1
    column = 1
    length = len(source)

    def advance(count: int) -> None:
        nonlocal pos, line, column
        for _ in range(count):
            if pos < length and source[pos] == "\n":
                line += 1
                column = 1
            else:
                column += 1
            pos += 1

    while pos < length:
        char = source[pos]

        if char in " \t\r\n":
            advance(1)
            continue

        if source.startswith("//", pos):
            while pos < length and source[pos] != "\n":
                advance(1)
            continue

        if source.startswith("/*", pos):
            start_line, start_col = line, column
            advance(2)
            while pos < length and not source.startswith("*/", pos):
                advance(1)
            if pos >= length:
                raise InvalidTokenError(
                    "unterminated block comment", line=start_line, column=start_col
                )
            advance(2)
            continue

        if char == '"':
            start_line, start_col = line, column
            advance(1)
            begin = pos
            while pos < length and source[pos] not in ('"', "\n"):
                advance(1)
            if pos >= length or source[pos] != '"':
                raise InvalidTokenError(
                    "unterminated string literal", line=start_line, column=start_col
                )
            value = source[begin:pos]
            advance(1)
            tokens.append(Token(TokenType.STRING, value, start_line, start_col))
            continue

        if char.isdigit():
            start_line, start_col = line, column
            begin = pos
            while pos < length and source[pos].isdigit():
                advance(1)
            if pos < length and source[pos] == ".":
                if pos + 1 >= length or not source[pos + 1].isdigit():
                    raise InvalidTokenError("malformed number", line=start_line, column=start_col)
                advance(1)
                while pos < length and source[pos].isdigit():
                    advance(1)
            tokens.append(Token(TokenType.NUMBER, source[begin:pos], start_line, start_col))
            continue

        if char.isalpha() or char == "_":
            start_line, start_col = line, column
            begin = pos
            while pos < length and (source[pos].isalnum() or source[pos] in "_."):
                advance(1)
            value = source[begin:pos]
            if value.endswith(".") or ".." in value:
                raise InvalidTokenError(
                    f"malformed identifier {value!r}", line=start_line, column=start_col
                )
            token_type = TokenType.KEYWORD if value in KEYWORDS else TokenType.IDENTIFIER
            tokens.append(Token(token_type, value, start_line, start_col))
            continue

        matched = False
        for op in _MULTI_OPERATORS:
            if source.startswith(op, pos):
                tokens.append(Token(TokenType.OPERATOR, op, line, column))
                advance(2)
                matched = True
                break
        if matched:
            continue
        for op in _MULTI_ASSIGN:
            if source.startswith(op, pos):
                tokens.append(Token(TokenType.ASSIGN, op, line, column))
                advance(2)
                matched = True
                break
        if matched:
            continue

        if char == "=":
            tokens.append(Token(TokenType.ASSIGN, "=", line, column))
            advance(1)
            continue
        if char == "(":
            tokens.append(Token(TokenType.LPAREN, "(", line, column))
            advance(1)
            continue
        if char == ")":
            tokens.append(Token(TokenType.RPAREN, ")", line, column))
            advance(1)
            continue
        if char in _SINGLE_OPERATORS:
            tokens.append(Token(TokenType.OPERATOR, char, line, column))
            advance(1)
            continue

        raise InvalidTokenError(f"unexpected character {char!r}", line=line, column=column)

    tokens.append(Token(TokenType.EOF, "", line, column))
    return tuple(tokens)
