# SPEC-10 — Portfolio Engine

> Status: Accepted Version: 2.0 (Enterprise Draft)

# Portfolio Engine Specification

## Purpose

The Portfolio Engine transforms individual investment decisions into an
optimized portfolio while respecting user-defined constraints and
institutional risk policies.

------------------------------------------------------------------------

# Goals

-   Maximize expected utility, not raw return.
-   Control concentration risk.
-   Enforce portfolio constraints.
-   Produce explainable allocation decisions.
-   Remain asset-class agnostic.

------------------------------------------------------------------------

# Responsibilities

-   Portfolio construction
-   Position sizing
-   Cash allocation
-   Rebalancing
-   Exposure management
-   Constraint validation
-   Optimization orchestration

------------------------------------------------------------------------

# Inputs

## Decision Objects

Each decision must include:

-   Probability
-   Confidence
-   Expected Return
-   Expected Drawdown
-   Expected Utility
-   Risk Score

## Portfolio State

-   Current positions
-   Cash
-   Sector exposure
-   Industry exposure
-   Asset allocation
-   User constraints

------------------------------------------------------------------------

# Portfolio Lifecycle

Draft → Constructed → Validated → Approved → Active → Rebalanced →
Archived

------------------------------------------------------------------------

# Business Rules

1.  Position size must never exceed configured limits.
2.  Sector exposure limits must be enforced.
3.  Cash allocation may not become negative.
4.  Every rebalance must be auditable.
5.  Every allocation must be reproducible.

------------------------------------------------------------------------

# Optimization Objectives

Priority order:

1.  Constraint satisfaction
2.  Risk reduction
3.  Expected utility
4.  Expected return

------------------------------------------------------------------------

# Supported Constraints

-   Maximum position weight
-   Maximum sector exposure
-   Minimum cash reserve
-   Liquidity threshold
-   Risk budget
-   Maximum turnover

------------------------------------------------------------------------

# Sequence

``` mermaid
sequenceDiagram
Decision Kernel->>Portfolio Engine: Decision Objects
Portfolio Engine->>Risk Engine: Validate Risk
Risk Engine-->>Portfolio Engine: Risk Report
Portfolio Engine->>Optimizer: Optimize Allocation
Optimizer-->>Portfolio Engine: Portfolio Proposal
Portfolio Engine-->>API: Portfolio Result
```

------------------------------------------------------------------------

# Public Interface

CreatePortfolio()

RebalancePortfolio()

ValidateConstraints()

CalculateExposure()

OptimizeAllocation()

------------------------------------------------------------------------

# Output

Portfolio Proposal

-   allocation
-   position sizes
-   cash
-   expected utility
-   expected drawdown
-   constraint violations
-   explanation

------------------------------------------------------------------------

# Acceptance Tests

-   Concentration limits enforced
-   Rebalance reproducible
-   Utility improves after optimization
-   Constraint violations reported
-   Full audit trail available
