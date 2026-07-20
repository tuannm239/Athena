"""TCBS public-API price adapter (Vietnam market) — light, server-friendly.

A direct HTTP adapter to TCBS's public market-data endpoint, built to run
reliably on a server (Render): plain `httpx` + JSON, no heavyweight library,
no telemetry, and no `$HOME`/filesystem writes (the problems that made the
vnstock library fail in-container). It implements the SDK `PriceProvider`
port and covers BOTH indices and stocks, so it feeds the price dataset the
Market snapshot reads.

Design:
  - Network behind an injectable `HttpTransport` seam (like the Alpha Vantage
    adapter), so parsing is unit-testable without a network.
  - **Per-ticker tolerant**: any single ticker's failure returns `()` instead
    of raising, so one bad symbol never aborts a whole sync (the pipeline only
    fails when *every* ticker is empty).
  - Decimal everywhere (constitution: never float).
  - No business logic; it is an adapter only (ADR-0003/0017).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Mapping, Protocol, Sequence

from market.domain.vietnam import Index
from providers.sdk.models import PriceBar

TCBS_BARS_URL = "https://apipubaws.tcbs.com.vn/stock-insight/v1/stock/bars-long-term"
DEFAULT_TIMEOUT = 15.0
DEFAULT_ATTEMPTS = 2
_MAX_COUNT_BACK = 400

# vnstock/TCBS treat indices as symbols under type=index.
_INDEX_CODES: frozenset[str] = frozenset(i.value for i in Index)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AthenaBot/1.0)",
    "Accept": "application/json",
    "Origin": "https://tcinvest.tcbs.com.vn",
}

_LOG = logging.getLogger("athena.provider.tcbs")


class HttpTransport(Protocol):
    """The only network seam; production uses `HttpxTransport`."""

    def get_json(
        self, url: str, params: Mapping[str, str], timeout: float
    ) -> Mapping[str, object]: ...


class HttpxTransport:
    """Production transport (httpx) with browser-like headers."""

    def get_json(self, url: str, params: Mapping[str, str], timeout: float) -> Mapping[str, object]:
        import httpx

        response = httpx.get(url, params=dict(params), headers=_HEADERS, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("TCBS returned a non-object body")
        return data


def _dec(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _to_day(value: object) -> date | None:
    text = str(value)
    try:
        return date.fromisoformat(text[:10])  # "2026-01-31T00:00:00.000Z" -> 2026-01-31
    except ValueError:
        return None


@dataclass(frozen=True)
class TcbsProvider:
    """Raw TCBS price adapter. Implements PriceProvider (indices + stocks)."""

    transport: HttpTransport
    timeout: float = DEFAULT_TIMEOUT
    max_attempts: int = DEFAULT_ATTEMPTS
    logger: logging.Logger = field(default=_LOG)

    def daily_bars(self, ticker: str, start: date, end: date) -> tuple[PriceBar, ...]:
        symbol = ticker.upper()
        asset_type = "index" if symbol in _INDEX_CODES else "stock"
        to_ts = int(datetime(end.year, end.month, end.day, tzinfo=timezone.utc).timestamp()) + 86400
        count_back = min((end - start).days + 5, _MAX_COUNT_BACK)
        params = {
            "ticker": symbol,
            "type": asset_type,
            "resolution": "D",
            "to": str(to_ts),
            "countBack": str(count_back),
        }

        payload = self._fetch(symbol, params)
        if payload is None:
            return ()
        rows = payload.get("data")
        if not isinstance(rows, list):
            return ()

        bars: list[PriceBar] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            day = _to_day(row.get("tradingDate") or row.get("time") or row.get("date"))
            close = _dec(row.get("close"))
            if day is None or close is None or close <= 0 or not (start <= day <= end):
                continue
            bars.append(
                PriceBar(
                    ticker=symbol,
                    day=day,
                    close=close,
                    open=_dec(row.get("open")),
                    high=_dec(row.get("high")),
                    low=_dec(row.get("low")),
                    volume=_dec(row.get("volume")),
                )
            )
        return tuple(sorted(bars, key=lambda b: b.day))

    def _fetch(self, symbol: str, params: Mapping[str, str]) -> Mapping[str, object] | None:
        """Fetch with a small retry; return None on final failure (tolerant)."""
        for attempt in range(1, self.max_attempts + 1):
            try:
                return self.transport.get_json(TCBS_BARS_URL, params, self.timeout)
            except Exception as error:  # noqa: BLE001 — tolerate per-ticker failures
                self.logger.warning(
                    "tcbs.fetch_failed %s (%d/%d): %s: %s",
                    symbol,
                    attempt,
                    self.max_attempts,
                    type(error).__name__,
                    error,
                )
        return None


def create_tcbs_price_provider(*, transport: HttpTransport | None = None) -> TcbsProvider:
    """Production TCBS price provider (self-tolerant; no external credentials)."""
    return TcbsProvider(transport=transport or HttpxTransport())


# Convenience for callers that want the index set.
INDEX_CODES: Sequence[str] = tuple(_INDEX_CODES)
