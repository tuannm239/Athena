"""DNSE request signing — HMAC-SHA256 HTTP-Signatures (spec §2).

DNSE OpenAPI authenticates each request by signing it with the API secret
(HMAC-SHA256) rather than issuing a session token. `DnseSigner` builds the
per-request auth headers from the credential pair read from the environment via
`DnseConfig`; the secret is used only as the HMAC key and is never logged.

String-to-sign (HTTP-Signatures, draft-cavage):

    (request-target): {method} {path}
    date: {http-date}

Signature header:

    X-Signature: Signature keyId="{api_key}",algorithm="hmac-sha256",
                 headers="(request-target) date",signature="{base64(hmac)}"
"""

from __future__ import annotations

import base64
import hashlib
import hmac
from email.utils import formatdate
from typing import Callable

from providers.connectors.dnse.config import DnseConfig

_ALGORITHM = "hmac-sha256"
_SIGNED_HEADERS = "(request-target) date"


def _now_http_date() -> str:
    # RFC 1123 date in GMT, e.g. "Mon, 21 Jul 2026 05:00:00 GMT".
    return formatdate(timeval=None, localtime=False, usegmt=True)


class DnseSigner:
    """Produces the signed request headers for a DNSE OpenAPI call."""

    def __init__(
        self, config: DnseConfig, date_factory: Callable[[], str] = _now_http_date
    ) -> None:
        self._config = config
        self._date_factory = date_factory

    def headers(self, method: str, path: str) -> dict[str, str]:
        """Auth headers for ``method``/``path`` (empty when no credentials)."""
        headers = {"Accept": "application/json", "version": self._config.api_version}
        if not self._config.has_credentials:
            return headers  # public/unauthenticated call — no signature
        date = self._date_factory()
        string_to_sign = f"(request-target): {method.lower()} {path}\ndate: {date}"
        digest = hmac.new(
            self._config.api_secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        signature = base64.b64encode(digest).decode("ascii")
        headers["Date"] = date
        headers["x-api-key"] = self._config.api_key
        headers["X-Signature"] = (
            f'Signature keyId="{self._config.api_key}",algorithm="{_ALGORITHM}",'
            f'headers="{_SIGNED_HEADERS}",signature="{signature}"'
        )
        return headers
