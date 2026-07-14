# SPEC-06 — Factor Library

> Status: Accepted Version: 1.0

# Factor Library Specification

## Purpose

The Factor Library defines every quantitative and qualitative factor
used by Athena. Factors are reusable, versioned, independently testable
and composable.

------------------------------------------------------------------------

# Design Principles

-   Every factor has a unique identifier.
-   Factors are immutable once published.
-   Factors expose metadata and calculation rules.
-   Factors never contain portfolio logic.

------------------------------------------------------------------------

# Factor Categories

## Quality

-   ROE
-   ROIC
-   Gross Margin
-   Operating Margin
-   Earnings Stability

## Growth

-   Revenue Growth
-   EPS Growth
-   FCF Growth
-   Book Value Growth

## Value

-   PE Percentile
-   PB Percentile
-   EV/EBITDA
-   FCF Yield

## Momentum

-   Relative Strength
-   Price Momentum
-   Volume Momentum

## Liquidity

-   Average Daily Value
-   Turnover Ratio
-   Free Float

## Risk

-   Beta
-   Volatility
-   Drawdown
-   Downside Deviation

## Governance

-   Insider Ownership
-   Management Changes
-   Related Party Risk

------------------------------------------------------------------------

# Factor Metadata

Each factor exposes:

-   factor_id
-   name
-   category
-   description
-   unit
-   source
-   version
-   calculation_method
-   dependencies

------------------------------------------------------------------------

# Factor Interface

Inputs: - normalized dataset - evaluation date - asset identifier

Outputs: - value - confidence - quality flags

------------------------------------------------------------------------

# Registration

New factors must:

1.  Provide documentation
2.  Include unit tests
3.  Include benchmark data
4.  Declare dependencies
5.  Pass validation suite

------------------------------------------------------------------------

# Versioning

MAJOR: Breaking calculation changes

MINOR: Backward-compatible enhancements

PATCH: Documentation or bug fixes

------------------------------------------------------------------------

# Acceptance Criteria

-   Deterministic
-   Independently testable
-   Version controlled
-   Explainable
