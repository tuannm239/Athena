"""VCI (Vietcap) price adapter (Vietnam market) — public, token-free.

A direct HTTP adapter to Vietcap's public trading-chart endpoint (the OHLC
feed that the `vnstock` library uses as its default `VCI` source). It is
server-friendly (plain `httpx` + JSON, no library/telemetry/`$HOME` writes)
and needs no credentials.

Unlike the VNDirect/TCBS feeds (GET + query string), VCI takes a **POST** with
a JSON body, so it carries its own transport seam (`post_json`). It implements
the SDK `PriceProvider` port and covers BOTH indices and stocks (index codes
match VCI's symbols — VNINDEX, VN30, HNXINDEX, …).

Design:
  - Network behind an injectable `HttpTransport` seam, so parsing is
    unit-testable without a network.
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

# Vietcap's OHLC chart feed (POST + JSON body). `symbols` carries both indices
# and stocks; `from`/`to` are unix seconds; `timeFrame` selects the resolution.
BARS_URL = "https://trading.vietcap.com.vn/api/chart/OHLCChart/gap"
DAILY_TIMEFRAME = "ONE_DAY"
DEFAULT_TIMEOUT = 15.0
DEFAULT_ATTEMPTS = 2

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AthenaBot/1.0)",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Origin": "https://trading.vietcap.com.vn",
    "Referer": "https://trading.vietcap.com.vn/",
}

_LOG = logging.getLogger("athena.provider.vci")


class HttpTransport(Protocol):
    """The only network seam; production uses `HttpxTransport` (POST + JSON)."""

    def post_json(self, url: str, body: Mapping[str, object], timeout: float) -> object: ...


class HttpxTransport:
    """Production transport (httpx) with browser-like headers."""

    def post_json(self, url: str, body: Mapping[str, object], timeout: float) -> object:
        import httpx

        response = httpx.post(url, json=dict(body), headers=_HEADERS, timeout=timeout)
        response.raise_for_status()
        return response.json()


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


def _column(record: Mapping[str, object], key: str) -> list[object]:
    value = record.get(key)
    return list(value) if isinstance(value, list) else []


def _pick_record(payload: object, symbol: str) -> Mapping[str, object] | None:
    """VCI returns a list of per-symbol records (or a single object)."""
    if isinstance(payload, Mapping):
        return payload
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, Mapping) and str(item.get("symbol", "")).upper() == symbol:
                return item
        # Fall back to the first object if the symbol field is absent.
        for item in payload:
            if isinstance(item, Mapping):
                return item
    return None


@dataclass(frozen=True)
class VciProvider:
    """Raw VCI (Vietcap) price adapter. Implements PriceProvider (indices + stocks)."""

    transport: HttpTransport
    timeout: float = DEFAULT_TIMEOUT
    max_attempts: int = DEFAULT_ATTEMPTS
    logger: logging.Logger = field(default=_LOG)

    def daily_bars(self, ticker: str, start: date, end: date) -> tuple[PriceBar, ...]:
        symbol = ticker.upper()
        frm = int(datetime(start.year, start.month, start.day, tzinfo=timezone.utc).timestamp())
        to = int(datetime(end.year, end.month, end.day, tzinfo=timezone.utc).timestamp()) + 86400
        body: dict[str, object] = {
            "timeFrame": DAILY_TIMEFRAME,
            "symbols": [symbol],
            "from": frm,
            "to": to,
        }

        payload = self._fetch(symbol, body)
        record = _pick_record(payload, symbol) if payload is not None else None
        if record is None:
            return ()

        times = _column(record, "t")
        closes = _column(record, "c")
        opens = _column(record, "o")
        highs = _column(record, "h")
        lows = _column(record, "l")
        volumes = _column(record, "v")
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

    def _fetch(self, symbol: str, body: Mapping[str, object]) -> object | None:
        """Fetch with a small retry; return None on final failure (tolerant)."""
        for attempt in range(1, self.max_attempts + 1):
            try:
                return self.transport.post_json(BARS_URL, body, self.timeout)
            except Exception as error:  # noqa: BLE001 — tolerate per-ticker failures
                self.logger.warning(
                    "vci.fetch_failed %s (%d/%d): %s: %s",
                    symbol,
                    attempt,
                    self.max_attempts,
                    type(error).__name__,
                    error,
                )
        return None


def create_vci_price_provider(*, transport: HttpTransport | None = None) -> VciProvider:
    """Production VCI price provider (self-tolerant; no external credentials)."""
    return VciProvider(transport=transport or HttpxTransport())


# Convenience for callers/diagnostics.
HEADERS: Mapping[str, str] = dict(_HEADERS)
__all__: Sequence[str] = ("VciProvider", "create_vci_price_provider", "BARS_URL")
