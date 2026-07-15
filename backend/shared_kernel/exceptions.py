"""Root of the domain exception hierarchy.

Every bounded context derives its errors from DomainError so the
application layer can map domain failures to API error codes uniformly
(SPEC-08, Error Codes: 422 BusinessRuleViolation).

DomainError extends ValueError to stay compatible with value-object
validation raising conventions.
"""

from __future__ import annotations


class DomainError(ValueError):
    """A violated business rule or domain invariant."""
