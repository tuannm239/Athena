"""Phase 7 W1 — VN market reference + trading calendar."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from market.domain.vietnam import (
    EXCHANGES,
    INDICES,
    SECTORS,
    CorporateActionType,
    Exchange,
    Index,
    Sector,
    TradingCalendar,
    price_limit_band,
)


class TestReference:
    def test_three_exchanges_with_vn_price_limits(self) -> None:
        assert set(EXCHANGES) == {Exchange.HOSE, Exchange.HNX, Exchange.UPCOM}
        assert EXCHANGES[Exchange.HOSE].daily_price_limit == Decimal("0.07")
        assert EXCHANGES[Exchange.HNX].daily_price_limit == Decimal("0.10")
        assert EXCHANGES[Exchange.UPCOM].daily_price_limit == Decimal("0.15")

    def test_headline_indices_present(self) -> None:
        for idx in (Index.VNINDEX, Index.VN30, Index.HNX30):
            assert idx in INDICES
        assert INDICES[Index.VN30].exchange is Exchange.HOSE
        assert INDICES[Index.VN30].constituents == 30

    def test_sector_taxonomy(self) -> None:
        assert Sector.FINANCIALS in SECTORS
        assert Sector.REAL_ESTATE in SECTORS
        assert len(SECTORS) == len(set(SECTORS))

    def test_corporate_action_types_cover_vn_events(self) -> None:
        for name in ("CASH_DIVIDEND", "STOCK_DIVIDEND", "RIGHTS_ISSUE", "AGM"):
            assert hasattr(CorporateActionType, name)


class TestPriceLimits:
    def test_hose_band_is_seven_percent(self) -> None:
        floor, ceiling = price_limit_band(Exchange.HOSE, Decimal(100))
        assert floor == Decimal("93.00")
        assert ceiling == Decimal("107.00")

    def test_upcom_band_is_fifteen_percent(self) -> None:
        floor, ceiling = price_limit_band(Exchange.UPCOM, Decimal(100))
        assert floor == Decimal("85.00")
        assert ceiling == Decimal("115.00")

    def test_nonpositive_reference_rejected(self) -> None:
        with pytest.raises(ValueError):
            price_limit_band(Exchange.HOSE, Decimal(0))


class TestTradingCalendar:
    def test_weekends_are_not_trading_days(self) -> None:
        cal = TradingCalendar()
        assert cal.is_trading_day(date(2026, 1, 5)) is True  # Monday
        assert cal.is_trading_day(date(2026, 1, 3)) is False  # Saturday
        assert cal.is_trading_day(date(2026, 1, 4)) is False  # Sunday

    def test_fixed_national_holidays_seeded(self) -> None:
        cal = TradingCalendar.with_fixed_holidays(2026)
        assert cal.is_trading_day(date(2026, 9, 2)) is False  # National Day
        assert cal.is_trading_day(date(2026, 4, 30)) is False  # Reunification

    def test_next_and_previous_skip_non_trading(self) -> None:
        cal = TradingCalendar()
        # Friday 2026-01-02 → next trading day is Monday 2026-01-05
        assert cal.next_trading_day(date(2026, 1, 2)) == date(2026, 1, 5)
        assert cal.previous_trading_day(date(2026, 1, 5)) == date(2026, 1, 2)

    def test_trading_days_between_excludes_weekends_and_holidays(self) -> None:
        cal = TradingCalendar(holidays=frozenset({date(2026, 1, 1)}))
        days = cal.trading_days_between(date(2026, 1, 1), date(2026, 1, 7))
        # Jan 1 holiday, 3-4 weekend → 2,5,6,7 remain
        assert days == [date(2026, 1, 2), date(2026, 1, 5), date(2026, 1, 6), date(2026, 1, 7)]
