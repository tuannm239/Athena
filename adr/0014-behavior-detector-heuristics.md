# ADR-0014 — Behavior Detector Heuristics

- Status: Accepted (Engineering Authorization)
- Date: 2026-07-16
- Deciders: Engineering

## Problem

SPEC-12 mandates bias detection, confidence calibration and behavioral KPIs
but defines no detection rules. Authorization permits designing internal
algorithms with configurable parameters and an ADR.

## Alternatives considered

1. ML-based detection — rejected: SPEC-12 demands deterministic scoring and
   explainable recommendations; no training data exists.
2. Hardcoded thresholds — rejected: the authorization requires configurable
   parameters.
3. **Deterministic statistics over closed decisions with thresholds in a
   config object** — chosen.

## Chosen solution

Inputs are `ClosedDecision` records (stated probability/confidence at
approval, realized success, holding days, evidence mix, review flag).
Detectors (thresholds in `BehaviorThresholds`, defaults in parentheses):

- **OVERCONFIDENCE** — mean stated confidence − realized hit rate >
  `overconfidence_gap` (0.15).
- **CONFIRMATION_BIAS** — mean share of supporting evidence >
  `confirmation_share` (0.80).
- **DISPOSITION_EFFECT** — mean holding of winners <
  `disposition_ratio` (0.5) × mean holding of losers.

Confidence calibration = mean |stated probability − outcome| (also reported
as a Brier score). Behavior score = max(0, 1 − 0.2·detected − calibration
error), normalized 0..1. KPIs: average holding days, premature-exit rate
(winners held < half the average), review completion rate. Every detection
carries a recommendation and a learning action (SPEC-12: advisory only —
never overrides the Decision Kernel).

## Consequences

- (+) Deterministic, explainable, testable; thresholds tunable per investor.
- (−) Detectors needing richer telemetry (FOMO, herding, anchoring, recency)
  wait for execution-outcome data feeds; the enum already reserves them.
