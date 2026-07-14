# SPEC-05 — Market Engine

> Status: Accepted Version: 1.0

# Market Engine Specification

## Purpose

The Market Engine evaluates the current market environment.

It provides context to the Decision Kernel but never issues investment
recommendations.

------------------------------------------------------------------------

# Responsibilities

-   Detect market regime
-   Measure liquidity
-   Evaluate market breadth
-   Estimate volatility regime
-   Identify sector rotation
-   Publish market context events

------------------------------------------------------------------------

# Inputs

## Market Data

-   OHLCV
-   Index data
-   Sector indices
-   Trading value
-   Foreign flows
-   Margin indicators (when available)

## Macro Data

-   Interest rates
-   Inflation
-   GDP
-   PMI
-   Exchange rates

------------------------------------------------------------------------

# Outputs

MarketContext

-   regime
-   confidence
-   liquidity_score
-   breadth_score
-   volatility_score
-   rotation_score
-   timestamp

------------------------------------------------------------------------

# Market Regimes

-   Expansion
-   Recovery
-   Consolidation
-   Contraction

Each regime includes a confidence value between 0.0 and 1.0.

------------------------------------------------------------------------

# Core Indicators

## Liquidity

-   Relative trading value
-   Average turnover
-   Participation rate

## Breadth

-   Advance/Decline ratio
-   New highs/new lows
-   Percentage above moving averages

## Volatility

-   Realized volatility
-   ATR percentile
-   Index volatility

------------------------------------------------------------------------

# Business Rules

-   Market regime must be deterministic.
-   Missing indicators reduce confidence.
-   Raw indicators must not be exposed directly to UI.
-   All calculations must be reproducible.

------------------------------------------------------------------------

# Domain Events

-   MarketRegimeChanged
-   LiquidityChanged
-   BreadthChanged
-   VolatilityChanged

------------------------------------------------------------------------

# Acceptance Criteria

-   Deterministic calculations
-   Test coverage \>90%
-   Independent from UI and LLM
-   Explainable outputs
