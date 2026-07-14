# SPEC-04 — Data

Status: Draft (Sprint 0)
Owner: Architecture
Last updated: 2026-07-14

## 1. Stores and Responsibilities

| Store | Responsibility | Notes |
|---|---|---|
| PostgreSQL | System of record | Reference data, portfolios, decisions, audit trail, model registry |
| DuckDB | Analytical store | Columnar snapshots, research, backtests; files are immutable per snapshot |
| Redis | Ephemeral state | Caches, rate limits, idempotency keys, short-lived pipeline state |

## 2. Snapshots

- A **snapshot** is an immutable, content-addressed capture of normalized data as of a point in time.
- All feature engineering, analysis, and decisions reference a snapshot ID.
- Snapshots are never mutated; corrections produce a new snapshot with a lineage link.

## 3. Lineage

Minimum lineage chain persisted for every decision:

```text
raw records → normalized records → snapshot ID → feature set version
→ model versions → assessments → risk report → candidate portfolio
→ overrides → decision ID → explanation ID
```

## 4. Schema Governance

- SQLAlchemy 2.x declarative models; migrations via Alembic.
- Schema changes require an RFC if they alter a published contract.
- No SQL outside the infrastructure layer; repositories expose typed methods.

## 5. Data Quality Gates

Each ingestion batch must pass, before entering Normalization:

1. Schema validation (Pydantic v2 at the boundary).
2. Freshness checks against source SLA.
3. Duplicate/gap detection on time series.
4. Outlier flagging (flag, never silently drop).

Failures quarantine the batch and raise an operational event; partial data never silently enters the pipeline.

## 6. Retention & Audit

- Decisions, explanations, and their full lineage: retained indefinitely (auditability is a core quality attribute).
- Raw data retention per-source, documented in ingestion specs (post-Sprint 0).
