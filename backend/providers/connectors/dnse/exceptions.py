"""DNSE provider exceptions — all translated to Athena `DomainError`s.

Never let a DNSE SDK/HTTP error (httpx status errors, JSON decode errors,
transport failures) escape the Infrastructure layer: the client translates
each into one of these, so business layers stay provider-agnostic (spec §7).
"""

from __future__ import annotations

from shared_kernel.exceptions import DomainError


class DnseError(DomainError):
    """Base for any DNSE provider failure (already translated; no httpx leaks)."""


class DnseAuthError(DnseError):
    """Authentication / authorization failed (HTTP 401/403). Not retryable."""


class DnseRateLimitError(DnseError):
    """Rate limited by DNSE (HTTP 429). Transient — safe to retry with backoff."""


class DnseUnavailableError(DnseError):
    """Upstream unavailable or timed out (HTTP 5xx / network / timeout). Transient."""


# The subset of failures that are safe to retry (spec §9: transient only).
TRANSIENT_ERRORS: tuple[type[DnseError], ...] = (DnseRateLimitError, DnseUnavailableError)
