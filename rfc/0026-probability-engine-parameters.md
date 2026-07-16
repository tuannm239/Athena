# RFC-0026 — Probability Engine Parameters

**Status:** Accepted (Executive Implementation Directive v1.0) **Version:** 1.0
Refines RFC-0018 with the deterministic formulas the implementation codifies.

## 1. Pipeline

```text
Prior → Evidence Reliability → Evidence Freshness → Evidence Relevance
      → Bayesian Update → Calibration → Expected Utility
```

Probability and Confidence are different concepts and are never merged.

## 2. Evidence weighting (ADR-0006 model)

Each evidence item contributes weight `w = reliability × freshness × relevance`,
all in [0, 1]:

- **reliability** — the ADR-0006 evidence attribute.
- **freshness** `= max(0, 1 − age_days / 365)` with age measured from the
  evaluation time to the evidence timestamp (linear one-year decay;
  parameter `freshness_horizon_days = 365`).
- **relevance** — supplied per evidence at evaluation time, default 1.

## 3. Bayesian update

Log-odds form over the prior `p₀ ∈ (0, 1)` (PE001 if outside):

```text
odds = p₀/(1−p₀) · Π BFᵢ
BFᵢ  = (1 + wᵢ)      if direction = SUPPORTING
     = 1/(1 + wᵢ)    if direction = CONTRADICTING
     = 1              if direction = NEUTRAL
posterior = odds/(1+odds)
```

Posterior is therefore always in (0, 1) — PE004 is unreachable by
construction and asserted in tests. Contradictory evidence is never
discarded (RFC-0018 §9).

## 4. Confidence

```text
coverage    = n/(n+2)                     (n = evidence count; 0 evidence ⇒ 0)
consistency = max(share of supporting w, share of contradicting w)
confidence  = coverage × mean(reliability) × consistency
```

Missing evidence reduces confidence; confidence is reported separately from
probability (RFC-0018 §6).

## 5. Calibration

Historical calibration data does not exist yet; the calibration step is the
identity transform and records `calibration: "identity-v1"` in the report so
future recalibration is traceable (RFC-0018 §11 audit trail).

## 6. Expected Utility (ALG-005)

```text
EU = posterior × expected_return − (1 − posterior) × expected_drawdown
```

Inputs are the decision's expected_return and expected_drawdown (fractions).
Portfolio-level utility aggregation belongs to the Portfolio Engine.

## 7. Error codes (RFC-0018 §10)

PE001 invalid prior · PE002 invalid evidence weight inputs · PE003 missing
hypothesis · PE005 calibration failure.

## 8. Output

Probability Report: prior, posterior, confidence, evidence_summary,
assumptions, uncertainty (`1 − confidence`), expected_utility, explanation —
every report carries a human-readable explanation.
