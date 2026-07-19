"""Phase 7 W2 — VN company fundamentals (pure Decimal domain logic)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from company.domain.fundamentals import (
    FinancialStatement,
    compute_ratios,
    growth,
    quality_score,
)


def _statement(**over: object) -> FinancialStatement:
    base: dict[str, object] = dict(
        period="2025Q4",
        revenue=Decimal(1000),
        gross_profit=Decimal(400),
        operating_income=Decimal(250),
        net_income=Decimal(150),
        total_assets=Decimal(2000),
        total_equity=Decimal(1000),
        total_liabilities=Decimal(1000),
        current_assets=Decimal(600),
        current_liabilities=Decimal(300),
        cash_from_operations=Decimal(200),
        capital_expenditure=Decimal(50),
        shares_outstanding=Decimal(100),
        total_debt=Decimal(400),
        ebitda=Decimal(300),
    )
    base.update(over)
    return FinancialStatement(**base)  # type: ignore[arg-type]


class TestRatios:
    def test_core_ratios_are_exact_decimals(self) -> None:
        r = compute_ratios(_statement(), price_per_share=Decimal(30))
        assert r.roe == Decimal("0.15")
        assert r.roa == Decimal("0.075")
        assert r.gross_margin == Decimal("0.4")
        assert r.operating_margin == Decimal("0.25")
        assert r.net_margin == Decimal("0.15")
        assert r.debt_to_equity == Decimal("0.4")  # uses total_debt
        assert r.current_ratio == Decimal("2")
        assert r.free_cash_flow == Decimal(150)
        assert r.eps == Decimal("1.5")
        assert r.bvps == Decimal(10)
        assert r.pe == Decimal(20)
        assert r.pb == Decimal(3)
        assert r.ev_ebitda == (Decimal(3000) + Decimal(400)) / Decimal(300)

    def test_valuation_needs_a_price(self) -> None:
        r = compute_ratios(_statement())
        assert r.pe is None and r.pb is None and r.ev_ebitda is None
        assert r.roe == Decimal("0.15")  # non-valuation ratios still computed

    def test_zero_denominators_return_none_not_crash(self) -> None:
        r = compute_ratios(
            _statement(total_equity=Decimal(0), revenue=Decimal(0), shares_outstanding=Decimal(0)),
            price_per_share=Decimal(30),
        )
        assert r.roe is None and r.net_margin is None and r.eps is None
        assert r.pe is None  # eps None → no P/E

    def test_falls_back_to_total_liabilities_when_no_debt(self) -> None:
        r = compute_ratios(_statement(total_debt=None))
        assert r.debt_to_equity == Decimal(1)  # 1000 liabilities / 1000 equity

    def test_negative_eps_yields_no_pe(self) -> None:
        r = compute_ratios(_statement(net_income=Decimal(-50)), price_per_share=Decimal(30))
        assert r.eps == Decimal("-0.5")
        assert r.pe is None


class TestGrowth:
    def test_growth_fraction(self) -> None:
        assert growth(Decimal(120), Decimal(100)) == Decimal("0.2")

    def test_growth_uses_magnitude_base(self) -> None:
        # from a loss (-50) to a profit (50): (50 - -50)/|−50| = 2.0
        assert growth(Decimal(50), Decimal(-50)) == Decimal(2)

    def test_zero_or_missing_base_is_none(self) -> None:
        assert growth(Decimal(10), Decimal(0)) is None
        assert growth(None, Decimal(10)) is None


class TestQualityScore:
    def test_strong_company_scores_high(self) -> None:
        r = compute_ratios(_statement(), price_per_share=Decimal(30))
        s = quality_score(r, revenue_growth=Decimal("0.25"), eps_growth=Decimal("0.10"))
        assert Decimal(90) <= s.quality <= Decimal(100)
        assert s.valuation is not None and Decimal(30) <= s.valuation <= Decimal(45)
        assert s.growth == Decimal(75)  # (100 + 50) / 2
        assert "roe" in s.components

    def test_weak_company_scores_low(self) -> None:
        weak = _statement(
            net_income=Decimal(10),
            operating_income=Decimal(15),
            total_equity=Decimal(1000),
            total_liabilities=Decimal(2500),
            total_debt=Decimal(2500),
            current_assets=Decimal(200),
            current_liabilities=Decimal(400),
            cash_from_operations=Decimal(10),
            capital_expenditure=Decimal(80),
        )
        s = quality_score(compute_ratios(weak))
        assert s.quality < Decimal(40)

    def test_unknown_inputs_are_neutral_not_zero(self) -> None:
        # valuation/growth omitted → None, quality still computed from ratios
        s = quality_score(compute_ratios(_statement()))
        assert s.valuation is None and s.growth is None
        assert s.quality > Decimal(0)


def test_statement_validates() -> None:
    with pytest.raises(ValueError):
        _statement(period="")
    with pytest.raises(ValueError):
        _statement(shares_outstanding=Decimal(-1))
