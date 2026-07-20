"""vnstock dataset capability catalog — what the installed vnstock provides.

The single, honest source of truth for *which* Athena market datasets the
installed `vnstock` (source `VCI`) can serve, and which it cannot. Support is
**discovered from the installed package on disk** (whether an explorer source
defines the backing method), so it reflects the version actually installed and
never fabricates a capability.

Datasets vnstock does not officially provide return **NOT_SUPPORTED** — the
platform never invents data or a placeholder for them.

This module is pure metadata + disk inspection: it imports nothing from
`vnstock` (so no telemetry) and never hits the network.
"""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

DEFAULT_SOURCE = "vci"


class Support(str, Enum):
    SUPPORTED = "SUPPORTED"
    NOT_SUPPORTED = "NOT_SUPPORTED"


@dataclass(frozen=True, slots=True)
class DatasetCapability:
    """One required dataset and how (or whether) vnstock serves it."""

    dataset: str
    support: Support
    vnstock_api: str | None  # official call, e.g. "Quote.history()"
    athena_model: str | None  # Athena DTO / read model it maps to
    persistence: str | None  # existing pipeline dataset, or None
    note: str

    def as_dict(self) -> dict[str, object]:
        return {
            "dataset": self.dataset,
            "support": self.support.value,
            "vnstock_api": self.vnstock_api,
            "athena_model": self.athena_model,
            "persistence": self.persistence,
            "note": self.note,
        }


# ---------------------------------------------------------------------------
# Disk inspection (no vnstock import)
# ---------------------------------------------------------------------------
def _explorer_dir() -> Path | None:
    try:
        spec = importlib.util.find_spec("vnstock")
    except (ImportError, ValueError, ModuleNotFoundError):
        return None
    if spec is None or not spec.submodule_search_locations:
        return None
    explorer = Path(next(iter(spec.submodule_search_locations))) / "explorer"
    return explorer if explorer.is_dir() else None


def module_defines(source: str, module: str, func: str) -> bool:
    """True iff `explorer/<source>/<module>.py` defines `def <func>(` on disk.

    This is how we tell an *implemented* VCI method (e.g. price_board) from an
    API-layer stub that raises NotImplementedError for VCI (e.g. foreign_trade).
    """
    explorer = _explorer_dir()
    if explorer is None:
        return False
    path = explorer / source / f"{module}.py"
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8", errors="ignore")
    return f"def {func}(" in text


def _supported(source: str, module: str, func: str) -> Support:
    return Support.SUPPORTED if module_defines(source, module, func) else Support.NOT_SUPPORTED


# ---------------------------------------------------------------------------
# The catalog
# ---------------------------------------------------------------------------
def catalog(source: str = DEFAULT_SOURCE) -> list[DatasetCapability]:
    """The full required-dataset catalog for the given vnstock source.

    Support flags are derived from the installed vnstock layout; the mappings
    and notes describe how each dataset relates to Athena. Historical Prices is
    the dataset wired end-to-end through the *existing* ProviderSync +
    DataPipeline; the rest are exposed as adapter capabilities (persisting them
    would require changing ProviderSyncService / the pipeline, which is out of
    scope).
    """
    s = source.lower()
    return [
        DatasetCapability(
            "Market Status",
            _supported(s, "listing", "market_status"),
            "Listing.market_status()",
            "market read model (session status)",
            None,
            "Current session open/closed + hours (not a holiday calendar).",
        ),
        DatasetCapability(
            "Market Snapshot",
            Support.NOT_SUPPORTED,
            None,
            "VnMarketSnapshotView",
            "derived from PRICES_DATASET",
            "Not a vnstock endpoint — derived by Athena's read model from "
            "persisted prices; not fetched from vnstock.",
        ),
        DatasetCapability(
            "Historical Prices",
            _supported(s, "quote", "history"),
            "Quote.history(interval='1D')",
            "PriceBar (providers.sdk.models)",
            "PRICES_DATASET (via ProviderSyncService)",
            "Indices (VNINDEX/VN30/HNXINDEX/UPCOMINDEX) and stocks. The one "
            "dataset wired end-to-end through the existing sync + pipeline.",
        ),
        DatasetCapability(
            "Price Board",
            _supported(s, "trading", "price_board"),
            "Trading.price_board(symbols_list=[...])",
            "adapter records (no persisted dataset)",
            None,
            "Real-time board for a caller-supplied symbol list.",
        ),
        DatasetCapability(
            "Trading Statistics",
            _supported(s, "company", "trading_stats"),
            "Company.trading_stats()",
            "adapter records (per symbol)",
            None,
            "Per-symbol trading statistics (Company module on VCI).",
        ),
        DatasetCapability(
            "Foreign Trading",
            _supported(s, "trading", "foreign_trade"),
            "Trading.foreign_trade()",
            None,
            None,
            "VCI does not implement foreign_trade (API stub raises "
            "NotImplementedError) — sponsor-only. NOT_SUPPORTED.",
        ),
        DatasetCapability(
            "Order Statistics",
            _supported(s, "trading", "order_stats"),
            "Trading.order_stats()",
            None,
            None,
            "VCI does not implement order_stats — sponsor-only. NOT_SUPPORTED.",
        ),
        DatasetCapability(
            "Side Statistics",
            _supported(s, "trading", "side_stats"),
            "Trading.side_stats()",
            None,
            None,
            "VCI does not implement side_stats — sponsor-only. NOT_SUPPORTED.",
        ),
        DatasetCapability(
            "Company Information",
            _supported(s, "company", "overview"),
            "Company.overview()",
            "CompanyProfile (providers.sdk.models)",
            None,
            "Company profile/overview.",
        ),
        DatasetCapability(
            "Industry Classification",
            _supported(s, "listing", "symbols_by_industries"),
            "Listing.symbols_by_industries()",
            "SectorMapping (providers.sdk.models)",
            None,
            "ICB classification per symbol.",
        ),
        DatasetCapability(
            "Financial Statements",
            _supported(s, "financial", "balance_sheet"),
            "Financial.balance_sheet()/income_statement()/cash_flow()/ratio()",
            "FundamentalRecord (providers.sdk.models)",
            None,
            "Statements + ratios.",
        ),
        DatasetCapability(
            "Trading Calendar",
            Support.NOT_SUPPORTED,
            None,
            "market/domain/vietnam.py::TradingCalendar",
            None,
            "vnstock has no exchange trading/holiday calendar (market_status is "
            "session-only; events_calendar is corporate events). Athena owns "
            "this in its domain layer. NOT_SUPPORTED from vnstock.",
        ),
        DatasetCapability(
            "Listed Symbols",
            _supported(s, "listing", "all_symbols"),
            "Listing.all_symbols()",
            "SymbolInfo (providers.sdk.models)",
            None,
            "Full listed-symbol universe.",
        ),
    ]


def catalog_as_dicts(source: str = DEFAULT_SOURCE) -> list[dict[str, object]]:
    return [c.as_dict() for c in catalog(source)]
