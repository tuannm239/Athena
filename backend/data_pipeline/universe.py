"""Investment universe — the editable set of symbols the platform syncs.

The universe lives in the database (`watchlist_universe`), so it is editable
at runtime and never hardcoded in business logic. This module defines the
value types (`SyncLevel`, `UniverseEntry`), the repository port, and the
*seed data* (`DEFAULT_UNIVERSE`) used once to initialise an empty table. The
seed is initialisation data, not logic: the sync path reads symbols from the
repository, never from this constant.

Sync levels tier how aggressively a symbol is refreshed:
  * REALTIME — most liquid names; price sync every market run (5–15 min).
  * HIGH     — frequent price sync.
  * NORMAL   — daily price sync (default).
  * LOW      — profile / financials only, refreshed infrequently.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class SyncLevel(StrEnum):
    REALTIME = "REALTIME"
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"


# Priority is a stable ordering hint (lower = more important); derived from level.
_LEVEL_PRIORITY: dict[SyncLevel, int] = {
    SyncLevel.REALTIME: 1,
    SyncLevel.HIGH: 2,
    SyncLevel.NORMAL: 3,
    SyncLevel.LOW: 4,
}


@dataclass(frozen=True, slots=True)
class UniverseEntry:
    """One universe member (mirrors a `watchlist_universe` row)."""

    symbol: str
    sector: str
    sync_level: SyncLevel = SyncLevel.NORMAL
    is_active: bool = True

    @property
    def priority(self) -> int:
        return _LEVEL_PRIORITY[self.sync_level]


class UniverseRepository(Protocol):
    """Port over the persistent, editable universe."""

    def active_symbols(self, level: SyncLevel | None = None) -> tuple[str, ...]: ...

    def all(self) -> tuple[UniverseEntry, ...]: ...

    def upsert(self, entry: UniverseEntry) -> None: ...

    def set_active(self, symbol: str, active: bool) -> None: ...

    def seed_if_empty(self, entries: tuple[UniverseEntry, ...]) -> int: ...


# ---------------------------------------------------------------------------
# Default universe (seed data — sector-grouped; overrides for REALTIME/HIGH)
# ---------------------------------------------------------------------------
_SECTORS: dict[str, tuple[str, ...]] = {
    "BANKING": (
        "VCB",
        "BID",
        "CTG",
        "TCB",
        "MBB",
        "ACB",
        "STB",
        "HDB",
        "SHB",
        "MSB",
        "LPB",
        "VIB",
        "EIB",
        "TPB",
        "OCB",
        "SSB",
        "ABB",
        "NAB",
        "BAB",
        "BVB",
        "KLB",
        "PGB",
    ),
    "SECURITIES": (
        "SSI",
        "VCI",
        "HCM",
        "VND",
        "VIX",
        "FTS",
        "CTS",
        "BSI",
        "SHS",
        "MBS",
        "AGR",
        "ORS",
        "APG",
        "TVS",
        "BVS",
        "SBS",
    ),
    "REAL_ESTATE": (
        "VHM",
        "VIC",
        "NVL",
        "KDH",
        "NLG",
        "PDR",
        "DXG",
        "DIG",
        "CEO",
        "HDG",
        "KBC",
        "IDC",
        "SZC",
        "BCM",
        "SCR",
    ),
    "STEEL_MATERIALS": ("HPG", "HSG", "NKG", "CSV", "DGC", "BMP", "AAA", "GVR"),
    "CONSUMER_RETAIL": ("MWG", "FRT", "PNJ", "VNM", "MSN", "SAB", "DBC", "QNS"),
    "TECHNOLOGY": ("FPT", "CMG", "CTR", "ELC", "FOX"),
    "UTILITIES": ("POW", "REE", "NT2", "PC1", "GEG", "BWE", "VSH", "GAS"),
    "OIL_GAS": ("PLX", "PVS", "PVD", "PVC", "BSR", "OIL", "PET"),
    "LOGISTICS": ("GMD", "HAH", "VSC", "PHP", "SGP"),
    "AVIATION": ("HVN", "VJC", "AST", "SCS"),
    "HEALTHCARE": ("DHG", "DBD"),
}

# Explicit tier overrides (everything else defaults to NORMAL).
_REALTIME = frozenset({"FPT", "VCB", "HPG", "SSI", "TCB"})
_HIGH = frozenset({"MWG", "VNM", "MBB", "ACB", "VHM"})


def _level_for(symbol: str) -> SyncLevel:
    if symbol in _REALTIME:
        return SyncLevel.REALTIME
    if symbol in _HIGH:
        return SyncLevel.HIGH
    return SyncLevel.NORMAL


def _build_default_universe() -> tuple[UniverseEntry, ...]:
    seen: set[str] = set()
    entries: list[UniverseEntry] = []
    for sector, symbols in _SECTORS.items():
        for symbol in symbols:
            if symbol in seen:
                continue
            seen.add(symbol)
            entries.append(
                UniverseEntry(symbol=symbol, sector=sector, sync_level=_level_for(symbol))
            )
    return tuple(entries)


DEFAULT_UNIVERSE: tuple[UniverseEntry, ...] = _build_default_universe()
