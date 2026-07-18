# ATHENA — Portfolio Research Report (Phase 4, Workstream 6)

| Field | Value |
|---|---|
| Dataset | Synthetic VN market, 20 seeds, 191 monthly rebalances each |
| Configuration | Athena = equal-weight top-quintile by posterior; monthly rebalance; rf=0 |
| Random Seed | 20260718 … 20260737 |
| Execution Time | study 96.9 s; supplementary analysis 33 s |
| Version | RFC-0026 engine @ `b242881` |
| Commit Hash | `b242881a3a0e8769f612c3ec4eb17854ab067894` |
| Reproduce | `python -m research.study --seeds 20 && python -m research.portfolio_extra` |

Five evaluation designs applied to the Athena top-quintile portfolio.

## 1. Monte Carlo (20 independent market histories)

| Metric | Mean | SD | Min | Max |
|---|---|---|---|---|
| CAGR | **19.6 %** | 10.2 % | −2.1 % | 44.4 % |
| Sharpe | **0.656** | 0.231 | 0.124 | 1.160 |
| P(Athena Sharpe > VNINDEX) | **100 %** | — | — | — |

Athena beat the market on risk-adjusted return in **every one** of 20
independent histories.

## 2. Walk-forward (4 sequential time folds, pooled over seeds)

| Fold | Athena Sharpe | VNINDEX Sharpe | Athena mean ret | VNINDEX mean ret |
|---|---|---|---|---|
| 1 | 0.750 | 0.572 | +2.30 %/mo | +1.14 %/mo |
| 2 | 0.652 | 0.485 | +2.01 %/mo | +0.99 %/mo |
| 3 | 0.543 | 0.379 | +1.69 %/mo | +0.77 %/mo |
| 4 | 0.672 | 0.528 | +2.08 %/mo | +1.08 %/mo |

Athena outperforms in **all four** sequential periods — the edge is not
an artifact of one lucky sub-period.

## 3. Rolling window (24-month, seed 0)

- 167 overlapping windows; Athena Sharpe > VNINDEX in **139 (83 %)**.
- Mean rolling 24-month Athena Sharpe **0.62**.

## 4. Bootstrap (6-month block bootstrap, seed 0, 5 000 resamples)

- Athena Sharpe point estimate **0.617**, 95 % CI **[0.075, 1.178]**.
- The single-path CI is wide (a 16-year history holds few independent
  6-month blocks); the **20-seed Monte-Carlo** is the higher-powered
  inference and puts the mean Sharpe firmly positive (0.656 ± 0.231).

## 5. Stress testing (regime-conditioned, 5 seeds)

| Regime | n months | Athena mean | VNINDEX mean | Athena edge |
|---|---|---|---|---|
| CONTRACTION | 220 | −0.86 % | −0.93 % | **+0.07 %** |
| EXPANSION | 735 | +3.14 % | +1.74 % | **+1.40 %** |

**Key nuance:** Athena's edge is **pro-cyclical**. In expansions it adds
+1.40 %/mo; in contractions the factor edge nearly vanishes (+0.07 %) —
Athena falls roughly with the market in downturns (it is long-only and
factor-driven, not a hedge). This is an honest, economically-sensible
finding: the value-add is stock-selection alpha in up-markets, **not**
downside protection. A risk-overlay (the Scenario Simulator / Risk
engine) remains necessary for drawdown control.

## Performance summary (mean over 20 seeds)

| Portfolio | CAGR | Sharpe | Sortino | Calmar | MaxDD | EU (log) | Vol |
|---|---|---|---|---|---|---|---|
| **Athena** | **19.6 %** | **0.656** | **1.158** | **0.404** | −55.6 % | **0.0146** | 37.0 % |
| Growth | 19.1 % | 0.646 | 1.132 | 0.380 | −56.8 % | 0.0143 | 36.9 % |
| Quality | 17.0 % | 0.600 | 1.039 | 0.338 | −57.9 % | 0.0128 | 36.9 % |
| Momentum | 17.0 % | 0.598 | 1.035 | 0.329 | −58.6 % | 0.0128 | 36.9 % |
| Value | 15.7 % | 0.565 | 0.979 | 0.310 | −59.2 % | 0.0118 | 37.0 % |
| VN30 | 12.8 % | 0.498 | 0.846 | 0.232 | −63.3 % | 0.0097 | 36.7 % |
| EqualWeight | 12.7 % | 0.496 | 0.842 | 0.236 | −62.9 % | 0.0096 | 36.7 % |
| VNINDEX | 9.6 % | 0.493 | 0.818 | 0.244 | −46.1 % | 0.0075 | 24.3 % |
| ETF (passive) | 8.3 % | 0.444 | 0.729 | 0.206 | −48.4 % | 0.0065 | 24.3 % |

Athena leads on **CAGR, Sharpe, Sortino, Calmar and expected utility**.
Note it does *not* lead on max drawdown or volatility — the index carries
less drawdown because it is not concentrated in high-beta factor names.
Athena's superiority is **risk-adjusted return via selection**, not
lower risk.

## Verdict

Across Monte-Carlo, walk-forward, rolling-window, bootstrap and stress
designs, the Athena top-quintile portfolio delivers **higher
risk-adjusted return than the market and every single-factor benchmark**,
consistently and out-of-sample-in-time. The edge is concentrated in
expansions and does not provide downside protection — a finding that
should shape how the portfolio is risk-managed, not whether it is used.
