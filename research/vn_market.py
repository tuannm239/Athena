"""Reproducible synthetic Vietnamese-market data-generating process (DGP).

*** IMPORTANT — READ THIS ***
No licensed Vietnamese market-data feed is connected to this environment
(known gap R1, PRODUCTION_READINESS_REPORT). This module does NOT contain
real VNINDEX/VN30 history. It is a *seeded synthetic* market whose
generative process is fully known, calibrated to publicly-documented
stylized facts of the VN market (annualised drift ~12%, volatility
~22%, regime switching, sector structure, fat tails). Because the
ground-truth factor→return relationship is known by construction, it is
a rigorous testbed for whether Athena's decision machinery adds value —
and, via many seeds, it yields statistical power a single historical
path cannot. Real-market certification still requires connecting the
feed and re-running these exact harnesses.

Everything here is deterministic given the seed.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

TRADING_DAYS = 252
SECTORS = (
    "Banks",
    "RealEstate",
    "Materials",
    "ConsumerStaples",
    "Technology",
    "Energy",
    "Industrials",
    "Utilities",
)

# Stylized-fact calibration (annual) — documented VN-market characteristics.
MARKET_DRIFT_EXPANSION = 0.22
MARKET_DRIFT_CONTRACTION = -0.15
MARKET_VOL = 0.22
# Asymmetric regime persistence: expansions last longer than contractions
# (stationary distribution ~72% expansion) -> positive long-run drift,
# matching the documented VN long-run equity premium.
PERSIST_EXPANSION = 0.992
PERSIST_CONTRACTION = 0.975
SECTOR_VOL = 0.14
IDIO_VOL = 0.22

# True cross-sectional factor premia (annualised, per unit factor deviation
# from 0.5). Calibrated so a diversified factor tilt earns a detectable but
# realistic edge — single-name predictability stays low (AUC ~0.55), the
# edge emerges through portfolio diversification, as in real factor investing.
QUALITY_PREMIUM = 0.14
VALUE_PREMIUM = 0.10
MOMENTUM_PREMIUM = 0.12
BETA_LOW, BETA_HIGH = 0.85, 1.15


@dataclass(frozen=True)
class Company:
    ticker: str
    sector: str
    # hidden, slowly-drifting factor loadings in [0,1]; drive forward returns
    quality0: float
    value0: float
    momentum0: float
    market_beta: float


@dataclass
class MarketPanel:
    """The generated world."""

    seed: int
    years: int
    dates: list[int]  # day index 0..N-1
    regimes: list[str]  # 'EXPANSION' | 'CONTRACTION' per day
    market: list[float]  # VNINDEX level
    market_ret: list[float]
    sector_level: dict[str, list[float]]
    sector_ret: dict[str, list[float]]
    companies: list[Company]
    prices: dict[str, list[float]]  # ticker -> daily close
    # observable point-in-time features per ticker per day (slowly drift)
    quality: dict[str, list[float]]
    value: dict[str, list[float]]
    momentum: dict[str, list[float]]
    vn30: list[str] = field(default_factory=list)  # top-30 by end market cap

    @property
    def n_days(self) -> int:
        return len(self.dates)


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, x))


def generate_market(seed: int = 20260718, years: int = 16, n_companies: int = 120) -> MarketPanel:
    """Generate a full synthetic VN market. Deterministic in `seed`."""
    rng = random.Random(seed)
    n = years * TRADING_DAYS

    # --- regime path (RFC-0025 exercises regime classification) ---
    regimes: list[str] = []
    state = "EXPANSION"
    for _ in range(n):
        persist = PERSIST_EXPANSION if state == "EXPANSION" else PERSIST_CONTRACTION
        if rng.random() > persist:
            state = "CONTRACTION" if state == "EXPANSION" else "EXPANSION"
        regimes.append(state)

    # --- market factor path ---
    dm_exp = MARKET_DRIFT_EXPANSION / TRADING_DAYS
    dm_con = MARKET_DRIFT_CONTRACTION / TRADING_DAYS
    vm = MARKET_VOL / math.sqrt(TRADING_DAYS)
    market_ret: list[float] = []
    market = [1000.0]
    for t in range(n):
        drift = dm_exp if regimes[t] == "EXPANSION" else dm_con
        # Student-t-ish fat tails: mix of normal and occasional shock
        z = rng.gauss(0, 1)
        if rng.random() < 0.02:
            z *= 3.0  # jump
        r = drift + vm * z
        market_ret.append(r)
        market.append(market[-1] * (1 + r))
    market = market[1:]

    # --- companies with persistent hidden factors ---
    companies: list[Company] = []
    for i in range(n_companies):
        companies.append(
            Company(
                ticker=f"C{i:03d}",
                sector=SECTORS[i % len(SECTORS)],
                quality0=rng.random(),
                value0=rng.random(),
                momentum0=rng.random(),
                market_beta=rng.uniform(BETA_LOW, BETA_HIGH),
            )
        )

    # --- sector factor paths ---
    vsec = SECTOR_VOL / math.sqrt(TRADING_DAYS)
    sector_ret: dict[str, list[float]] = {s: [] for s in SECTORS}
    sector_level: dict[str, list[float]] = {s: [] for s in SECTORS}
    sec_beta = {s: rng.uniform(0.7, 1.3) for s in SECTORS}
    for s in SECTORS:
        lvl = 1000.0
        for t in range(n):
            r = sec_beta[s] * market_ret[t] + vsec * rng.gauss(0, 1)
            sector_ret[s].append(r)
            lvl *= 1 + r
            sector_level[s].append(lvl)

    # --- individual companies: returns depend on KNOWN factor structure ---
    # forward daily excess return premium (annualised, per unit factor) —
    # the "true" cross-sectional signal Athena must discover.
    Q_PREMIUM, V_PREMIUM, M_PREMIUM = QUALITY_PREMIUM, VALUE_PREMIUM, MOMENTUM_PREMIUM
    vidio = IDIO_VOL / math.sqrt(TRADING_DAYS)

    prices: dict[str, list[float]] = {}
    quality: dict[str, list[float]] = {}
    value: dict[str, list[float]] = {}
    momentum: dict[str, list[float]] = {}

    for c in companies:
        q, v, m = c.quality0, c.value0, c.momentum0
        px = 10.0 + 90.0 * rng.random()
        p_series, q_series, v_series, m_series = [], [], [], []
        for t in range(n):
            # factors drift slowly (mean-reverting random walk) -> feature drift over time
            q = _clip01(q + rng.gauss(0, 0.01) - 0.001 * (q - 0.5))
            v = _clip01(v + rng.gauss(0, 0.01) - 0.001 * (v - 0.5))
            m = _clip01(m + rng.gauss(0, 0.02) - 0.002 * (m - 0.5))
            premium = (
                Q_PREMIUM * (q - 0.5) + V_PREMIUM * (v - 0.5) + M_PREMIUM * (m - 0.5)
            ) / TRADING_DAYS
            r = (
                c.market_beta * market_ret[t]
                + 0.5 * sector_ret[c.sector][t]
                + premium
                + vidio * rng.gauss(0, 1)
            )
            px *= 1 + r
            px = max(0.5, px)  # floor
            p_series.append(px)
            # OBSERVABLE features are the hidden factors + measurement noise
            q_series.append(_clip01(q + rng.gauss(0, 0.05)))
            v_series.append(_clip01(v + rng.gauss(0, 0.05)))
            m_series.append(_clip01(m + rng.gauss(0, 0.05)))
        prices[c.ticker] = p_series
        quality[c.ticker] = q_series
        value[c.ticker] = v_series
        momentum[c.ticker] = m_series

    # --- VN30: top 30 by START-of-sample cap proxy (point-in-time, NO
    # look-ahead — using end-of-sample cap would leak future winners). ---
    start_cap = sorted(companies, key=lambda c: prices[c.ticker][0], reverse=True)
    vn30 = [c.ticker for c in start_cap[:30]]

    return MarketPanel(
        seed=seed,
        years=years,
        dates=list(range(n)),
        regimes=regimes,
        market=market,
        market_ret=market_ret,
        sector_level=sector_level,
        sector_ret=sector_ret,
        companies=companies,
        prices=prices,
        quality=quality,
        value=value,
        momentum=momentum,
        vn30=vn30,
    )


# --- small stat helpers (pure Python; no numpy/scipy) ---
def annualised_return(series: list[float]) -> float:
    n_years = len(series) / TRADING_DAYS
    return (series[-1] / series[0]) ** (1 / n_years) - 1


def daily_returns(series: list[float]) -> list[float]:
    return [series[i] / series[i - 1] - 1 for i in range(1, len(series))]


def annualised_vol(rets: list[float]) -> float:
    if len(rets) < 2:
        return 0.0
    mu = sum(rets) / len(rets)
    var = sum((r - mu) ** 2 for r in rets) / (len(rets) - 1)
    return math.sqrt(var) * math.sqrt(TRADING_DAYS)


def max_drawdown(series: list[float]) -> float:
    peak = series[0]
    mdd = 0.0
    for x in series:
        peak = max(peak, x)
        mdd = min(mdd, x / peak - 1)
    return mdd


def sharpe(rets: list[float], rf: float = 0.0) -> float:
    if len(rets) < 2:
        return 0.0
    mu = sum(rets) / len(rets) - rf / TRADING_DAYS
    sd = annualised_vol(rets) / math.sqrt(TRADING_DAYS)
    return (mu / sd * math.sqrt(TRADING_DAYS)) if sd else 0.0


def sortino(rets: list[float], rf: float = 0.0) -> float:
    if len(rets) < 2:
        return 0.0
    mu = sum(rets) / len(rets) - rf / TRADING_DAYS
    downside = [r for r in rets if r < 0]
    if not downside:
        return float("inf")
    dd = math.sqrt(sum(r * r for r in downside) / len(rets))
    return (mu / dd * math.sqrt(TRADING_DAYS)) if dd else 0.0


def calmar(series: list[float]) -> float:
    mdd = abs(max_drawdown(series))
    return (annualised_return(series) / mdd) if mdd else 0.0


if __name__ == "__main__":
    p = generate_market()
    print(f"seed={p.seed} years={p.years} days={p.n_days} companies={len(p.companies)}")
    print(
        f"VNINDEX ann.return={annualised_return(p.market):.4f} "
        f"vol={annualised_vol(p.market_ret):.4f} mdd={max_drawdown(p.market):.4f}"
    )
