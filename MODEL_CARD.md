# ATHENA — Model Card

| Field | Value |
|---|---|
| Model | ATHENA Decision Kernel (SPEC-04) over the RFC-0026 Probability Engine |
| Version | commit `b242881a3a0e8769f612c3ec4eb17854ab067894`; compiler `athena-dslc/1.0.0` |
| Owner | Project Athena — Quantitative Research |
| Date | 2026-07-18 |
| Status | Research-validated on synthetic data; **not** certified on real market data |

## Intended use

- **Purpose:** improve investment *decision quality* — produce explainable,
  probabilistic, risk-aware assessments of investment hypotheses for
  **human review**.
- **In scope:** ranking/scoring candidate positions; probability &
  confidence estimation; evidence aggregation; portfolio construction
  input; scenario/risk analysis.
- **Out of scope (by constitution, SPEC-00):** producing BUY/SELL orders,
  allocating capital autonomously, or acting without human approval. No
  order-execution path exists in the platform (Phase 3, Shadow Mode).

## Architecture (unchanged in Phase 4)

Deterministic Bayesian pipeline: Evidence (explicit direction + reliability,
ADR-0006) → odds-form update (RFC-0026) → posterior probability + confidence
→ DSL rule adjustments (RFC-0020) → expected utility + position sizing
(RFC-0027) → Decision Object with six-facet explanation. LLM-isolated
(ADR-0003, machine-enforced both directions).

## Inputs / outputs

- **Inputs:** per-instrument observable features (quality, value, momentum;
  extensible via the feature store), market regime (RFC-0025), evidence
  items, prior probability.
- **Outputs:** posterior probability, confidence, expected utility, position
  size, matched rules, risk assessment, explanation. All Decimal; fully
  deterministic.

## Evaluation (this program, synthetic VN market, 20 seeds, 458 400 decisions)

| Metric | Value |
|---|---|
| Decision accuracy | 0.515 (AUC 0.522), positive in all 20 seeds |
| Expected-utility separation | +0.58 %/month (positive in all seeds) |
| Brier / ECE | 0.265 / **0.102 (over-confident)** |
| Stability (flip rate @ +0.02) | 2.0 % |
| Temporal drift | none (all PSI < 0.10) |
| Portfolio Sharpe vs VNINDEX | 0.656 vs 0.493, p<0.0001, 100 % win-rate |

## Known limitations

1. **Over-confident probabilities** (ECE 0.102) — recalibration recommended
   (CALIBRATION_REPORT), not applied.
2. **Pro-cyclical edge** — alpha concentrates in expansions; near-zero in
   contractions; provides no downside protection (PORTFOLIO_RESEARCH).
3. **Synthetic-data validation only** — real-market certification pending a
   licensed feed (R1). All metrics are DGP-conditional.
4. **Weak single-name signal** — value is realised through portfolio
   diversification, not individual prediction.

## Ethical / governance

- Human-in-the-loop by design; advisory only; every decision explainable
  and auditable (lineage, audit trail). LLMs never make decisions.
- Recalibration and business-rule changes require research evidence and
  explicit, versioned review — never silent/automatic.

## Maintenance

Re-run `research/study.py` on real-data folds once the feed lands; monitor
drift (PSI ≥ 0.10 alert) and calibration in production via the observability
stack.
