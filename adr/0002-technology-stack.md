# ADR-0002 — Technology Stack

- Status: Accepted
- Date: 2026-07-14
- Deciders: Architecture

## Context

The constitution fixes the stack. This ADR records the rationale so the choices are auditable.

## Decision

- **Python 3.13 + FastAPI + Pydantic v2 + SQLAlchemy 2.x** — typed, async-capable, API-first backend.
- **PostgreSQL** as system of record; **DuckDB** for immutable analytical snapshots; **Redis** for ephemeral state.
- **Polars** for feature engineering (columnar, fast, expression-based, snapshot-friendly).
- **LightGBM/XGBoost** for tabular supervised models with SHAP-style attributions (explainability requirement).
- **PyMC** for Bayesian probability updates with explicit uncertainty.
- **Optuna** for reproducible hyperparameter search.

## Consequences

- (+) Fully typed stack supports the 100% type-hints rule.
- (+) Snapshot-based DuckDB + Polars gives reproducible research and no look-ahead.
- (−) Two analytical engines (Polars/DuckDB) require clear ownership rules (SPEC-04).

## Alternatives Considered

- **pandas** — rejected in favor of Polars for performance and stricter expression semantics.
- **Deep learning first** — rejected: conflicts with explainability-over-black-box principle for decision-feeding models.
