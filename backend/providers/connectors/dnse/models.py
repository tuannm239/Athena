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


def parse_udf_bars(
    symbol: str, payload: Mapping[str, object], start: date, end: date
) -> tuple[PriceBar, ...]:
    """Parse a UDF column-array payload into sorted `PriceBar`s within [start, end].

    Returns ``()`` for an empty/no-data payload (``s`` != "ok" or no rows); rows
    without a valid positive close are skipped (index/placeholder rows).
    """
    status = payload.get("s")
    if status not in (None, "ok"):
        return ()
    times = _column(payload, "t")
    closes = _column(payload, "c")
    if not times or len(closes) != len(times):
        return ()
    opens = _column(payload, "o")
    highs = _column(payload, "h")
    lows = _column(payload, "l")
    volumes = _column(payload, "v")

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
