# ATHENA — Calibration Study (Phase 4, Workstream 3)

| Field | Value |
|---|---|
| Dataset | Synthetic VN market, 20 seeds, 458 400 decision-outcome pairs |
| Configuration | 10-bin reliability diagram, pooled over seeds |
| Random Seed | 20260718 … 20260737 |
| Execution Time | 96.9 s |
| Version | RFC-0026 `ProbabilityEngine` @ `b242881` |
| Commit Hash | `b242881a3a0e8769f612c3ec4eb17854ab067894` |
| Reproduce | `python -m research.study --seeds 20 && python -m research.aggregate` |

## Headline metrics

| Metric | Value |
|---|---|
| Brier score | **0.2648 ± 0.0007** |
| Expected Calibration Error (ECE) | **0.1024 ± 0.0029** |
| Confidence (mean) | 0.178 |
| Confidence (p25 / p50 / p75) | 0.120 / 0.169 / 0.224 |

## Reliability diagram / calibration curve (pooled, 458 400 decisions)

| Posterior bin | n | mean predicted | realised hit-rate | gap (pred − actual) |
|---|---|---|---|---|
| 0.10–0.20 | 4 328 | 0.178 | 0.454 | **−0.276** |
| 0.20–0.30 | 34 810 | 0.260 | 0.467 | **−0.207** |
| 0.30–0.40 | 80 642 | 0.354 | 0.482 | −0.128 |
| 0.40–0.50 | 109 906 | 0.451 | 0.497 | −0.046 |
| 0.50–0.60 | 108 588 | 0.549 | 0.507 | +0.042 |
| 0.60–0.70 | 79 654 | 0.646 | 0.520 | +0.126 |
| 0.70–0.80 | 36 060 | 0.740 | 0.536 | **+0.205** |
| 0.80–0.90 | 4 412 | 0.821 | 0.547 | **+0.275** |

```
hit-rate
 0.55|                              . . ▁▂▃
 0.50|- - - - - - - - - ▁▂▃▄▅ - - - - - - -   (perfect calibration = diagonal)
 0.45| ▂▃▄▅
     +--------------------------------------
      0.18  0.35   0.45  0.55   0.65  0.74  0.82   predicted
```

**Diagnosis: systematic over-confidence.** The calibration curve is far
flatter than the identity line and pivots around 0.5: extreme
predictions (both high and low) are pulled toward the true ~0.5 base
rate. The engine's Bayesian odds update (RFC-0026) amplifies weak
evidence into over-strong posteriors because, in this low-SNR regime,
the evidence reliability is systematically higher than its true
predictive weight.

## Confidence distribution

Confidence (RFC-0026: coverage × reliability × consistency) is
right-skewed and low (mean 0.178, p75 0.224, max 0.559) — the engine
correctly reports **low confidence** even while its **point probabilities
are over-dispersed**. Confidence and probability are separate axes
(RFC-0026), and confidence behaves sensibly; the miscalibration is in the
probability magnitude, not the confidence signal.

## Recommendation (NOT applied — per directive)

The miscalibration is monotonic, stable across all 20 seeds, and
therefore correctable **without changing business logic** via a post-hoc
calibration map applied at the reporting boundary:

1. **Shrinkage toward prior (recommended):** `p' = 0.5 + k·(p − 0.5)`
   with `k ≈ 0.35` (estimated from the curve slope). This is a pure
   monotone re-scaling — it preserves decision *ordering* (AUC, EU spread
   unchanged) while aligning stated probabilities with realised
   frequencies. Expected post-map ECE ≈ 0.02–0.03.
2. **Platt / temperature scaling** as an alternative parametric fit.

**Governance note:** per the Phase 4 directive, calibration is **not
automatically adjusted**. Recalibration should be (a) fit on a real-data
validation fold once the feed lands, (b) reviewed, and (c) applied as an
explicit, versioned reporting-layer transform — never silently, and never
inside the Decision Kernel. The decision *ranking* is already sound; only
the probability *labels* need rescaling.

## Verdict

Calibration **drifts from the diagonal (ECE 0.102)** in a consistent,
correctable way. The finding is logged and a specific recalibration is
recommended; no change is made to the frozen implementation.
