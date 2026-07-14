# SPEC-03 — Decision Pipeline

Status: Draft (Sprint 0)
Owner: Architecture
Last updated: 2026-07-14

The pipeline is the spine of ATHENA. Stages run in order; none may be skipped. Each stage consumes the versioned output contract of the previous stage and emits its own versioned contract.

## Stage Contracts

### 1. Data
- **In:** external sources (market, fundamental, alternative).
- **Out:** raw payloads persisted with source, timestamp, and snapshot ID.
- **Invariant:** raw data is immutable once ingested.

### 2. Normalization
- **In:** raw payloads.
- **Out:** canonical entities (instruments, prices, fundamentals) with corporate actions applied, currencies unified, calendars aligned.
- **Invariant:** every normalized record traces to raw records.

### 3. Feature Engineering
- **In:** canonical entities.
- **Out:** versioned feature sets in the feature store (Polars/DuckDB).
- **Invariant:** features are pure functions of a snapshot; no look-ahead.

### 4. Knowledge Graph
- **In:** canonical entities + curated relationships.
- **Out:** graph of companies, sectors, factors, events, supply-chain links.
- **Invariant:** every edge has provenance.

### 5. Market Regime
- **In:** features + graph context.
- **Out:** regime label(s) with probability distribution (e.g., risk-on/risk-off, volatility state).
- **Invariant:** downstream analyses must condition on regime output.

### 6. Sector Analysis
- **In:** regime, features, graph.
- **Out:** probabilistic sector assessments with drivers/attributions.

### 7. Company Analysis
- **In:** sector context, company features, graph neighborhood.
- **Out:** probabilistic company assessments with drivers/attributions.

### 8. Probability Update
- **In:** prior assessments + new evidence.
- **Out:** posterior probabilities (Bayesian update, PyMC), with calibration metadata.
- **Invariant:** priors, evidence, and posteriors are all persisted.

### 9. Risk Assessment
- **In:** posteriors + current portfolio.
- **Out:** risk report: exposures, concentration, drawdown/VaR estimates, scenario stress results.
- **Invariant:** risk is computed **before** any return-seeking optimization (Principle 5).

### 10. Portfolio Optimization
- **In:** posteriors + risk report + constraints.
- **Out:** candidate target portfolio(s) with expected risk/return trade-offs.
- **Invariant:** portfolio-level reasoning precedes single-instrument reasoning (Principle 6).

### 11. Behavioral Override
- **In:** candidate portfolio + investor profile + bias rule set.
- **Out:** adjusted candidate + list of triggered overrides (e.g., overtrading guard, loss-aversion guard, recency guard).
- **Invariant:** every override is rule-based, logged, and explainable.

### 12. Decision
- **In:** adjusted candidate + full lineage.
- **Out:** final decision object produced by the **Decision Kernel** — deterministic, versioned, reproducible.
- **Invariant:** no LLM participates in this stage (SPEC-05).

### 13. Explanation
- **In:** decision object + lineage.
- **Out:** human-readable explanation: what, why, key drivers, uncertainties, triggered overrides. LLMs may phrase the explanation but only from structured facts produced upstream.
- **Invariant:** every factual claim in an explanation maps to a lineage item.

### 14. Learning
- **In:** decisions + realized outcomes.
- **Out:** calibration reports, model/feature performance, recalibration proposals.
- **Invariant:** learning changes future priors only through reviewed, versioned updates.

## Traceability

Every pipeline run has a run ID; every decision references its run ID, snapshot ID, model versions, and feature set versions. This tuple must reproduce the decision bit-for-bit.
