# ATHENA — Decision Validation V2 (Phase 4, Workstream 2)

| Field | Value |
|---|---|
| Dataset | Synthetic VN market, 20 seeds × 22 920 decisions = **458 400 decision-outcome pairs** |
| Configuration | monthly rebalance, 21-day forward horizon, prior 0.5, 3 factor-evidence items/decision |
| Random Seed | 20260718 … 20260737 (20 seeds) |
| Execution Time | 96.9 s (full 20-seed study) |
| Version | RFC-0026 `ProbabilityEngine` @ `b242881` |
| Commit Hash | `b242881a3a0e8769f612c3ec4eb17854ab067894` |
| Reproduce | `python -m research.study --seeds 20 && python -m research.aggregate` |

Every Decision Object from the replay is compared to its realised outcome
(did the company out-return the market over the next month). This extends
Phase 3 V5 from a single synthetic panel to a 20-seed Monte-Carlo at
full market scale.

## Decision accuracy (mean ± sd over 20 seeds)

| Metric | Value | Interpretation |
|---|---|---|
| Base rate (P[outperform]) | 0.5015 ± 0.014 | balanced target |
| Accuracy (posterior>0.5 vs outcome) | **0.5151 ± 0.0034** | +1.5 pp over random |
| AUC (rank discrimination) | **0.5218 ± 0.0039** | consistent positive discrimination |
| Brier score | 0.2648 ± 0.0007 | near-uninformed (weak per-name signal) |
| Expected-utility spread | **+0.0058 ± 0.0012** | high-posterior names out-return low-posterior by +58 bps/mo |

The per-decision edge is small but **statistically robust**: AUC > 0.5
in all 20 seeds (min 0.5104), and the EU spread is positive in all 20
seeds. This is exactly the expected profile of a genuine but noisy
cross-sectional factor signal at a monthly horizon — the edge is real
but only becomes economically large after portfolio diversification
(see PORTFOLIO_RESEARCH_REPORT and BENCHMARK_REPORT, where the
top-quintile portfolio's Sharpe advantage is highly significant).

## Expected utility

Decisions Athena rates positive (posterior > 0.5) realise a mean
market-relative return of **+0.44 %/month**; those it rates negative
realise **−0.14 %/month** — an EU separation of **+0.58 %/month**,
positive in every seed. The decision layer orders names in the direction
of realised utility (SPEC-00 principle 1).

## Calibration (summary; full study in CALIBRATION_REPORT.md)

- Expected Calibration Error **0.102 ± 0.003** — the engine is
  **systematically over-confident**: it states probabilities near 0.82
  where the realised hit-rate is 0.55, and near 0.18 where the realised
  rate is 0.45. Monotonic and consistent across seeds → a good candidate
  for post-hoc recalibration (shrinkage toward prior). **Recommended, not
  applied** (see CALIBRATION_REPORT.md).

## Decision stability

| Metric | Value |
|---|---|
| Flip rate under +0.02 feature perturbation | 2.03 % ± 0.38 % |
| Mean posterior drift under perturbation | 0.0070 ± 0.0001 |
| Determinism (identical input → identical posterior) | exact (Phase 3 V5 confirmed) |

The engine is smooth and monotonic near the decision boundary — a small
input nudge flips only ~2 % of binary calls — and fully deterministic.

## Verdict

Athena's decisions are **directionally accurate (AUC 0.522, all seeds),
utility-ordered (+0.58 %/mo separation, all seeds), and stable**, but
**over-confident** in their stated probabilities. The economic value of
the (small) per-decision edge is realised at the portfolio level. No
engine defect: the miscalibration is a tunable post-processing gap, not
a logic error — recalibration is recommended and quantified in the
calibration study.
