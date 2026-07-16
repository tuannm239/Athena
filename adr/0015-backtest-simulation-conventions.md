# ADR-0015 — Backtest Simulation Conventions

- Status: Accepted (Engineering Authorization)
- Date: 2026-07-16
- Deciders: Engineering

## Problem

SPEC-09 fixes the backtest pipeline, metrics list, bias constraints and
reports but not the numeric conventions. Authorization permits designing
them, documented here.

## Chosen conventions

1. **Rebalance cadence** (SPEC-09 modes): DAILY = every bar, WEEKLY = every
   5 bars, MONTHLY = every 21 bars (trading-day approximations).
2. **No look-ahead:** decisions at bar *t* see only data ≤ *t*; the resulting
   target weights earn the *t → t+1* return. Fact providers are called with
   the decision date and must be point-in-time; prices are sliced by the
   engine itself.
3. **No survivorship bias:** the universe at *t* is exactly the tickers with
   a price at *t*; tickers may enter/leave the dataset.
4. **Metrics** (annualization by 252 bars, risk-free rate 0 documented):
   Sharpe = mean/stdev × √252 of period portfolio returns; Sortino uses
   downside deviation; Calmar = CAGR / max drawdown; win rate = share of
   rebalance periods with positive portfolio return; profit factor = gross
   positive period P&L / gross negative; turnover = Σ|Δw|/2 per rebalance,
   annualized by cadence; alpha/beta via OLS versus benchmark period returns
   (beta = cov/var, alpha = mean_p − beta·mean_b, annualized ×252).
5. **Determinism:** no randomness anywhere; identical inputs reproduce the
   report bit-for-bit (SPEC-09 validation rule).

## Alternatives considered

Calendar-aware cadences and non-zero risk-free curves — deferred until real
trading calendars land with the data feeds (RFC-0024 sources).

## Consequences

- (+) Reproducible, bias-guarded simulation testable on synthetic series.
- (−) Approximated cadences until exchange calendars are ingested.
