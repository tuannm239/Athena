# SPEC-09 — Backtest Engine

> Status: Accepted Version: 1.0

# Backtest Engine Specification

## Purpose

The Backtest Engine validates decision logic against historical data
before production use.

No investment rule may be promoted without successful backtesting.

------------------------------------------------------------------------

# Objectives

-   Verify reproducibility
-   Measure risk-adjusted performance
-   Compare against benchmark
-   Detect overfitting

------------------------------------------------------------------------

# Inputs

-   Strategy definition
-   Decision DSL rules
-   Historical market data
-   Historical factor snapshots
-   Portfolio constraints
-   Time range

------------------------------------------------------------------------

# Outputs

## Performance Metrics

-   CAGR
-   Total Return
-   Sharpe Ratio
-   Sortino Ratio
-   Calmar Ratio
-   Maximum Drawdown
-   Win Rate
-   Profit Factor
-   Turnover
-   Alpha
-   Beta

------------------------------------------------------------------------

# Execution Pipeline

1.  Load historical dataset
2.  Build simulation universe
3.  Apply Decision Kernel
4.  Generate simulated decisions
5.  Rebalance portfolio
6.  Record trades
7.  Calculate metrics
8.  Produce report

------------------------------------------------------------------------

# Simulation Modes

-   Daily
-   Weekly
-   Monthly
-   Event-driven

------------------------------------------------------------------------

# Constraints

-   No look-ahead bias
-   No survivorship bias
-   Corporate actions adjusted
-   Deterministic execution
-   Fixed random seed where applicable

------------------------------------------------------------------------

# Benchmark

Support comparison against:

-   VNINDEX
-   VN30
-   User-defined benchmark

------------------------------------------------------------------------

# Reports

Every backtest must generate:

-   Summary
-   Equity curve
-   Drawdown curve
-   Monthly returns
-   Trade statistics
-   Decision statistics
-   Failure analysis

------------------------------------------------------------------------

# Validation Rules

A strategy cannot be promoted if:

-   Tests fail
-   Metrics are incomplete
-   Results are not reproducible
-   Required documentation is missing

------------------------------------------------------------------------

# Acceptance Criteria

-   Reproducible results
-   Versioned datasets
-   Versioned strategies
-   Full audit trail
-   Automated regression tests
