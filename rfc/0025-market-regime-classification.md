# RFC-0025 — Market Regime Classification

**Status:** Accepted (Executive Implementation Directive v1.0) **Version:** 1.0

## 1. Inputs

Five indicator scores, each in **0..100**: TrendScore, BreadthScore,
LiquidityScore, MomentumScore, VolatilityScore.

## 2. Market Score

```text
MarketScore = 0.30·Trend + 0.20·Breadth + 0.20·Liquidity
            + 0.15·Momentum + 0.15·(100 − Volatility)
```

## 3. Classification

| MarketScore | Regime |
|---|---|
| ≥ 80 | Expansion |
| 60–79 | Recovery |
| 40–59 | Consolidation |
| < 40 | Contraction |

Boundaries are inclusive lower bounds (79.99 → Recovery, 80.00 → Expansion).

## 4. Confidence

```text
Confidence = WeightedConsistency × DataCompleteness   (normalized 0..1)
```

Implementation definitions (deterministic, codified here):

- **Adjusted component** `cᵢ`: the input as it enters the score
  (volatility enters as `100 − Volatility`).
- **WeightedConsistency** `= 1 − Σ wᵢ·|cᵢ − MarketScore| / 100` over the
  provided components, weights renormalized when inputs are missing.
- **DataCompleteness** `= provided_inputs / 5`.
- Missing indicators therefore reduce confidence (SPEC-05, Business Rules)
  while the score is computed over renormalized weights of present inputs.
- At least one input must be provided; zero inputs is an error.

## 5. Outputs

`MarketContext` (SPEC-05 Outputs): regime, confidence (0..1) and the five
component scores normalized to 0..1 fractions, plus timestamp.
`MarketRegimeChanged` is emitted when the classified regime differs from the
previous context.

## 6. Acceptance Criteria

- Deterministic: identical inputs ⇒ identical regime, score and confidence.
- All four regimes reachable; boundary values unit-tested.
- Missing-input handling reduces confidence and is unit-tested.
