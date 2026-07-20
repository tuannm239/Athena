"""vnstock source routing — configurable data source for the VnstockProvider.

`VnstockProvider` speaks to the Vietnamese market through the `vnstock`
library, which itself supports several upstream data sources (VCI, MSN, KBS,
…). This module is the single place that decides *which* source a run uses,
driven by the `VNSTOCK_SOURCE` environment variable.

Design decisions (per the source-routing directive):
  * **One provider, many sources.** We do not add a second provider; we route
    the existing `VnstockProvider` to a configured source.
  * **No automatic failover.** Exactly one source is used per run. If it fails,
    the error is raised with the source named — we never silently fall back to
    another source.
  * **Version-accurate, discovered from disk.** The set of supported sources
    and which datasets each serves is read from the installed `vnstock`
    package layout (`vnstock/explorer/<source>/<module>.py`), so it always
    reflects the version actually installed — no hand-maintained list that can
    drift. Reading the filesystem also avoids importing `vnstock` (and its
    telemetry) just to answer "is this source valid?".

Only sources that can serve equity price history (an `explorer/<s>/quote.py`)
are accepted for `VNSTOCK_SOURCE`, since the market sync needs OHLCV. In
vnstock 4.x that is `vci`, `msn`, `kbs`. Sources such as `ssi` or `tcbs` are
*not* part of vnstock 4.x and are reported as unsupported rather than guessed.
"""

from __future__ import annotations

import importlib.util
import re
import time
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Callable, Protocol

from shared_kernel.exceptions import DomainError

DEFAULT_SOURCE = "vci"

# Adapter dataset -> the vnstock explorer module that must exist for a source
# to serve it. Mirrors the calls VnstockProvider makes:
#   prices       -> quote.history
#   symbols      -> listing.all_symbols
#   sector       -> listing.symbols_by_industries
#   fundamentals -> financial.ratio
#   profile      -> company.overview
DATASET_MODULES: dict[str, str] = {
    "prices": "quote",
    "symbols": "listing",
    "sector": "listing",
    "fundamentals": "financial",
    "profile": "company",
}

# Used only if the installed layout cannot be read (defensive; matches 4.x).
_FALLBACK_SOURCES: tuple[str, ...] = ("vci", "msn", "kbs")


class VnstockSourceError(DomainError):
    """`VNSTOCK_SOURCE` names a source the installed vnstock does not support."""


def _vnstock_explorer_dir() -> Path | None:
    """Locate `vnstock/explorer` on disk *without importing* vnstock."""
    try:
        spec = importlib.util.find_spec("vnstock")
    except (ImportError, ValueError, ModuleNotFoundError):
        return None
    if spec is None or not spec.submodule_search_locations:
        return None
    explorer = Path(next(iter(spec.submodule_search_locations))) / "explorer"
    return explorer if explorer.is_dir() else None


def _has_module(source: str, module: str) -> bool:
    explorer = _vnstock_explorer_dir()
    if explorer is None:
        # Fall back to the known 4.x matrix when the layout is unreadable.
        if module == "quote":
            return source in _FALLBACK_SOURCES
        if module in ("listing",):
            return source in _FALLBACK_SOURCES
        return source in ("vci", "kbs")
    return (explorer / source / f"{module}.py").is_file()


def all_source_dirs() -> tuple[str, ...]:
    """Every source directory vnstock ships (for transparency/diagnostics)."""
    explorer = _vnstock_explorer_dir()
    if explorer is None:
        return _FALLBACK_SOURCES
    names = [
        p.name
        for p in explorer.iterdir()
        if p.is_dir() and not p.name.startswith("_") and p.name != "misc"
    ]
    return tuple(sorted(names))


def supported_sources() -> tuple[str, ...]:
    """Sources usable for `VNSTOCK_SOURCE` — those that can serve price history.

    Equity OHLCV is the dataset the market sync requires, so a source must
    provide `quote` to be routable. In vnstock 4.x: ``vci, msn, kbs``.
    """
    candidates = all_source_dirs()
    usable = tuple(s for s in candidates if _has_module(s, "quote"))
    return usable or _FALLBACK_SOURCES


def datasets_for_source(source: str) -> tuple[str, ...]:
    """Which Athena datasets the given source can serve, discovered from disk."""
    s = source.strip().lower()
    seen: list[str] = []
    for dataset, module in DATASET_MODULES.items():
        if _has_module(s, module) and dataset not in seen:
            seen.append(dataset)
    return tuple(seen)


