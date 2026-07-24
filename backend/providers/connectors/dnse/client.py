"""DNSE HTTP client — the only network seam for the DNSE connector.

`DnseTransport` is the injectable seam (production: `HttpxDnseTransport`), so
the adapter and its tests never touch the network. Every HTTP failure is
translated to a typed `DnseError` (spec §7); transient failures (429/5xx/
timeout/network) are retried with exponential backoff (spec §9); secrets are
never logged (spec §8).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Callable, Mapping, Protocol

from providers.connectors.dnse.auth import DnseAuthenticator
from providers.connectors.dnse.config import DnseConfig, redact_headers
from providers.connectors.dnse.exceptions import (
    TRANSIENT_ERRORS,
    DnseAuthError,
    DnseError,
    DnseRateLimitError,
    DnseUnavailableError,
)

_LOG = logging.getLogger("athena.provider.dnse")

# DNSE chart (TradingView-UDF) OHLC routes — stocks vs indices.
_OHLC_STOCK_PATH = "/chart-api/v2/ohlcs/stock"
_OHLC_INDEX_PATH = "/chart-api/v2/ohlcs/index"

Json = Mapping[str, object]


def raise_for_status(status: int, detail: str) -> None:
    """Translate an HTTP status into a typed `DnseError` (transient vs not)."""
    if status in (401, 403):
        raise DnseAuthError(f"DNSE auth failed (HTTP {status})")
    if status == 429:
        raise DnseRateLimitError("DNSE rate limit exceeded (HTTP 429)")
    if status in (500, 502, 503, 504):
        raise DnseUnavailableError(f"DNSE unavailable (HTTP {status})")
    if status >= 400:
        raise DnseError(f"DNSE request failed (HTTP {status}): {detail[:200]}")


class DnseTransport(Protocol):
    """The only network seam. Methods return a JSON object or raise `DnseError`."""

    def get_json(
        self, url: str, params: Mapping[str, str], headers: Mapping[str, str], timeout: float
    ) -> Json: ...

    def post_json(
        self, url: str, body: Mapping[str, object], headers: Mapping[str, str], timeout: float
    ) -> Json: ...


class HttpxDnseTransport:
    """Production transport (httpx). Maps every transport/HTTP error to `DnseError`."""

    def get_json(
        self, url: str, params: Mapping[str, str], headers: Mapping[str, str], timeout: float
    ) -> Json:
        return self._request("GET", url, headers, timeout, params=params)

    def post_json(
        self, url: str, body: Mapping[str, object], headers: Mapping[str, str], timeout: float
    ) -> Json:
        return self._request("POST", url, headers, timeout, json=body)

    def _request(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        timeout: float,
        *,
        params: Mapping[str, str] | None = None,
        json: Mapping[str, object] | None = None,
    ) -> Json:
        import httpx

        try:
            response = httpx.request(
                method, url, params=params, json=json, headers=dict(headers), timeout=timeout
            )
        except httpx.TimeoutException as error:
            raise DnseUnavailableError(f"DNSE timeout for {url}") from error
        except httpx.HTTPError as error:  # transport/connection error
            raise DnseUnavailableError(f"DNSE transport error for {url}") from error
        raise_for_status(response.status_code, response.text)
        try:
            data = response.json()
        except ValueError as error:
            raise DnseError(f"DNSE returned a non-JSON body for {url}") from error
        if not isinstance(data, dict):
            raise DnseError(f"DNSE returned a non-object body for {url}")
        return data


@dataclass
class DnseMarketClient:
    """Market-data client over the DNSE chart API (OHLC for stocks + indices).

    Retries only transient failures with exponential backoff, attaches a bearer
    token when credentials are configured, and logs request/latency/retries with
    secrets redacted.
    """

    config: DnseConfig
    transport: DnseTransport
    auth: DnseAuthenticator
    sleeper: Callable[[float], None] = time.sleep
    clock: Callable[[], float] = time.monotonic
    logger: logging.Logger = _LOG

    @classmethod
    def from_env(cls, transport: DnseTransport | None = None) -> DnseMarketClient:
        config = DnseConfig.from_env()
        chosen = transport or HttpxDnseTransport()
        return cls(config=config, transport=chosen, auth=DnseAuthenticator(config, chosen))

    def ohlc(self, symbol: str, frm: int, to: int, resolution: str, *, is_index: bool) -> Json:
        path = _OHLC_INDEX_PATH if is_index else _OHLC_STOCK_PATH
        url = f"{self.config.base_url}{path}"
        params = {"symbol": symbol, "resolution": resolution, "from": str(frm), "to": str(to)}
        return self._get(url, params, symbol)

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "User-Agent": "AthenaBot/1.0"}
        token = self.auth.token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _get(self, url: str, params: Mapping[str, str], label: str) -> Json:
        headers = self._headers()
        last: DnseError | None = None
        for attempt in range(1, self.config.max_attempts + 1):
            started = self.clock()
            try:
                result = self.transport.get_json(url, params, headers, self.config.timeout)
                self.logger.info(
                    "dnse.request ok provider=dnse symbol=%s attempt=%d %.0fms url=%s headers=%s",
                    label,
                    attempt,
                    (self.clock() - started) * 1000,
                    url,
                    redact_headers(headers),
                )
                return result
            except TRANSIENT_ERRORS as error:
                last = error
                rate_limited = isinstance(error, DnseRateLimitError)
                self.logger.warning(
                    "dnse.request transient provider=dnse symbol=%s try=%d/%d rate_limited=%s: %s",
                    label,
                    attempt,
                    self.config.max_attempts,
                    rate_limited,
                    error,
                )
                if attempt < self.config.max_attempts:
                    self.sleeper(self.config.base_delay_seconds * (2 ** (attempt - 1)))
            except DnseError as error:  # non-transient (auth / 4xx) — do not retry
                self.logger.warning("dnse.request failed provider=dnse symbol=%s: %s", label, error)
                raise
        assert last is not None
        raise last
