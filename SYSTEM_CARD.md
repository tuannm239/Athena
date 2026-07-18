# ATHENA — System Card

| Field | Value |
|---|---|
| System | ATHENA Financial Decision Intelligence Platform |
| Version | commit `b242881a3a0e8769f612c3ec4eb17854ab067894` |
| Date | 2026-07-18 |
| Verification basis | Phase 3 (9 verifications) + Phase 4 (9 research workstreams) |

## What the system is

A modular-monolith (ADR-0001) decision-intelligence platform that turns
market data + evidence into explainable, probabilistic, risk-aware
investment *decisions for human review*. It is **not** a trading bot: no
order-execution path exists (verified by code scan, Phase 3 Shadow Mode).

## Components (bounded contexts)

Decision Kernel (SPEC-04) · Probability Engine (RFC-0026) · Market Regime
(RFC-0025) · Risk Engine (RFC-0027) · Portfolio (sizing/optimizer) · Decision
DSL + Compiler (RFC-0017/0020) · Knowledge Graph (RFC-0019) · Feature Store &
Data Pipeline (RFC-0023/0024) · Behavior Engine (SPEC-12, advisory) · Backtest
& Scenario Simulator · LLM Gateway (ADR-0003, isolated) · Research Copilot ·
Providers SDK + connectors · Identity/Security · Observability.

## Guarantees (machine-enforced / verified)

| Property | Evidence |
|---|---|
| Clean/DDD/Hexagonal architecture | ARCHITECTURE_COMPLIANCE_REPORT (0 violations) |
| LLMs never make decisions | ADR-0003 tests, both directions |
| No autonomous capital allocation | Shadow Mode (0 orders, structural) |
| Deterministic decisions | Phase 3 V5, Phase 4 (bit-identical) |
| Security (RBAC/JWT/keys/injection) | SECURITY_AUDIT_REPORT (10/10 probes) |
| Performance (6 engines within target) | PERFORMANCE_REPORT |
| Graceful failure recovery | FAILURE_INJECTION_REPORT (11/11) |
| Data quality gating + lineage | DATA_QUALITY_REPORT |

## Research findings (Phase 4, synthetic VN market)

- Decisions are accurate (AUC 0.522, all seeds), utility-ordered
  (+0.58 %/mo), stable, drift-free — but **over-confident** (ECE 0.102).
- Portfolio beats all passive & single-factor benchmarks (p<0.0001, 100 %
  win-rate); parity-to-marginal vs a composite multi-factor strategy.
- Edge is **pro-cyclical** (expansions), not downside protection.

## Operating envelope

- **Approved use:** internal analyst decision support / shadow mode.
- **Not approved:** autonomous trading; unattended capital allocation
  (structurally impossible); live use on real capital before real-data
  certification (R1).
- **Human oversight:** required; decisions are advisory and explainable.

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| Over-confident probabilities | recommended recalibration (CALIBRATION_REPORT), reviewed & versioned |
| No real-data certification (R1) | connect feed, re-run research harnesses before live use |
| Pro-cyclical drawdown exposure | Risk/Scenario overlay; regime-conditioned risk veto |
| Model/DGP risk | conclusions are DGP-conditional; re-validate on real data |

## Change control

No architecture, framework, or business-rule change without research
evidence and explicit review. Recalibration and feature changes are
research recommendations pending real-data confirmation — none applied in
Phase 4.

## Reproducibility

Every result regenerable from the commit via `research/` harnesses; see
`EXPERIMENT_REGISTRY.md`.
