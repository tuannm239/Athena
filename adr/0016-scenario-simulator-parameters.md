# ADR-0016 — Scenario Simulator Parameters

- Status: Accepted (Engineering Authorization)
- Date: 2026-07-16
- Deciders: Engineering

## Problem

ALG-015 and SPEC-11 §Scenario Analysis name the scenario families
(interest-rate shock, market crash, sector rotation, liquidity contraction,
user-defined) without shock magnitudes. Authorization requires parameters to
be configurable rather than hardcoded.

## Chosen solution

A `Scenario` value object carries a uniform market shock, per-sector shocks
and a liquidity haircut; stress testing applies them linearly to position
weights (documented approximation — no cross-asset correlation model until
one is specified). Built-in scenarios are provided as *default parameter
sets*, overridable at call time:

| Scenario | Market | Sector shocks | Liquidity haircut |
|---|---|---|---|
| interest_rate_shock | −8% | Financials −15%, Real Estate −12% | 20% |
| market_crash | −20% | — | 40% |
| sector_rotation | 0% | named winners +10% / losers −10% | 0% |
| liquidity_contraction | −5% | — | 50% |

Stressed liquidity scales days-to-liquidate by 1/(1 − haircut).

## Alternatives considered

Factor-model propagation via the Knowledge Graph — planned once factor
loadings exist (ALG-002 data); the linear model is the simplest design
satisfying SPEC-11 today.

## Consequences

- (+) Deterministic, explainable stress results with tunable parameters.
- (−) Linear shocks ignore correlation/convexity until factor data lands.
