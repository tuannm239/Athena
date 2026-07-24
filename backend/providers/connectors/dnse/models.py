"""Map DNSE OpenAPI chart responses to Athena SDK `PriceBar`s.

DNSE's chart endpoints return TradingView-UDF style column arrays
(``{"s":"ok","t":[...],"o":[...],"h":[...],"l":[...],"c":[...],"v":[...]}``),
where ``t`` is unix seconds. Pure functions, Decimal everywhere (constitution:
never float), no business logic.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Mapping

from providers.sdk.models import PriceBar


def _dec(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


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


def _bar(
    symbol: str, day: date | None, close: object, row: Mapping[str, object]
) -> PriceBar | None:
    value = _dec(close)
    if day is None or value is None or value <= 0:
        return None
    return PriceBar(
        ticker=symbol,
        day=day,
        close=value,
        open=_dec(row.get("o", row.get("open"))),
        high=_dec(row.get("h", row.get("high"))),
        low=_dec(row.get("l", row.get("low"))),
        volume=_dec(row.get("v", row.get("volume"))),
    )


def _parse_bar_list(
    symbol: str, rows: list[object], start: date, end: date
) -> tuple[PriceBar, ...]:
    """Parse a list of bar objects (``[{t/time, o, h, l, c, v}, …]``)."""
    bars: list[PriceBar] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        day = _day_from_epoch(row.get("t", row.get("time", row.get("tradingDate"))))
        bar = _bar(symbol, day, row.get("c", row.get("close")), row)
        if bar is not None and start <= bar.day <= end:
            bars.append(bar)
    return tuple(sorted(bars, key=lambda b: b.day))


def parse_udf_bars(
    symbol: str, payload: Mapping[str, object], start: date, end: date
) -> tuple[PriceBar, ...]:
    """Parse a DNSE OHLC payload into sorted `PriceBar`s within [start, end].

    Handles both the TradingView-UDF column-array shape
    (``{"t":[…],"o":[…],…}``) and a list-of-bar-objects shape carried under
    ``data``/``bars``/``candles``. Returns ``()`` for an empty/no-data payload;
    rows without a valid positive close are skipped.
    """
    status = payload.get("s")
    if status not in (None, "ok"):
        return ()
    times = _column(payload, "t")
    if not times:
        for key in ("data", "bars", "candles", "ohlc"):
            value = payload.get(key)
            if isinstance(value, list) and value:
                return _parse_bar_list(symbol, value, start, end)
        return ()
    closes = _column(payload, "c")
    if len(closes) != len(times):
        return ()
    opens, highs, lows, volumes = (
        _column(payload, "o"),
        _column(payload, "h"),
        _column(payload, "l"),
        _column(payload, "v"),
    )
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
