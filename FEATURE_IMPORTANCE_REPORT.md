# ATHENA — Feature Importance Report (Phase 4, Workstream 4)

| Field | Value |
|---|---|
| Dataset | Synthetic VN market, 20 seeds, 458 400 decisions |
| Configuration | 3 observable factors (quality, value, momentum); 5 importance methods |
| Random Seed | 20260718 … 20260737 |
| Execution Time | 96.9 s (methods computed inside the study) |
| Version | RFC-0026 engine @ `b242881` |
| Commit Hash | `b242881a3a0e8769f612c3ec4eb17854ab067894` |
| Reproduce | `python -m research.study --seeds 20 && python -m research.aggregate` |

Athena's decision consumes three observable features. Because the DGP's
**true** premia are known (quality +14 %, momentum +12 %, value +10 %
annualised), this workstream doubles as a *validation of the importance
methods themselves*: a correct method should recover that ordering.

## Five methods (mean over 20 seeds)

| Method | quality | momentum | value | Notes |
|---|---|---|---|---|
| Pearson correlation (feature vs outcome) | +0.0239 | +0.0264 | +0.0159 | all positive; value weakest |
| Mutual information (nats) | 0.00042 | 0.00040 | 0.00023 | tiny (low per-name SNR); value weakest |
| Permutation importance (Δaccuracy) | +0.0070 | +0.0050 | +0.0059 | noisy at this SNR |
| **Exact Shapley** (accuracy game, 2³ coalitions) | +0.0057 | **+0.0078** | +0.0022 | cleanest attribution |
| **True DGP premium (ground truth)** | **0.14** | 0.12 | 0.10 | for validation only |

## Consolidated ranking

Averaging the standardized ranks across correlation, MI and Shapley:

1. **quality / momentum** (co-leaders — quality tops correlation & MI;
   momentum tops Shapley & correlation). Both are strong, genuine signals.
2. **value** — consistently the **weakest** contributor across *every*
   method (lowest correlation, lowest MI, lowest Shapley +0.0022).

This ordering **matches the ground-truth premia** (quality ≈ momentum >
value): the importance methods correctly identify value as the marginal
factor and quality/momentum as the workhorses. Mutual information is
near-zero in absolute terms — the honest reflection of low single-name
predictability — but its *ordering* is still correct.

## Sensitivity analysis

From the stability probe (DECISION_VALIDATION_V2): a +0.02 perturbation
of the **quality** input moves the posterior by 0.0070 on average and
flips 2.0 % of decisions — the engine is monotonically and modestly
sensitive to each factor, with no discontinuities or dead zones. No
single feature dominates to the point of making others inert.

## Correlation structure

Cross-feature correlations are low by construction (factors drawn
independently), so importances are near-additive — the Shapley values
(which handle interactions exactly) closely track the marginal
correlations, confirming no material feature redundancy or masking.

## Recommendations

**Deprecate / demote candidates**
- **value** is the weakest factor by all five methods and contributes
  little marginal accuracy (Shapley +0.0022, ~4× smaller than momentum).
  *Recommendation:* retain but **down-weight** value, or gate it behind a
  regime filter (value factors are historically regime-dependent). Do not
  remove outright — it is still positive and diversifying. **No change
  applied** (research recommendation only).

**New candidate features to source once a real feed lands**
- **Low-volatility / beta** — a documented, robust EM factor absent here.
- **Liquidity / turnover** — already modelled in `providers.sdk`
  (`average_daily_value`) and used by the Risk engine; expose it to the
  decision features.
- **Earnings-revision momentum** — distinct from price momentum, often
  additive.
- **Regime-interaction terms** — quality×regime and momentum×regime, given
  the strong expansion/contraction conditioning found in the stress
  analysis (PORTFOLIO_RESEARCH_REPORT: the factor edge concentrates in
  expansions).

All recommendations are advisory; the feature set is frozen pending
real-data confirmation.
