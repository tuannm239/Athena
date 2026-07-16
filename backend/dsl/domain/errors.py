"""Decision DSL error codes (RFC-0017 §Error Codes)."""

from __future__ import annotations

from shared_kernel.exceptions import DomainError


class DslError(DomainError):
    """Base compiler error; `code` carries the RFC-0017 error code."""

    code = "DSL000"

    def __init__(self, message: str, *, line: int = 0, column: int = 0) -> None:
        super().__init__(f"{self.code} at {line}:{column}: {message}")
        self.line = line
        self.column = column


class InvalidTokenError(DslError):
    code = "DSL001"


class InvalidSyntaxError(DslError):
    code = "DSL002"


class UnknownIdentifierError(DslError):
    code = "DSL003"


class UnknownFunctionError(DslError):
    code = "DSL004"


class TypeMismatchError(DslError):
    code = "DSL005"


class ProbabilityOutOfRangeError(DslError):
    code = "DSL006"


class ConfidenceOutOfRangeError(DslError):
    code = "DSL007"


class DuplicateRuleError(DslError):
    code = "DSL008"


class CircularDependencyError(DslError):
    code = "DSL009"


class MissingWhenError(DslError):
    code = "DSL010"


class MissingThenError(DslError):
    code = "DSL011"


class InvalidActionError(DslError):
    code = "DSL012"


class InvalidPropertyError(DslError):
    code = "DSL013"


class InvalidEnumError(DslError):
    code = "DSL014"


class SemanticValidationError(DslError):
    code = "DSL015"
