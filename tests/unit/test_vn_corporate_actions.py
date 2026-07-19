"""Phase 7 W5 — VN portfolio corporate actions (no derivatives/margin)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from portfolio.domain.corporate_actions import (
    Holding,
    apply_cash_dividend,
    apply_rights_issue,
    apply_stock_dividend,
    apply_stock_split,
    sector_exposure,
    total_return,
)
from shared_kernel.money import Currency, Money


def _vnd(amount: str | int) -> Money:
    return Money(Decimal(amount), Currency.VND)


def _holding(qty: int = 100, cost: int = 10_000) -> Holding:
    return Holding(ticker="HPG", quantity=Decimal(qty), average_cost=_vnd(cost))


class TestCashDividend:
    def test_pays_per_share_and_leaves_holding_unchanged(self) -> None:
        cash = apply_cash_dividend(_holding(), _vnd(500))
        assert cash == _vnd(50_000)  # 100 shares × 500


class TestStockDividend:
    def test_bonus_shares_dilute_cost_basis_but_preserve_total(self) -> None:
        h = apply_stock_dividend(_holding(), Decimal("0.10"))
        assert h.quantity == Decimal(110)
        # total cost preserved at 1,000,000
        assert h.cost_basis.amount == Decimal("1000000")
        assert h.average_cost.amount == Decimal(1_000_000) / Decimal(110)


class TestStockSplit:
    def test_two_for_one(self) -> None:
        h = apply_stock_split(_holding(), Decimal(2))
        assert h.quantity == Decimal(200)
        assert h.average_cost == _vnd(5_000)
        assert h.cost_basis.amount == Decimal("1000000")


class TestRightsIssue:
    def test_subscribing_adds_shares_and_recomputes_cost(self) -> None:
        out = apply_rights_issue(_holding(), Decimal("0.5"), _vnd(15_000), subscribe=True)
        assert out.cash_outflow == _vnd(750_000)  # 50 entitled × 15,000
        assert out.holding.quantity == Decimal(150)
        # new cost basis = 1,000,000 + 750,000 = 1,750,000 over 150 shares
        assert out.holding.average_cost.amount == Decimal(1_750_000) / Decimal(150)

    def test_not_subscribing_leaves_holding_unchanged(self) -> None:
        out = apply_rights_issue(_holding(), Decimal("0.5"), _vnd(15_000), subscribe=False)
        assert out.holding.quantity == Decimal(100)
        assert out.cash_outflow == _vnd(0)


class TestExposureAndReturn:
    def test_sector_exposure_weights_sum_to_one(self) -> None:
        mv = {"HPG": _vnd(600_000), "VCB": _vnd(400_000)}
        sectors = {"HPG": "Materials", "VCB": "Financials"}
        w = sector_exposure(mv, sectors)
        assert w["Materials"] == Decimal("0.6")
        assert w["Financials"] == Decimal("0.4")
        assert sum(w.values()) == Decimal(1)

    def test_total_return_includes_dividends(self) -> None:
        r = total_return(
            cost_basis=_vnd(1_000_000), market_value=_vnd(1_200_000), dividends=_vnd(50_000)
        )
        assert r == Decimal("0.25")  # (1.2M - 1M + 50k) / 1M

    def test_total_return_none_without_cost(self) -> None:
        assert total_return(_vnd(0), _vnd(100), _vnd(0)) is None


def test_no_short_positions() -> None:
    with pytest.raises(ValueError):
        Holding(ticker="HPG", quantity=Decimal(-1), average_cost=_vnd(10_000))
