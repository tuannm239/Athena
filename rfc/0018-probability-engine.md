# RFC-0018 --- Probability Engine

**Status:** Draft\
**Version:** 1.0

# 1. Purpose

The Probability Engine converts evidence into calibrated probabilities.

It does NOT predict prices.

It estimates the probability that an investment hypothesis is valid.

------------------------------------------------------------------------

# 2. Principles

-   Deterministic
-   Explainable
-   Reproducible
-   Versioned
-   Testable

------------------------------------------------------------------------

# 3. Inputs

## Hypothesis

A structured investment statement.

Example:

Company ABC can sustain earnings growth above industry average over the
next 24 months.

## Evidence

Evidence objects include:

-   Source
-   Category
-   Timestamp
-   Reliability
-   Direction (support / contradict)

## Market Context

-   Market regime
-   Liquidity
-   Volatility
-   Sector strength

------------------------------------------------------------------------

# 4. Processing Pipeline

``` text
Hypothesis
    ↓
Prior Probability
    ↓
Evidence Validation
    ↓
Evidence Weighting
    ↓
Likelihood Estimation
    ↓
Bayesian Update
    ↓
Posterior Probability
    ↓
Confidence Calibration
    ↓
Expected Utility
```

------------------------------------------------------------------------

# 5. Core Objects

## Prior

Initial probability before observing new evidence.

Range:

0.0 -- 1.0

------------------------------------------------------------------------

## Likelihood

Represents the strength of evidence.

Each evidence item has:

-   reliability
-   relevance
-   direction
-   freshness

------------------------------------------------------------------------

## Posterior

Posterior is calculated after Bayesian updating.

Posterior must always remain within:

\[0.0, 1.0\]

------------------------------------------------------------------------

# 6. Confidence

Confidence measures the quality of available evidence.

Influenced by:

-   number of evidence items
-   source reliability
-   evidence consistency
-   historical calibration

Confidence is NOT probability.

------------------------------------------------------------------------

# 7. Expected Utility

Utility combines:

-   posterior probability
-   downside risk
-   expected return
-   portfolio impact

Utility is the optimization target for the Portfolio Engine.

------------------------------------------------------------------------

# 8. Outputs

Probability Report

-   prior
-   posterior
-   confidence
-   evidence_summary
-   assumptions
-   uncertainty
-   expected_utility
-   explanation

------------------------------------------------------------------------

# 9. Business Rules

-   Missing evidence reduces confidence.
-   Contradictory evidence must never be discarded.
-   Posterior probability must be reproducible.
-   Every probability must include an explanation.

------------------------------------------------------------------------

# 10. Error Codes

PE001 Invalid prior

PE002 Invalid evidence

PE003 Missing hypothesis

PE004 Probability overflow

PE005 Calibration failure

------------------------------------------------------------------------

# 11. Acceptance Criteria

-   Same input produces same output.
-   Bayesian update is unit tested.
-   Confidence and probability are reported separately.
-   Output is explainable.
-   Full audit trail is available.
