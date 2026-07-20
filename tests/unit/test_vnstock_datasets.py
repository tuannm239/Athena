"""vnstock dataset capability catalog — SUPPORTED / NOT_SUPPORTED contract.

Asserts the catalog reflects what the installed vnstock (VCI) actually
implements on disk: prices/company/industry/listing supported; foreign /
order / side statistics NOT_SUPPORTED (API stubs on VCI); market snapshot and
trading calendar NOT_SUPPORTED from vnstock (derived / Athena-owned).
"""

from __future__ import annotations

from providers.connectors.vnstock_datasets import (
    Support,
    catalog,
    catalog_as_dicts,
    module_defines,
)

_BY_NAME = {c.dataset: c for c in catalog("vci")}


def _support(name: str) -> Support:
    return _BY_NAME[name].support


class TestSupported:
    def test_historical_prices_supported_and_persisted(self) -> None:
        cap = _BY_NAME["Historical Prices"]
        assert cap.support is Support.SUPPORTED
        assert cap.vnstock_api == "Quote.history(interval='1D')"
        assert cap.persistence and "PRICES_DATASET" in cap.persistence

    def test_core_datasets_supported(self) -> None:
        for name in (
            "Historical Prices",
            "Price Board",
            "Trading Statistics",
            "Company Information",
            "Industry Classification",
            "Financial Statements",
            "Listed Symbols",
            "Market Status",
        ):
            assert _support(name) is Support.SUPPORTED, name


class TestNotSupported:
    def test_sponsor_only_datasets_not_supported(self) -> None:
        for name in ("Foreign Trading", "Order Statistics", "Side Statistics"):
            cap = _BY_NAME[name]
            assert cap.support is Support.NOT_SUPPORTED, name
            assert cap.athena_model is None

    def test_market_snapshot_is_derived_not_fetched(self) -> None:
        cap = _BY_NAME["Market Snapshot"]
        assert cap.support is Support.NOT_SUPPORTED
        assert "derived" in cap.note.lower()

    def test_trading_calendar_is_athena_owned(self) -> None:
        cap = _BY_NAME["Trading Calendar"]
        assert cap.support is Support.NOT_SUPPORTED
        assert "TradingCalendar" in (cap.athena_model or "")


class TestDiscovery:
    def test_module_defines_reads_installed_layout(self) -> None:
        # price_board is implemented for VCI; foreign_trade is not.
        assert module_defines("vci", "trading", "price_board") is True
        assert module_defines("vci", "trading", "foreign_trade") is False

    def test_catalog_covers_all_required_datasets(self) -> None:
        names = {c["dataset"] for c in catalog_as_dicts("vci")}
        required = {
            "Market Status",
            "Market Snapshot",
            "Historical Prices",
            "Price Board",
            "Trading Statistics",
            "Foreign Trading",
            "Order Statistics",
            "Side Statistics",
            "Company Information",
            "Industry Classification",
            "Financial Statements",
            "Trading Calendar",
            "Listed Symbols",
        }
        assert required <= names

    def test_never_fabricates_unsupported_mapping(self) -> None:
        # A NOT_SUPPORTED dataset must not claim a vnstock API that returns data.
        for cap in catalog("vci"):
            if cap.support is Support.NOT_SUPPORTED and cap.dataset in (
                "Foreign Trading",
                "Order Statistics",
                "Side Statistics",
            ):
                assert cap.persistence is None
