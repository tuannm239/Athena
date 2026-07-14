# ADR-0004 — Align Bounded-Context Packages with SPEC-03

- Status: Accepted
- Date: 2026-07-14
- Deciders: Architecture

## Context

The initial domain skeleton (Sprint 0 bundle) used packages derived from the
draft decision-pipeline spec: `analysis`, `regime`, `market_data`, plus a
`behavior` model built around a pipeline "override" stage. The accepted
canonical specification set (SPEC-03, Domain Model) defines different bounded
contexts: **Decision, Market, Company, Portfolio, Risk, Research, Behavior,
Identity** — and SPEC-12 (v2.0) states the Behavior Engine is advisory only
and never overrides the Decision Kernel.

## Decision

1. Backend packages map 1:1 to SPEC-03 contexts: `decision_kernel` (Decision),
   `market`, `company`, `portfolio`, `risk`, `research`, `behavior`,
   `identity`, plus the `shared_kernel`.
2. `regime` and `market_data` merge into `market`; `analysis` is superseded by
   `company`. Market regimes follow SPEC-05: Expansion, Recovery,
   Consolidation, Contraction.
3. The behavioral "override" model is replaced by advisory bias detection,
   behavior reports, and an immutable decision journal (SPEC-12).
4. The Decision aggregate follows the SPEC-03/SPEC-04 lifecycle
   (Draft → UnderReview → Approved/Rejected → Archived) with evidence,
   counter-evidence, and risk-assessment invariants.

## Consequences

- (+) Code structure matches the accepted specs; import-boundary rules can be
  stated in spec vocabulary.
- (+) The LLM boundary (ADR-0003) still holds: `decision_kernel`, `risk`,
  `portfolio`, and `behavior` have no import path to any LLM gateway.
- (−) Artifacts from the draft pipeline model (CompanyAssessment, Regime
  probability distributions, TargetPortfolio, TriggeredOverride) were removed;
  they remain available in git history if a future spec reintroduces them.

## Alternatives Considered

- **Keep draft-era packages alongside canonical ones** — rejected: two
  vocabularies for the same domain violates DDD ubiquitous language.
