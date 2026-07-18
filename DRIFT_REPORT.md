# ATHENA — Decision Drift Report (Phase 4, Workstream 5)

| Field | Value |
|---|---|
| Dataset | Synthetic VN market, 20 seeds, 191 months each |
| Configuration | timeline split into thirds (early vs late); PSI on 10 bins |
| Random Seed | 20260718 … 20260737 |
| Execution Time | 96.9 s |
| Version | RFC-0026 engine @ `b242881` |
| Commit Hash | `b242881a3a0e8769f612c3ec4eb17854ab067894` |
| Reproduce | `python -m research.study --seeds 20 && python -m research.aggregate` |

Tracks whether Athena's behaviour is stable across the 16-year replay by
comparing the first third of the timeline to the last third. PSI
interpretation (industry convention): **< 0.10 = no significant shift**,
0.10–0.25 = moderate, > 0.25 = major.

## Drift metrics (mean ± sd over 20 seeds)

| Drift type | Metric | Value | Verdict |
|---|---|---|---|
| Probability drift | posterior PSI | 0.035 ± 0.019 | ✅ no shift |
| Confidence drift | confidence PSI | 0.050 ± 0.028 | ✅ no shift |
| Feature drift | quality PSI | 0.050 ± 0.025 | ✅ no shift |
| Distribution drift | decision-rate early → late | 0.505 → 0.499 | ✅ stable (−0.6 pp) |
| Decision drift | accuracy early → late | 0.516 → 0.515 | ✅ stable (−0.1 pp) |

## Analysis

- **Probability & confidence drift**: both PSI values sit well under the
  0.10 "no-shift" threshold. The posterior and confidence distributions
  the engine emits in years 1–5 are statistically the same as in years
  12–16. The engine does not wander.
- **Feature drift**: the observable factors drift slowly by construction
  (mean-reverting random walk), yet quality PSI stays at 0.05 — the
  drift is bounded and does not destabilise decisions.
- **Distribution drift**: the fraction of positive decisions is flat
  (50.5 % → 49.9 %) — no creeping bullish/bearish bias over time.
- **Decision drift (the key operational metric)**: decision accuracy is
  essentially identical early vs late (51.6 % → 51.5 %). The engine's
  edge neither decays nor strengthens over the horizon — it is a stable,
  stationary process.

## Monitoring recommendation

Because all drift metrics are benign here, no recalibration is triggered
by drift (distinct from the *calibration-level* over-confidence found in
CALIBRATION_REPORT, which is a stationary bias, not drift). For
production the recommended monitor is:

- Compute rolling-window PSI (posterior, confidence, each feature) monthly
  vs a fixed reference window; **alert at PSI ≥ 0.10**, **page at ≥ 0.25**.
- Track rolling accuracy/AUC vs the reference; alert on a sustained drop.
- These fold naturally into the existing observability stack
  (Prometheus/Grafana, ADR-0018) as research-computed gauges.

## Verdict

**No material decision drift.** Probability, confidence, feature,
distribution and decision-accuracy drift are all below the significance
threshold across all 20 seeds. Athena behaves as a stable, stationary
decision process over the full 16-year replay. (This addresses *temporal
stability*; the *level* miscalibration is handled separately in
CALIBRATION_REPORT.)
