"""Probability Engine error codes (RFC-0018 §10)."""

from __future__ import annotations

from shared_kernel.exceptions import DomainError


class ProbabilityError(DomainError):
    """Base class; `code` carries the RFC-0018 §10 error code."""

    code = "PE000"


class InvalidPriorError(ProbabilityError):
    code = "PE001"


class InvalidEvidenceError(ProbabilityError):
    code = "PE002"


class MissingHypothesisError(ProbabilityError):
    code = "PE003"


class CalibrationError(ProbabilityError):
    code = "PE005"
