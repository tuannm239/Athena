"""Ticker universe resolution for scheduled market synchronisation.

Static reference data only — resolving a sync spec into concrete symbols
never touches the network (the scheduler must not fetch directly). Two kinds
of token are understood:

  * index codes (VNINDEX, VN30, HNXINDEX, HNX30, UPCOMINDEX) — kept as-is;
    vnstock treats an index as a symbol, so `ProviderSyncService` fetches its
    daily bars like any other ticker;
  * exchange codes (HOSE, HNX, UPCOM) — expanded to a curated set of that
    exchange's most liquid tickers (below);

any other token is treated as a literal ticker, so custom lists work
(`SYNC_TICKERS="FPT,HPG,VNINDEX"`).
"""

from __future__ import annotations

from collections.abc import Iterable

from market.domain.vietnam import Index

# Index symbols (VNINDEX, VN30, HNXINDEX, HNX30, UPCOMINDEX).
INDEX_TICKERS: tuple[str, ...] = tuple(index.value for index in Index)

# Curated liquid constituents per exchange (reference data; extend as needed).
HOSE_TICKERS: tuple[str, ...] = (
    "FPT",
    "HPG",
    "VCB",
    "VIC",
    "VHM",
    "VNM",
    "MWG",
    "MSN",
    "TCB",
    "VPB",
    "MBB",
    "GAS",
    "CTG",
    "BID",
    "ACB",
    "SSI",
    "HDB",
    "VRE",
    "PLX",
    "POW",
)
HNX_TICKERS: tuple[str, ...] = ("SHS", "PVS", "IDC", "CEO", "MBS", "PVI", "TNG", "VCS")
UPCOM_TICKERS: tuple[str, ...] = ("BSR", "VGI", "MCH", "ACV", "VEA", "QNS")

EXCHANGE_TICKERS: dict[str, tuple[str, ...]] = {
    "HOSE": HOSE_TICKERS,
    "HNX": HNX_TICKERS,
    "UPCOM": UPCOM_TICKERS,
}

# Default sync spec (overridable via SYNC_TICKERS): headline indices + the
# curated constituents of the three exchanges.
DEFAULT_SYNC_SPEC: tuple[str, ...] = ("VNINDEX", "VN30", "HOSE", "HNX", "UPCOM")

# Sync scopes (see `athena sync market|universe|symbol`). These select *which*
# tickers a run covers; they do not change how a run fetches/persists (that is
# the unchanged ProviderSyncService + Data Pipeline).
#   * market   — headline indices only. Fast; safe to run every 5–15 min. The
#                dashboard's breadth / sector / snapshot are derived by the
#                existing read model from persisted prices, so refreshing the
#                index prices refreshes them too.
#   * universe — the configured symbol universe (curated constituents, ~34;
#                override with SYNC_UNIVERSE). Never "every listed company".
MARKET_SCOPE_SPEC: tuple[str, ...] = ("VNINDEX", "VN30", "HNXINDEX", "UPCOMINDEX")
UNIVERSE_SCOPE_SPEC: tuple[str, ...] = ("HOSE", "HNX", "UPCOM")


def market_scope() -> tuple[str, ...]:
    """Indices only — the fast, frequent market-refresh scope."""
    return resolve_tickers(MARKET_SCOPE_SPEC)


def universe_scope(spec: str | None = None) -> tuple[str, ...]:
    """The configured symbol universe (override via SYNC_UNIVERSE), never all."""
    return resolve_tickers(parse_spec(spec) if spec else UNIVERSE_SCOPE_SPEC)


def symbol_scope(symbol: str) -> tuple[str, ...]:
    """A single explicit symbol (`athena sync symbol FPT`)."""
    return resolve_tickers((symbol,))


def resolve_tickers(spec: Iterable[str]) -> tuple[str, ...]:
    """Expand a sync spec into a de-duplicated, ordered tuple of symbols."""
    out: list[str] = []
    seen: set[str] = set()
    for raw in spec:
        token = raw.strip().upper()
        if not token:
            continue
        candidates = EXCHANGE_TICKERS.get(token, (token,))
        for candidate in candidates:
            if candidate not in seen:
                seen.add(candidate)
                out.append(candidate)
    return tuple(out)


def parse_spec(value: str | None) -> tuple[str, ...]:
    """Parse a comma-separated SYNC_TICKERS value (or the default)."""
    if value is None or not value.strip():
        return DEFAULT_SYNC_SPEC
    return tuple(part for part in value.split(",") if part.strip())
