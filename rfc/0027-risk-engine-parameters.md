# RFC-0027 — Risk Engine Parameters

**Status:** Accepted (Executive Implementation Directive v1.0) **Version:** 1.0
Refines SPEC-11 with fixed parameters and the risk-score composition.

## 1. Fixed parameters

- VaR confidence: **95%** (historical method)
- CVaR confidence: **95%** (mean loss beyond VaR)
- Lookback: **252 trading days**

## 2. Risk levels (supersedes the SPEC-11 five-level naming)

| Score | Level |
|---|---|
| 0–20 | Very Low |
| 21–40 | Low |
| 41–60 | Moderate |
| 61–80 | High |
| 81–100 | Critical |

## 3. Metrics (over the lookback window of daily returns)

- Historical volatility: `stdev(returns) × √252`
- VaR95: `−quantile(returns, 0.05)` (loss as a positive fraction)
- CVaR95: `−mean(returns ≤ quantile(returns, 0.05))`
- Maximum drawdown: max peak-to-trough decline of the cumulative curve
- Downside deviation (tail risk): `stdev(min(returns, 0)) × √252`
- Liquidity: `days_to_liquidate = position_value / average_daily_value`

## 4. Risk score composition (codified; each component capped at 1)

```text
score = 100 × (0.25·min(vol/0.60, 1) + 0.25·min(VaR95/0.05, 1)
             + 0.20·min(CVaR95/0.08, 1) + 0.20·min(drawdown/0.50, 1)
             + 0.10·min(days_to_liquidate/10, 1))
```

Normalization caps: 60% annualized volatility, 5% daily VaR, 8% daily CVaR,
50% drawdown, 10 days to liquidate. Confidence of an assessment is
`min(1, observations/252)` — a full lookback gives confidence 1.

## 5. Position sizing (ALG-007)

```text
PositionSize = KellyFraction × RiskBudget × LiquidityFactor
             × Confidence × PortfolioConstraintCap
KellyFraction = max(0, p − (1 − p)/b),  b = expected_return/expected_drawdown
```

`p` = posterior probability; the result is finally capped by
`max_position_weight` and available cash (SPEC-10 constraints; cash never
negative).

## 6. Acceptance

Deterministic metrics, reproducible across runs, regression-tested against
fixed return series.
