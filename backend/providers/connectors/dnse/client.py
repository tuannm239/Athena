"""DNSE HTTP client — the only network seam for the DNSE connector.

`DnseTransport` is the injectable seam (production: `HttpxDnseTransport`), so
the adapter and its tests never touch the network. Requests are signed per call
(HMAC-SHA256; `DnseSigner`), every HTTP failure is translated to a typed
`DnseError` (spec §7), transient failures (429/5xx/timeout/network) are retried
with exponential backoff (spec §9), and secrets are never logged (spec §8).

Market data: ``GET {base}/price/ohlc?type={STOCK|INDEX}&symbol&resolution&from&to``.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Callable, Mapping, Protocol

from providers.connectors.dnse.auth import DnseSigner
from providers.connectors.dnse.config import DnseConfig, redact_headers
from providers.connectors.dnse.exceptions import (
    TRANSIENT_ERRORS,
    DnseAuthError,
    DnseError,
    DnseRateLimitError,
    DnseUnavailableError,
)

_LOG = logging.getLogger("athena.provider.dnse")

# DNSE OpenAPI OHLC route (bar_type is the `type` query param: STOCK / INDEX).
_OHLC_PATH = "/price/ohlc"

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
    """The only network seam. Returns a JSON object or raises a typed `DnseError`."""

    def get_json(
        self, url: str, params: Mapping[str, str], headers: Mapping[str, str], timeout: float
    ) -> Json: ...


class HttpxDnseTransport:
    """Production transport (httpx). Maps every transport/HTTP error to `DnseError`."""

    def get_json(
        self, url: str, params: Mapping[str, str], headers: Mapping[str, str], timeout: float
    ) -> Json:
        import httpx

        try:
            response = httpx.get(url, params=dict(params), headers=dict(headers), timeout=timeout)
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
    """Market-data client over the DNSE OpenAPI OHLC route (stocks + indices).

    Retries only transient failures with exponential backoff, signs each request
    with HMAC-SHA256, and logs request/latency/retries with secrets redacted.
    """

    config: DnseConfig
    transport: DnseTransport
    signer: DnseSigner
    sleeper: Callable[[float], None] = time.sleep
    clock: Callable[[], float] = time.monotonic
    logger: logging.Logger = _LOG

    @classmethod
    def from_env(cls, transport: DnseTransport | None = None) -> DnseMarketClient:
        config = DnseConfig.from_env()
        return cls(
            config=config,
            transport=transport or HttpxDnseTransport(),
            signer=DnseSigner(config),
        )

    def ohlc(self, symbol: str, frm: int, to: int, resolution: str, *, is_index: bool) -> Json:
        params = {
            "type": "INDEX" if is_index else "STOCK",
            "symbol": symbol,
            "resolution": resolution,
            "from": str(frm),
            "to": str(to),
        }
        return self._get(_OHLC_PATH, params, symbol)

    def _get(self, path: str, params: Mapping[str, str], label: str) -> Json:
        url = f"{self.config.base_url}{path}"
        headers = self.signer.headers("GET", path)
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
