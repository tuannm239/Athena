"""Canonical factor definitions (SPEC-06, Factor Categories).

These are metadata drafts — calculation implementations arrive with
ALG-002 (Factor Engine); registering the catalogue reserves ids,
categories, units and calculation-method contracts.
"""

from __future__ import annotations

from feature_store.domain.feature import FactorCategory, FeatureMetadata

_V1 = "1.0.0"
_OWNER = "factor-library"


def _factor(
    feature_id: str, name: str, category: FactorCategory, unit: str, method: str
) -> FeatureMetadata:
    return FeatureMetadata(
        feature_id=feature_id,
        name=name,
        version=_V1,
        owner=_OWNER,
        description=f"{name} ({category.value}) — SPEC-06 Factor Library",
        data_type="decimal",
        unit=unit,
        calculation_method=method,
        category=category,
        freshness_policy="per-snapshot",
    )


def canonical_factors() -> tuple[FeatureMetadata, ...]:
    """The SPEC-06 catalogue, one draft metadata entry per factor."""
    q, g, v, m, li, r, gov = (
        FactorCategory.QUALITY,
        FactorCategory.GROWTH,
        FactorCategory.VALUE,
        FactorCategory.MOMENTUM,
        FactorCategory.LIQUIDITY,
        FactorCategory.RISK,
        FactorCategory.GOVERNANCE,
    )
    return (
        _factor("quality.roe", "ROE", q, "ratio", "net_income / avg_equity"),
        _factor("quality.roic", "ROIC", q, "ratio", "nopat / invested_capital"),
        _factor("quality.gross_margin", "Gross Margin", q, "ratio", "gross_profit / revenue"),
        _factor("quality.operating_margin", "Operating Margin", q, "ratio", "op_income / revenue"),
        _factor(
            "quality.earnings_stability",
            "Earnings Stability",
            q,
            "score",
            "1 - stdev(eps, 5y) / mean(eps, 5y)",
        ),
        _factor("growth.revenue", "Revenue Growth", g, "ratio", "yoy(revenue)"),
        _factor("growth.eps", "EPS Growth", g, "ratio", "yoy(eps)"),
        _factor("growth.fcf", "FCF Growth", g, "ratio", "yoy(free_cash_flow)"),
        _factor("growth.book_value", "Book Value Growth", g, "ratio", "yoy(book_value)"),
        _factor("value.pe_percentile", "PE Percentile", v, "percentile", "percentile(pe, 5y)"),
        _factor("value.pb_percentile", "PB Percentile", v, "percentile", "percentile(pb, 5y)"),
        _factor("value.ev_ebitda", "EV/EBITDA", v, "ratio", "enterprise_value / ebitda"),
        _factor("value.fcf_yield", "FCF Yield", v, "ratio", "free_cash_flow / market_cap"),
        _factor(
            "momentum.relative_strength",
            "Relative Strength",
            m,
            "score",
            "return(asset) - return(benchmark)",
        ),
        _factor("momentum.price", "Price Momentum", m, "ratio", "close / close[-126] - 1"),
        _factor("momentum.volume", "Volume Momentum", m, "ratio", "adv(20) / adv(120) - 1"),
        _factor(
            "liquidity.avg_daily_value", "Average Daily Value", li, "currency", "mean(value, 20)"
        ),
        _factor(
            "liquidity.turnover_ratio", "Turnover Ratio", li, "ratio", "volume / free_float_shares"
        ),
        _factor("liquidity.free_float", "Free Float", li, "ratio", "float_shares / total_shares"),
        _factor("risk.beta", "Beta", r, "ratio", "cov(r_a, r_m) / var(r_m)"),
        _factor("risk.volatility", "Volatility", r, "ratio", "stdev(returns, 252) * sqrt(252)"),
        _factor("risk.drawdown", "Drawdown", r, "ratio", "max_drawdown(close, 252)"),
        _factor(
            "risk.downside_deviation",
            "Downside Deviation",
            r,
            "ratio",
            "stdev(min(returns, 0), 252)",
        ),
        _factor(
            "governance.insider_ownership",
            "Insider Ownership",
            gov,
            "ratio",
            "insider_shares / total_shares",
        ),
        _factor(
            "governance.management_changes",
            "Management Changes",
            gov,
            "count",
            "count(executive_changes, 1y)",
        ),
        _factor(
            "governance.related_party_risk",
            "Related Party Risk",
            gov,
            "score",
            "score(related_party_transactions)",
        ),
    )
