"""Vietnamese company fundamentals analysis (Phase 7, WS2).

Pure domain logic in the `company` bounded context: it turns a company's
financial statements into the ratios a long-term Vietnamese-equity investor
uses, plus explainable quality / valuation / growth scores. No infrastructure,
no I/O, no LLM — every number is Decimal (constitution) and every division is
guarded so a missing or zero denominator yields ``None`` rather than a crash.

Scoring is deliberately transparent (documented thresholds) so every score is
explainable, as the constitution requires. Thresholds are tuned for the
Vietnamese market's long-term-investing lens, not US/EU benchmarks.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from shared_kernel.money import Currency

_ZERO = Decimal(0)
_HUNDRED = Decimal(100)


def _div(numer: Decimal | None, denom: Decimal | None) -> Decimal | None:
    """Safe Decimal division: ``None`` if either side is missing or denom == 0."""
    if numer is None or denom is None or denom == _ZERO:
        return None
    return numer / denom


@dataclass(frozen=True, slots=True)
class FinancialStatement:
    """One reporting period for a listed company (all amounts in `currency`).

    Amounts follow Vietnamese quarterly/annual filings. Optional fields
    (`total_debt`, `ebitda`) refine ratios when available.
    """

    period: str  # e.g. "2025Q4" or "2025"
    revenue: Decimal
    gross_profit: Decimal
    operating_income: Decimal
    net_income: Decimal
    total_assets: Decimal
    total_equity: Decimal
    total_liabilities: Decimal
    current_assets: Decimal
    current_liabilities: Decimal
    cash_from_operations: Decimal
    capital_expenditure: Decimal  # positive number = cash outflow for capex
    shares_outstanding: Decimal
    total_debt: Decimal | None = None  # interest-bearing debt, if reported
    ebitda: Decimal | None = None
    currency: Currency = Currency.VND

    def __post_init__(self) -> None:
        if not self.period:
            raise ValueError("statement period must not be empty")
        if self.shares_outstanding < _ZERO:
            raise ValueError("shares_outstanding must not be negative")


@dataclass(frozen=True, slots=True)
class FundamentalRatios:
    """Computed ratios. Any ratio may be ``None`` when its inputs are absent."""

    # profitability
    roe: Decimal | None
    roa: Decimal | None
    gross_margin: Decimal | None
    operating_margin: Decimal | None
    net_margin: Decimal | None
    # leverage / liquidity
    debt_to_equity: Decimal | None
    current_ratio: Decimal | None
    # cash & per-share
    free_cash_flow: Decimal | None
    eps: Decimal | None
    bvps: Decimal | None
    # valuation (need a price)
    pe: Decimal | None
    pb: Decimal | None
    ev_ebitda: Decimal | None


def compute_ratios(
    statement: FinancialStatement, price_per_share: Decimal | None = None
) -> FundamentalRatios:
    """Compute the WS2 ratio set. `price_per_share` enables P/E, P/B, EV/EBITDA."""
    s = statement
    eps = _div(s.net_income, s.shares_outstanding)
    bvps = _div(s.total_equity, s.shares_outstanding)
    # Debt/Equity uses reported interest-bearing debt when available, else the
    # broader total-liabilities/equity (both are common; we document the choice).
    debt = s.total_debt if s.total_debt is not None else s.total_liabilities

    pe = (
        _div(price_per_share, eps)
        if (price_per_share is not None and eps and eps > _ZERO)
        else None
    )
    pb = (
        _div(price_per_share, bvps)
        if (price_per_share is not None and bvps and bvps > _ZERO)
        else None
    )

    ev_ebitda: Decimal | None = None
    if price_per_share is not None and s.ebitda is not None and s.ebitda > _ZERO:
        market_cap = price_per_share * s.shares_outstanding
        # EV = market cap + total debt − cash-equivalents. We approximate cash
        # by (current_assets − current_liabilities) only when total_debt is
        # given; otherwise EV = market cap + debt (conservative, no cash netting).
        enterprise_value = market_cap + debt
        ev_ebitda = _div(enterprise_value, s.ebitda)

    return FundamentalRatios(
        roe=_div(s.net_income, s.total_equity),
        roa=_div(s.net_income, s.total_assets),
        gross_margin=_div(s.gross_profit, s.revenue),
        operating_margin=_div(s.operating_income, s.revenue),
        net_margin=_div(s.net_income, s.revenue),
        debt_to_equity=_div(debt, s.total_equity),
        current_ratio=_div(s.current_assets, s.current_liabilities),
        free_cash_flow=s.cash_from_operations - s.capital_expenditure,
        eps=eps,
        bvps=bvps,
        pe=pe,
        pb=pb,
        ev_ebitda=ev_ebitda,
    )


def growth(current: Decimal | None, prior: Decimal | None) -> Decimal | None:
    """Period-over-period growth as a fraction (0.15 == +15%).

    Uses the magnitude of the prior value as the base so a swing from a loss
    to a profit is still meaningful; ``None`` if the base is zero/absent.
    """
    if current is None or prior is None or prior == _ZERO:
        return None
    return (current - prior) / abs(prior)


@dataclass(frozen=True, slots=True)
class QualityScores:
    """0–100 scores. Higher is better. Components are the driver breakdown."""

    quality: Decimal
    valuation: Decimal | None
    growth: Decimal | None
    components: dict[str, Decimal]


def _score_ge(value: Decimal | None, good: Decimal, weak: Decimal) -> Decimal:
    """Map a higher-is-better metric to 0..100 with a linear band [weak, good]."""
    if value is None:
        return Decimal(50)  # neutral when unknown
    if value >= good:
        return _HUNDRED
    if value <= weak:
        return _ZERO
    return ((value - weak) / (good - weak)) * _HUNDRED


def _score_le(value: Decimal | None, good: Decimal, weak: Decimal) -> Decimal:
    """Map a lower-is-better metric (e.g. D/E) to 0..100; `good` <= `weak`."""
    if value is None:
        return Decimal(50)
    if value <= good:
        return _HUNDRED
    if value >= weak:
        return _ZERO
    return ((weak - value) / (weak - good)) * _HUNDRED


def quality_score(
    ratios: FundamentalRatios,
    *,
    revenue_growth: Decimal | None = None,
    eps_growth: Decimal | None = None,
) -> QualityScores:
    """Explainable quality/valuation/growth scores for a VN long-term view.

    Quality blends profitability (ROE, ROA, net margin), balance-sheet strength
    (D/E, current ratio) and cash quality (positive FCF). Valuation rewards
    reasonable P/E and P/B. Growth blends revenue and EPS growth. Thresholds
    reflect the Vietnamese market's long-term-investing lens and are documented
    inline so every score is explainable.
    """
    d = Decimal
    profitability = {
        "roe": _score_ge(ratios.roe, good=d("0.18"), weak=d("0.05")),
        "roa": _score_ge(ratios.roa, good=d("0.08"), weak=d("0.02")),
        "net_margin": _score_ge(ratios.net_margin, good=d("0.15"), weak=d("0.03")),
    }
    strength = {
        "debt_to_equity": _score_le(ratios.debt_to_equity, good=d("0.5"), weak=d("2.0")),
        "current_ratio": _score_ge(ratios.current_ratio, good=d("1.5"), weak=d("1.0")),
    }
    cash = {
        "free_cash_flow": (
            _HUNDRED
            if (ratios.free_cash_flow is not None and ratios.free_cash_flow > _ZERO)
            else (Decimal(50) if ratios.free_cash_flow is None else _ZERO)
        )
    }

    # Weighted blend: profitability 45%, strength 30%, cash 25%.
    prof = sum(profitability.values(), _ZERO) / d(len(profitability))
    strg = sum(strength.values(), _ZERO) / d(len(strength))
    csh = sum(cash.values(), _ZERO) / d(len(cash))
    quality = prof * d("0.45") + strg * d("0.30") + csh * d("0.25")

    valuation: Decimal | None = None
    val_components: dict[str, Decimal] = {}
    if ratios.pe is not None or ratios.pb is not None:
        pe_s = _score_le(ratios.pe, good=d("10"), weak=d("25")) if ratios.pe is not None else None
        pb_s = _score_le(ratios.pb, good=d("1.5"), weak=d("4")) if ratios.pb is not None else None
        parts = [x for x in (pe_s, pb_s) if x is not None]
        if parts:
            valuation = sum(parts, _ZERO) / d(len(parts))
            if pe_s is not None:
                val_components["pe"] = pe_s
            if pb_s is not None:
                val_components["pb"] = pb_s

    grow: Decimal | None = None
    grow_components: dict[str, Decimal] = {}
    if revenue_growth is not None or eps_growth is not None:
        rev_s = (
            _score_ge(revenue_growth, good=d("0.20"), weak=_ZERO)
            if revenue_growth is not None
            else None
        )
        eps_s = (
            _score_ge(eps_growth, good=d("0.20"), weak=_ZERO) if eps_growth is not None else None
        )
        parts = [x for x in (rev_s, eps_s) if x is not None]
        if parts:
            grow = sum(parts, _ZERO) / d(len(parts))
            if rev_s is not None:
                grow_components["revenue_growth"] = rev_s
            if eps_s is not None:
                grow_components["eps_growth"] = eps_s

    components = {**profitability, **strength, **cash, **val_components, **grow_components}
    return QualityScores(
        quality=quality.quantize(Decimal("0.01")),
        valuation=valuation.quantize(Decimal("0.01")) if valuation is not None else None,
        growth=grow.quantize(Decimal("0.01")) if grow is not None else None,
        components={k: v.quantize(Decimal("0.01")) for k, v in components.items()},
    )
