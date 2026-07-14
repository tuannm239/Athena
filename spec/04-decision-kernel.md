# SPEC-04 — Decision Kernel

> Status: Accepted Version: 1.0

# Decision Kernel Specification

## Purpose

The Decision Kernel is the core business engine of Athena.

It evaluates investment hypotheses using evidence, probability,
portfolio context and risk.

It never predicts prices. It evaluates decision quality.

------------------------------------------------------------------------

# Responsibilities

-   Evaluate hypotheses
-   Aggregate evidence
-   Estimate probability
-   Calculate expected utility
-   Validate decision rules
-   Produce explainable output

------------------------------------------------------------------------

# Inputs

## Market Context

-   Market regime
-   Liquidity
-   Volatility
-   Breadth

## Company Context

-   Quality
-   Growth
-   Valuation
-   Financial health
-   Catalyst

## Portfolio Context

-   Current positions
-   Cash
-   Sector exposure
-   Risk budget

## Behavioral Context

-   Bias profile
-   Historical decisions

------------------------------------------------------------------------

# Decision Pipeline

1.  Validate input
2.  Build hypothesis
3.  Collect supporting evidence
4.  Collect counter evidence
5.  Estimate probability
6.  Estimate confidence
7.  Evaluate portfolio impact
8.  Evaluate risk
9.  Calculate expected utility
10. Generate explanation
11. Produce decision object

------------------------------------------------------------------------

# Decision States

Draft

↓

Evaluated

↓

Reviewed

↓

Approved

↓

Archived

------------------------------------------------------------------------

# Decision Object

Required fields

-   hypothesis
-   evidence
-   counter_evidence
-   probability
-   confidence
-   expected_return
-   expected_drawdown
-   expected_utility
-   position_size
-   portfolio_impact
-   assumptions
-   invalidation_conditions
-   explanation

------------------------------------------------------------------------

# Decision Types

-   Accumulate
-   Reduce
-   Hold
-   Watchlist
-   Reject

These are evaluation outcomes, not trading instructions.

------------------------------------------------------------------------

# Business Rules

-   No decision without evidence.
-   Counter evidence is mandatory.
-   Confidence must be reported.
-   Probability must be bounded \[0,1\].
-   Every decision must define invalidation conditions.
-   Every approved decision must include a risk assessment.

------------------------------------------------------------------------

# Explainability

Every decision exposes:

-   Why
-   Why not
-   Assumptions
-   Missing information
-   Key risks
-   Alternative scenarios

------------------------------------------------------------------------

# Extension Points

The kernel must support plugins for:

-   New asset classes
-   New factor models
-   New probability engines
-   New optimization engines

No modification to the core kernel should be required.

------------------------------------------------------------------------

# Acceptance Criteria

-   Deterministic outputs for identical inputs.
-   Fully testable.
-   Explainable.
-   Independent of UI, database and LLM.
