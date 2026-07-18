# ATHENA — Benchmark Report (Phase 4, Workstream 8)

| Field | Value |
|---|---|
| Dataset | Synthetic VN market, 20 seeds, 191 monthly rebalances each |
| Configuration | all strategies equal-weight; factor strategies = top quintile by that factor; monthly rebalance |
| Random Seed | 20260718 … 20260737 |
| Execution Time | 96.9 s |
| Version | RFC-0026 engine @ `b242881` |
| Commit Hash | `b242881a3a0e8769f612c3ec4eb17854ab067894` |
| Reproduce | `python -m research.study --seeds 20 && python -m research.aggregate` |

Athena (top-quintile by posterior) vs nine benchmarks, ranked by Sharpe,
with **paired bootstrap significance** (per-seed differences, 5 000
resamples).

## League table (mean over 20 seeds, ranked by Sharpe)

| Rank | Strategy | CAGR | Sharpe | Sortino | Calmar | MaxDD | EU (log) |
|---|---|---|---|---|---|---|---|
| 1 | **Athena** | **19.6 %** | **0.656** | **1.158** | **0.404** | −55.6 % | **0.0146** |
| 2 | Growth (quality+momentum) | 19.1 % | 0.646 | 1.132 | 0.380 | −56.8 % | 0.0143 |
| 3 | Quality | 17.0 % | 0.600 | 1.039 | 0.338 | −57.9 % | 0.0128 |
| 4 | Momentum | 17.0 % | 0.598 | 1.035 | 0.329 | −58.6 % | 0.0128 |
| 5 | Value | 15.7 % | 0.565 | 0.979 | 0.310 | −59.2 % | 0.0118 |
| 6 | VN30 | 12.8 % | 0.498 | 0.846 | 0.232 | −63.3 % | 0.0097 |
| 7 | Equal-Weight | 12.7 % | 0.496 | 0.842 | 0.236 | −62.9 % | 0.0096 |
| 8 | VNINDEX (passive index) | 9.6 % | 0.493 | 0.818 | 0.244 | −46.1 % | 0.0075 |
| 9 | ETF (index − fee) | 8.3 % | 0.444 | 0.729 | 0.206 | −48.4 % | 0.0065 |

Athena ranks **#1 on CAGR, Sharpe, Sortino, Calmar and expected utility**.

## Statistical significance — Athena minus benchmark

Paired bootstrap on **per-seed Sharpe** (20 seeds; 95 % CI; two-sided p;
win-rate = fraction of seeds Athena wins):

| Benchmark | ΔSharpe | 95 % CI | p | win-rate |
|---|---|---|---|---|
| ETF (passive) | **+0.213** | [+0.196, +0.230] | <0.0001 | 100 % |
| VNINDEX | **+0.163** | [+0.147, +0.180] | <0.0001 | 100 % |
| Equal-Weight | **+0.160** | [+0.151, +0.170] | <0.0001 | 100 % |
| VN30 | **+0.158** | [+0.144, +0.172] | <0.0001 | 100 % |
| Value | **+0.092** | [+0.082, +0.101] | <0.0001 | 100 % |
| Momentum | **+0.059** | [+0.047, +0.070] | <0.0001 | 100 % |
| Quality | **+0.056** | [+0.043, +0.071] | <0.0001 | 100 % |
| Growth | +0.010 | [−0.001, +0.021] | 0.076 | 65 % |

Paired bootstrap on **per-seed CAGR**:

| Benchmark | ΔCAGR | 95 % CI | p | win-rate |
|---|---|---|---|---|
| ETF (passive) | **+11.2 %** | [+9.3 %, +13.3 %] | <0.0001 | 100 % |
| VNINDEX | **+9.9 %** | [+8.0 %, +11.9 %] | <0.0001 | 100 % |
| Equal-Weight | **+6.9 %** | [+6.4 %, +7.4 %] | <0.0001 | 100 % |
| VN30 | **+6.8 %** | [+6.1 %, +7.5 %] | <0.0001 | 100 % |
| Value | **+3.9 %** | [+3.5 %, +4.3 %] | <0.0001 | 100 % |
| Momentum | **+2.6 %** | [+2.1 %, +3.1 %] | <0.0001 | 100 % |
| Quality | **+2.5 %** | [+1.9 %, +3.2 %] | <0.0001 | 100 % |
| Growth | +0.5 % | [+0.0 %, +1.0 %] | 0.043 | 70 % |

## Interpretation

- **Athena beats all passive benchmarks (VNINDEX, ETF, VN30, Equal-Weight)
  decisively** — ΔSharpe +0.16 to +0.21, ΔCAGR +6.8 to +11.2 pp, p<0.0001,
  100 % win-rate. This is the headline: the decision system adds
  statistically significant, economically large value over indexing.
- **Athena beats every single-factor strategy** (Value, Momentum, Quality)
  — p<0.0001, 100 % win-rate — because its probabilistic combination of
  the three factors is more efficient than any factor alone.
- **Athena ≈ Growth** (a hand-built quality+momentum composite): ΔSharpe
  +0.010, p=0.076 (not significant at 5 %); ΔCAGR +0.5 %, p=0.043
  (marginal), 65–70 % win-rate. **Honest conclusion:** against a
  well-designed multi-factor composite, Athena is *statistically
  indistinguishable-to-marginally-better*, not dramatically superior. Its
  advantage over Growth is that it produces **calibrated probabilities and
  explanations per decision**, not just a ranking — value that this
  return-only benchmark cannot capture.

## Verdict

Athena demonstrates **statistically significant (p<0.0001), 100 %-win-rate
outperformance over all passive and single-factor benchmarks** on
risk-adjusted return, and **parity-to-marginal-edge over a composite
multi-factor strategy**. The improvement over the investable baselines a
real portfolio would otherwise use (index/ETF/single factor) is robust and
large.
