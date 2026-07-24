"""DNSE authentication — JWT bearer token, cached until near expiry.

DNSE's OpenAPI issues a JWT from a username/password login; the connector
reads the credential pair from the environment (`DNSE_API_KEY` /
`DNSE_API_SECRET`) via `DnseConfig` and never hardcodes or logs them. When no
credentials are configured the public chart (market-data) routes are used
without a token, so `token()` returns ``None``.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Callable

from providers.connectors.dnse.config import DnseConfig
from providers.connectors.dnse.exceptions import DnseAuthError

if TYPE_CHECKING:  # avoid an import cycle (client imports auth)
    from providers.connectors.dnse.client import DnseTransport

# DNSE login route (username/password -> JWT). Overridable only via base_url.
_LOGIN_PATH = "/auth-service/login"


class DnseAuthenticator:
    """Obtains and caches a DNSE JWT; returns ``None`` when no credentials exist."""

    def __init__(
        self,
        config: DnseConfig,
        transport: "DnseTransport",
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._config = config
        self._transport = transport
        self._clock = clock
        self._token: str | None = None
        self._expires_at = 0.0

    def token(self) -> str | None:
        """A valid bearer token, refreshing when missing/expired; ``None`` if unauthenticated."""
        if not self._config.has_credentials:
            return None
        if self._token is not None and self._clock() < self._expires_at:
            return self._token
        self._login()
        return self._token

    def _login(self) -> None:
        url = f"{self._config.base_url}{_LOGIN_PATH}"
        body = {"username": self._config.api_key, "password": self._config.api_secret}
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        data = self._transport.post_json(url, body, headers, self._config.timeout)
        token = data.get("token") or data.get("access_token")
        if not token or not isinstance(token, str):
            raise DnseAuthError("DNSE login returned no token")
        self._token = token
        # Refresh a minute before the configured TTL to avoid edge-of-expiry use.
        self._expires_at = self._clock() + max(self._config.token_ttl_seconds - 60.0, 60.0)