def resolve_source(raw: str | None) -> str:
    """Normalise + validate `VNSTOCK_SOURCE`; raise clearly if unsupported.

    No failover: an unsupported value is a hard error naming the supported
    sources, never a silent switch to a working one.
    """
    value = (raw or DEFAULT_SOURCE).strip().lower()
    allowed = supported_sources()
    if value not in allowed:
        raise VnstockSourceError(
            f"VNSTOCK_SOURCE={raw!r} is not supported by the installed vnstock. "
            f"Supported equity sources: {', '.join(allowed)}. "
            "Automatic failover is disabled — set VNSTOCK_SOURCE to one of these."
        )
    return value


# ---------------------------------------------------------------------------
# Source probe (used by `athena provider test`)
# ---------------------------------------------------------------------------
class _HistoryClient(Protocol):
    def history(
        self, symbol: str, start: str, end: str, interval: str
    ) -> list[dict[str, object]]: ...


@dataclass(frozen=True, slots=True)
class SourceProbe:
    """One source's reachability result — the unit `athena provider test` prints."""

    source: str
    reachable: bool
    status_code: int | None
    response_ms: float
    supported_datasets: tuple[str, ...]
    rows: int
    detail: str
    category: str = "ok"  # failure classification (dns/tls/timeout/http/auth/provider)

    def as_dict(self) -> dict[str, object]:
        return {
            "source": self.source,
            "reachable": self.reachable,
            "status_code": self.status_code,
            "response_ms": self.response_ms,
            "category": self.category,
            "supported_datasets": list(self.supported_datasets),
            "rows": self.rows,
            "detail": self.detail,
        }


_STATUS_RE = re.compile(r"\b([1-5]\d{2})\b")


def _status_from_error(error: BaseException) -> int | None:
    """Best-effort HTTP status: walk the cause chain for a response/status hint."""
    seen: set[int] = set()
    current: BaseException | None = error
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        response = getattr(current, "response", None)
        code = getattr(response, "status_code", None)
        if isinstance(code, int):
            return code
        status = getattr(current, "status_code", None)
        if isinstance(status, int):
            return status
        match = _STATUS_RE.search(str(current))
        if match:
            return int(match.group(1))
        current = current.__cause__ or current.__context__
    return None


def probe_source(
    source: str,
    *,
    client_factory: Callable[[str], _HistoryClient] | None = None,
    symbol: str = "VCI",
    lookback_days: int = 7,
    today: date | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> SourceProbe:
    """Exercise one source with a small daily-history call and time it.

    Reports reachability, a best-effort HTTP status, the response time, and the
    datasets that source can serve (from the installed vnstock layout). Never
    raises — a failure is captured in the result. Injecting `client_factory`
    keeps this unit-testable without a network.
    """
    factory = client_factory or _default_history_client
    end = today or date.today()
    start = end - timedelta(days=lookback_days)
    datasets = datasets_for_source(source)
    began = clock()
    try:
        client = factory(source)
        rows = client.history(symbol, start.isoformat(), end.isoformat(), "1D")
        elapsed = round((clock() - began) * 1000, 1)
        count = len(rows)
        return SourceProbe(
            source=source,
            reachable=count > 0,
            status_code=200 if count > 0 else None,
            response_ms=elapsed,
            supported_datasets=datasets,
            rows=count,
            detail=f"{count} rows for {symbol}" if count else f"empty response for {symbol}",
        )
    except Exception as error:  # noqa: BLE001 — a probe never raises; it reports
        from providers.connectors.vnstock_diagnostics import classify_exception

        elapsed = round((clock() - began) * 1000, 1)
        category, status = classify_exception(error)
        return SourceProbe(
            source=source,
            reachable=False,
            status_code=_status_from_error(error) or status,
            response_ms=elapsed,
            supported_datasets=datasets,
            rows=0,
            detail=f"{type(error).__name__}: {error}",
            category=category.value,
        )


def _default_history_client(source: str) -> _HistoryClient:
    # Lazy import: only touch vnstock when an actual probe runs.
    from providers.connectors.vnstock_provider import RealVnstockClient

    return RealVnstockClient(source=source)
