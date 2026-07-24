"""DNSE connector configuration + secret redaction (spec §2, §8).

Credentials are read only from environment variables and never hardcoded.
`redact`/`redact_headers` keep secrets (API key/secret, tokens, signatures,
Authorization headers) out of every log line.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

# DNSE OpenAPI base (overridable via DNSE_BASE_URL). Requests are signed per
# call with HMAC-SHA256 (HTTP-Signatures scheme) using the API key/secret.
DEFAULT_BASE_URL = "https://openapi.dnse.com.vn"
# API version sent in the `version` header (DNSE_API_VERSION overrides).
DEFAULT_API_VERSION = "2026-05-07"

# Header/field names whose values must never be logged.
_SECRET_NAMES = frozenset(
    {
        "authorization",
        "x-signature",
        "x-api-key",
        "token",
        "access_token",
        "api_key",
        "api_secret",
        "password",
        "signature",
    }
)
_REDACTED = "***redacted***"


@dataclass(frozen=True, slots=True)
class DnseConfig:
    """Immutable DNSE connector settings (from env; no secrets in logs)."""

    base_url: str = DEFAULT_BASE_URL
    api_key: str = ""
    api_secret: str = ""
    api_version: str = DEFAULT_API_VERSION
    timeout: float = 10.0
    max_attempts: int = 4
    base_delay_seconds: float = 0.5

    @property
    def has_credentials(self) -> bool:
        """True when both credentials are present (requests are otherwise unsigned)."""
        return bool(self.api_key and self.api_secret)

    @classmethod
    def from_env(cls) -> DnseConfig:
        return cls(
            base_url=(os.environ.get("DNSE_BASE_URL") or DEFAULT_BASE_URL).rstrip("/"),
            api_key=os.environ.get("DNSE_API_KEY", ""),
            api_secret=os.environ.get("DNSE_API_SECRET", ""),
            api_version=os.environ.get("DNSE_API_VERSION") or DEFAULT_API_VERSION,
            timeout=float(os.environ.get("DNSE_TIMEOUT_SECONDS", "10")),
            max_attempts=int(os.environ.get("DNSE_MAX_ATTEMPTS", "4")),
        )


def redact_headers(headers: Mapping[str, str]) -> dict[str, str]:
    """Copy of `headers` with secret values masked (safe to log)."""
    return {k: (_REDACTED if k.lower() in _SECRET_NAMES else v) for k, v in headers.items()}
