# SPEC-11 — Risk Engine

> Status: Accepted Version: 2.0 (Enterprise Draft)

# Risk Engine Specification

## Purpose

The Risk Engine measures, monitors and constrains investment risk across
decisions and portfolios.

Risk management always takes precedence over return optimization.

------------------------------------------------------------------------

# Objectives

-   Quantify risk consistently
-   Enforce portfolio risk limits
-   Provide explainable risk reports
-   Support stress testing and scenario analysis

------------------------------------------------------------------------

# Responsibilities

-   Position risk
-   Portfolio risk
-   Concentration analysis
-   Liquidity risk
-   Tail risk
-   Stress testing
-   Risk budget validation

------------------------------------------------------------------------

# Inputs

-   Decision Objects
-   Portfolio State
-   Market Context
-   Historical Data
-   User Constraints

------------------------------------------------------------------------

# Core Metrics

## Market Risk

-   Beta
-   Historical Volatility
-   Realized Volatility
-   Downside Volatility

## Portfolio Risk

-   Value at Risk (VaR)
-   Conditional VaR (CVaR)
-   Maximum Drawdown
-   Expected Drawdown
-   Concentration Index

## Liquidity Risk

-   Average Daily Value
-   Days to Liquidate
-   Slippage Estimate

------------------------------------------------------------------------

# Risk Levels

-   Low
-   Moderate
-   Elevated
-   High
-   Critical

Every assessment must include a confidence score.

------------------------------------------------------------------------

# Business Rules

1.  Every approved decision requires a RiskAssessment.
2.  Portfolio risk budget must never be exceeded.
3.  Constraint violations must block approval.
4.  Every risk calculation must be reproducible.

------------------------------------------------------------------------

# Scenario Analysis

Support scenarios including:

-   Interest rate shock
-   Market crash
-   Sector rotation
-   Liquidity contraction
-   User-defined scenarios

------------------------------------------------------------------------

# Sequence

``` mermaid
sequenceDiagram
Decision Kernel->>Risk Engine: Evaluate Decision
Risk Engine->>Market Engine: Request Context
Market Engine-->>Risk Engine: Market State
Risk Engine->>Portfolio Engine: Validate Budget
Portfolio Engine-->>Risk Engine: Portfolio State
Risk Engine-->>Decision Kernel: Risk Assessment
```

------------------------------------------------------------------------

# Outputs

Risk Report

-   overall_risk
-   var
-   cvar
-   drawdown
-   liquidity
-   violations
-   recommendations
-   explanation

------------------------------------------------------------------------

# Acceptance Criteria

-   Deterministic calculations
-   Full audit trail
-   Explainable outputs
-   Automated regression tests
-   Independent from UI and LLM
