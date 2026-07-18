# ATHENA — Quantitative Research Conclusion (Phase 4)

| Field | Value |
|---|---|
| Program | Phase 4 — Quant Research (9 workstreams) |
| Dataset | Seeded synthetic VN market, 20 seeds, 458 400 decisions |
| Version / Commit | Athena engines @ `b242881a3a0e8769f612c3ec4eb17854ab067894` |
| Date | 2026-07-18 |
| Reproduce | see `EXPERIMENT_REGISTRY.md` |

## The question

> **Can Athena consistently improve investment decision quality?**

## The answer

**Yes — conditionally and with quantified limits.** On a reproducible
synthetic Vietnamese market with known ground truth, Athena demonstrates
**measurable, statistically significant improvement over every passive and
single-factor benchmark**, consistently across 20 independent market
histories and 4 sequential time periods. The improvement is real, robust,
and economically material. Two honest qualifications bound the claim: it is
**not yet certified on real market data** (no feed connected — R1), and its
edge is **pro-cyclical stock-selection alpha, not downside protection**.

## Evidence for "yes"

| Claim | Evidence | Report |
|---|---|---|
| Decisions discriminate outcomes | AUC 0.522, **positive in all 20 seeds** | DECISION_VALIDATION_V2 |
| Decisions are utility-ordered | +0.58 %/mo EU separation, **all seeds** | DECISION_VALIDATION_V2 |
| Beats passive indexing | ΔSharpe **+0.16**, ΔCAGR **+9.9 pp** vs VNINDEX, **p<0.0001, 100 % win** | BENCHMARK_REPORT |
| Beats every single factor | ΔSharpe +0.06…+0.09 vs Value/Momentum/Quality, **p<0.0001, 100 % win** | BENCHMARK_REPORT |
| Consistent through time | wins **4/4** walk-forward folds; **83 %** of rolling windows | PORTFOLIO_RESEARCH |
| Consistent across worlds | wins **20/20** Monte-Carlo seeds | PORTFOLIO_RESEARCH |
| Stable & drift-free | 2 % flip rate; all drift PSI < 0.10 | DRIFT_REPORT |
| Recovers true factor structure | importance ranking matches ground-truth premia | FEATURE_IMPORTANCE |

The word the directive asks for — **"consistently"** — is met literally:
100 % seed win-rate, 4/4 folds, 83 % of rolling windows, all at p<0.0001.

## Honest limitations (the "conditionally")

1. **Synthetic data only.** No licensed VN feed exists (R1). Every metric is
   conditional on the data-generating process. *This is the single gating
   condition before any live-capital claim.* The identical harnesses re-run
   on real data the moment the feed lands.
2. **Over-confident probabilities** (ECE 0.102). The decision *ranking* is
   sound; the stated *probability magnitudes* are too extreme. A specific
   recalibration is recommended (shrink toward prior, k≈0.35) — **not
   applied**, per directive (CALIBRATION_REPORT).
3. **Pro-cyclical edge.** Alpha is concentrated in expansions (+1.4 %/mo)
   and vanishes in contractions (+0.07 %/mo). Athena selects better stocks;
   it does not protect the downside. Drawdown control needs the Risk/Scenario
   overlay.
4. **Parity vs a composite multi-factor strategy.** Athena's edge over a
   hand-built quality+momentum "Growth" strategy is not statistically
   significant (ΔSharpe +0.010, p=0.076). Athena's differentiator there is
   *calibrated probabilities + per-decision explanations*, not raw return.
5. **Gross of costs.** No transaction costs, slippage or liquidity limits —
   real net returns would be lower (monthly rebalancing of a top-quintile is
   turnover-intensive).

## What was NOT done (by directive)

- No architecture, framework, or business-rule change.
- No automatic recalibration (recommended only).
- No production code — **except** one testbed defect fix (VN30 look-ahead in
  the *research harness*, not Athena engine code; logged in
  EXPERIMENT_REGISTRY). Athena's frozen implementation is unchanged; the full
  test suite (338 tests, 96 % coverage) remains green.

## Recommendation

**Proceed to a real-data research pilot.** The decision machinery is sound,
validated, reproducible and value-adding on known-truth data. The remaining
uncertainty is *entirely* about real-market generalisation, which only a
licensed feed can resolve. Concretely:

1. **Connect a licensed VN market-data feed** (closes R1) — the one gate.
2. **Re-run `research/study.py` on real historical folds** and re-issue
   DECISION_VALIDATION, CALIBRATION and BENCHMARK on real data.
3. **Fit and review the recommended recalibration** on a real validation
   fold; apply as a versioned reporting-layer transform if confirmed.
4. **Run in shadow mode** (already supported, 0 orders) against the live feed
   before any capital is committed.
5. **Add the risk overlay** for contraction regimes; source the candidate
   features (low-vol, liquidity, earnings-revision) identified in
   FEATURE_IMPORTANCE.

## Final verdict

> **Athena consistently improves investment decision quality over the
> benchmarks a real portfolio would otherwise use (index, ETF, single
> factor) — statistically significant (p<0.0001), across all tested worlds
> and periods, on a reproducible known-truth testbed. The result is
> conditional on real-data certification (R1) and bounded by a correctable
> calibration bias and a pro-cyclical risk profile. The evidence supports
> advancing to a real-data pilot, not yet to live capital.**

Every conclusion above is backed by the quantitative evidence in the
nine workstream reports and is reproducible from the experiment registry.
