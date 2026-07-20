"""VNDirect dchart price adapter (Vietnam market) — public, token-free.

A direct HTTP adapter to VNDirect's public charting endpoint (the TradingView
UDF `history` feed used by their web charts). It is server-friendly (plain
`httpx` + JSON, no library/telemetry/`$HOME` writes) and needs no credentials,
which is why it replaces the TCBS `bars-long-term` route after TCBS retired it
(that route now 404s from every caller).

It implements the SDK `PriceProvider` port and covers BOTH indices and stocks
(index codes match VNDirect's symbols — VNINDEX, VN30, HNXINDEX, …), so it
feeds the same price dataset the Market snapshot reads.

Design:
  - Network behind an injectable `HttpTransport` seam, so parsing is
    unit-testable without a network (same pattern as the TCBS adapter).
  - **Per-ticker tolerant**: any single ticker's failure returns `()` instead
    of raising, so one bad symbol never aborts a whole sync.
  - Decimal everywhere (constitution: never float).
  - No business logic; it is an adapter only (ADR-0003/0017).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Mapping, Protocol, Sequence

from providers.sdk.models import PriceBar

# VNDirect's TradingView-UDF daily history feed. `symbol` carries both indices
# and stocks (no separate type parameter); `from`/`to` are unix seconds.
BARS_URL = "https://dchart-api.vndirect.com.vn/dchart/history"
DEFAULT_TIMEOUT = 15.0
DEFAULT_ATTEMPTS = 2

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AthenaBot/1.0)",
    "Accept": "application/json",
    "Origin": "https://dchart.vndirect.com.vn",
    "Referer": "https://dchart.vndirect.com.vn/",
}

_LOG = logging.getLogger("athena.provider.vndirect")


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
            raise ValueError("VNDirect returned a non-object body")
        return data


def _dec(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return result


def _day_from_epoch(value: object) -> date | None:
    if not isinstance(value, (int, float, str)):
        return None
    try:
        seconds = int(float(value))
    except (TypeError, ValueError):
        return None
    try:
        return datetime.fromtimestamp(seconds, tz=timezone.utc).date()
    except (OverflowError, OSError, ValueError):
        return None


def _column(payload: Mapping[str, object], key: str) -> list[object]:
    value = payload.get(key)
    return list(value) if isinstance(value, list) else []


@dataclass(frozen=True)
class VndirectProvider:
    """Raw VNDirect dchart price adapter. Implements PriceProvider (indices + stocks)."""

    transport: HttpTransport
    timeout: float = DEFAULT_TIMEOUT
    max_attempts: int = DEFAULT_ATTEMPTS
    logger: logging.Logger = field(default=_LOG)

    def daily_bars(self, ticker: str, start: date, end: date) -> tuple[PriceBar, ...]:
        symbol = ticker.upper()
        frm = int(datetime(start.year, start.month, start.day, tzinfo=timezone.utc).timestamp())
        to = int(datetime(end.year, end.month, end.day, tzinfo=timezone.utc).timestamp()) + 86400
        params = {
            "symbol": symbol,
            "resolution": "D",
            "from": str(frm),
            "to": str(to),
        }

        payload = self._fetch(symbol, params)
        if payload is None or payload.get("s") not in (None, "ok"):
            return ()

        times = _column(payload, "t")
        closes = _column(payload, "c")
        opens = _column(payload, "o")
        highs = _column(payload, "h")
        lows = _column(payload, "l")
        volumes = _column(payload, "v")
        if not times or len(closes) != len(times):
            return ()

        bars: list[PriceBar] = []
        for i, raw_time in enumerate(times):
            day = _day_from_epoch(raw_time)
            close = _dec(closes[i])
            if day is None or close is None or close <= 0 or not (start <= day <= end):
                continue
            bars.append(
                PriceBar(
                    ticker=symbol,
                    day=day,
                    close=close,
                    open=_dec(opens[i]) if i < len(opens) else None,
                    high=_dec(highs[i]) if i < len(highs) else None,
                    low=_dec(lows[i]) if i < len(lows) else None,
                    volume=_dec(volumes[i]) if i < len(volumes) else None,
                )
            )
        return tuple(sorted(bars, key=lambda b: b.day))

    def _fetch(self, symbol: str, params: Mapping[str, str]) -> Mapping[str, object] | None:
        """Fetch with a small retry; return None on final failure (tolerant)."""
        for attempt in range(1, self.max_attempts + 1):
            try:
                return self.transport.get_json(BARS_URL, params, self.timeout)
            except Exception as error:  # noqa: BLE001 — tolerate per-ticker failures
                self.logger.warning(
                    "vndirect.fetch_failed %s (%d/%d): %s: %s",
                    symbol,
                    attempt,
                    self.max_attempts,
                    type(error).__name__,
                    error,
                )
        return None


def create_vndirect_price_provider(
    *,
    transport: HttpTransport | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    max_attempts: int = DEFAULT_ATTEMPTS,
) -> VndirectProvider:
    """Production VNDirect price provider (self-tolerant; no external credentials)."""
    return VndirectProvider(
        transport=transport or HttpxTransport(), timeout=timeout, max_attempts=max_attempts
    )


# Convenience for callers that want the header set (e.g. diagnostics).
HEADERS: Mapping[str, str] = dict(_HEADERS)
__all__: Sequence[str] = ("VndirectProvider", "create_vndirect_price_provider", "BARS_URL")
