"""Alpha Vantage production data-provider adapter (Phase 5, Workstream 5).

Closes gap R1: the first *production* connector to a real, documented
market-data API. It is an adapter only — it maps vendor JSON to the
Athena domain DTOs (`providers.sdk.models`) and implements the SDK ports
(`PriceProvider`, `FXProvider`). It contains NO business logic.

Design:
  - HTTP behind an injectable `HttpTransport` (like the LLM gateway), so
    the adapter is fully unit-testable without a network.
  - Credentials come from the environment ONLY (`ALPHAVANTAGE_API_KEY`);
    nothing is hardcoded and the key is never logged.
  - Compose with `ResilientPriceProvider` (retry/backoff/rate-limit/
    cache/health) — the resilience layer already exists (Module 2); this
    adapter does not re-implement it.
  - All numeric values become `Decimal` (constitution: never float).

Alpha Vantage is chosen because it is free-tier, documented, keyed by a
single env var, and covers daily equity bars and FX — enough to feed the
price/FX paths of the Data Pipeline. Swapping vendors is a new adapter,
no change to the pipeline (ADR-0017, "every integration replaceable").
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Mapping, Protocol

from providers.connectors.resilience import (
    HealthMonitor,
    RetryPolicy,
    TokenBucketRateLimiter,
    TtlCache,
)
from providers.connectors.resilient import ResilientFxProvider, ResilientPriceProvider
from providers.sdk.models import FxRate, PriceBar
from shared_kernel.exceptions import DomainError

ALPHAVANTAGE_BASE_URL = "https://www.alphavantage.co/query"
DEFAULT_TIMEOUT = 30.0
# Alpha Vantage free tier: 5 requests/min. Keep well under it.
DEFAULT_RATE_PER_SECOND = 0.08
DEFAULT_CACHE_TTL = 3600.0


class AlphaVantageError(DomainError):
    """Vendor returned an error, a rate-limit note, or unusable data."""


class HttpTransport(Protocol):
    """The only network seam; production uses `HttpxTransport`."""

    def get_json(
        self, url: str, params: Mapping[str, str], timeout: float
    ) -> Mapping[str, object]: ...


class HttpxTransport:
    """Production transport (httpx). Raises `AlphaVantageError` on failure."""

    def get_json(self, url: str, params: Mapping[str, str], timeout: float) -> Mapping[str, object]:
        import httpx

        try:
            response = httpx.get(url, params=dict(params), timeout=timeout)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as error:
            raise AlphaVantageError(f"Alpha Vantage request failed: {error}") from error
        if not isinstance(data, dict):
            raise AlphaVantageError("Alpha Vantage returned a non-object body")
        return data


def _decimal(value: object, field: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError) as error:
        raise AlphaVantageError(f"unparseable {field}: {value!r}") from error


def _guard_vendor_errors(payload: Mapping[str, object]) -> None:
    """Alpha Vantage signals problems in-band (HTTP 200 + a message)."""
    for key in ("Error Message", "Note", "Information"):
        if key in payload:
            raise AlphaVantageError(f"Alpha Vantage: {payload[key]}")


@dataclass(frozen=True)
class AlphaVantageProvider:
    """Raw adapter (no resilience). Implements PriceProvider + FXProvider."""

    api_key: str
    transport: HttpTransport
    base_url: str = ALPHAVANTAGE_BASE_URL
    timeout: float = DEFAULT_TIMEOUT

    # -- PriceProvider -------------------------------------------------------
    def daily_bars(self, ticker: str, start: date, end: date) -> tuple[PriceBar, ...]:
        payload = self.transport.get_json(
            self.base_url,
            {
                "function": "TIME_SERIES_DAILY",
                "symbol": ticker,
                "outputsize": "full",
                "apikey": self.api_key,
            },
            self.timeout,
        )
        _guard_vendor_errors(payload)
        series = payload.get("Time Series (Daily)")
        if not isinstance(series, dict):
            raise AlphaVantageError("missing 'Time Series (Daily)' in response")
        bars: list[PriceBar] = []
        for day_str, ohlc in series.items():
            try:
                day = date.fromisoformat(day_str)
            except ValueError:
                continue
            if not (start <= day <= end) or not isinstance(ohlc, dict):
                continue
            bars.append(
                PriceBar(
                    ticker=ticker,
                    day=day,
                    close=_decimal(ohlc.get("4. close"), "close"),
                    open=_decimal(ohlc.get("1. open"), "open"),
                    high=_decimal(ohlc.get("2. high"), "high"),
                    low=_decimal(ohlc.get("3. low"), "low"),
                    volume=_decimal(ohlc.get("5. volume"), "volume"),
                )
            )
        return tuple(sorted(bars, key=lambda b: b.day))

    # -- FXProvider ----------------------------------------------------------
    def rate(self, pair: str, day: date) -> FxRate | None:
        if len(pair) != 6:
            raise AlphaVantageError(f"FX pair must be 6 chars (e.g. USDVND): {pair!r}")
        payload = self.transport.get_json(
            self.base_url,
            {
                "function": "FX_DAILY",
                "from_symbol": pair[:3],
                "to_symbol": pair[3:],
                "outputsize": "full",
                "apikey": self.api_key,
            },
            self.timeout,
        )
        _guard_vendor_errors(payload)
        series = payload.get("Time Series FX (Daily)")
        if not isinstance(series, dict):
            raise AlphaVantageError("missing 'Time Series FX (Daily)' in response")
        # most recent day at or before the requested date (point-in-time)
        best: FxRate | None = None
        for day_str, ohlc in series.items():
            try:
                row_day = date.fromisoformat(day_str)
            except ValueError:
                continue
            if row_day <= day and isinstance(ohlc, dict):
                if best is None or row_day > best.day:
                    best = FxRate(
                        pair=pair, day=row_day, rate=_decimal(ohlc.get("4. close"), "rate")
                    )
        return best


def create_alphavantage_price_provider(
    *,
    api_key: str | None = None,
    transport: HttpTransport | None = None,
) -> ResilientPriceProvider:
    """Production-ready, resilient price provider from environment config.

    Reads `ALPHAVANTAGE_API_KEY` (env only). Wraps the raw adapter in the
    Module-2 resilience stack (retry/backoff, rate limit, TTL cache,
    health monitor).
    """
    key = api_key or os.environ.get("ALPHAVANTAGE_API_KEY", "")
    if not key:
        raise AlphaVantageError("ALPHAVANTAGE_API_KEY is not set")
    adapter = AlphaVantageProvider(api_key=key, transport=transport or HttpxTransport())
    return ResilientPriceProvider(
        inner=adapter,
        retry=RetryPolicy(max_attempts=4, base_delay_seconds=1.0),
        limiter=TokenBucketRateLimiter(rate_per_second=DEFAULT_RATE_PER_SECOND, capacity=5.0),
        cache=TtlCache(ttl_seconds=DEFAULT_CACHE_TTL),
        health=HealthMonitor(name="alphavantage-price"),
    )


def create_alphavantage_fx_provider(
    *,
    api_key: str | None = None,
    transport: HttpTransport | None = None,
) -> ResilientFxProvider:
    key = api_key or os.environ.get("ALPHAVANTAGE_API_KEY", "")
    if not key:
        raise AlphaVantageError("ALPHAVANTAGE_API_KEY is not set")
    adapter = AlphaVantageProvider(api_key=key, transport=transport or HttpxTransport())
    return ResilientFxProvider(
        inner=adapter,
        retry=RetryPolicy(max_attempts=4, base_delay_seconds=1.0),
        limiter=TokenBucketRateLimiter(rate_per_second=DEFAULT_RATE_PER_SECOND, capacity=5.0),
        cache=TtlCache(ttl_seconds=DEFAULT_CACHE_TTL),
        health=HealthMonitor(name="alphavantage-fx"),
    )
