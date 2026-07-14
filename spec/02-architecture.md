# SPEC-02 — Architecture

Status: Draft (Sprint 0)
Owner: Architecture
Last updated: 2026-07-14

## 1. Style

- **Clean Architecture** with strict dependency rule: `domain ← application ← interface/infrastructure`.
- **Domain-Driven Design** with explicit bounded contexts and a published ubiquitous language per context.
- **Modular monolith first.** Contexts are packaged as independent modules with enforced import boundaries; extraction to services is a later, ADR-gated decision.

## 2. Layering (per bounded context)

```text
backend/<context>/
  domain/          # entities, value objects, domain services, domain events — no framework imports
  application/     # use cases, ports (interfaces), DTOs — no SQL, no HTTP
  infrastructure/  # SQLAlchemy repositories, external adapters, message publishers
  api/             # FastAPI routers (controllers) — no business logic
```

Rules (enforced by lint/import checks, see SPEC-06):

- `domain` imports nothing outside the standard library and the shared kernel.
- `application` imports `domain` only.
- `infrastructure` implements `application` ports.
- `api` calls `application` use cases only; controllers contain no business logic.
- No SQL outside `infrastructure`.

## 3. Bounded Contexts (initial map)

| Context | Responsibility | Pipeline stages |
|---|---|---|
| `market_data` | Ingestion, normalization, data snapshots | Data, Normalization |
| `features` | Feature engineering, feature store | Feature Engineering |
| `knowledge` | Knowledge graph of companies/sectors/factors/events | Knowledge Graph |
| `regime` | Market regime detection | Market Regime |
| `analysis` | Sector and company analysis, probability updates | Sector/Company Analysis, Probability Update |
| `risk` | Risk assessment (portfolio-first) | Risk Assessment |
| `portfolio` | Optimization under constraints | Portfolio Optimization |
| `behavior` | Behavioral override rules | Behavioral Override |
| `decision_kernel` | Final decision assembly — deterministic, non-LLM | Decision |
| `explanation` | Human-readable explanations, audit trail | Explanation |
| `learning` | Outcome tracking, recalibration | Learning |

Shared kernel: identifiers, money/quantity value objects, time/calendar, probability types.

## 4. Context Communication

- Within the monolith: application-layer ports and domain events (in-process event bus).
- Contexts never reach into another context's domain model; they consume published contracts (DTOs/events) only.
- All cross-context contracts are versioned and documented in `/spec`.

## 5. Data Architecture

| Store | Role |
|---|---|
| PostgreSQL | System of record: reference data, decisions, audit trail, portfolios |
| DuckDB | Analytical workloads over columnar snapshots; reproducible research |
| Redis | Caching, short-lived computation state, idempotency keys |
| Polars | In-process dataframe engine for feature engineering and analytics |

Reproducibility rule: every pipeline run references an immutable data snapshot ID.

## 6. ML Architecture

- LightGBM / XGBoost for supervised signals feeding *probabilistic assessments* (never direct decisions).
- PyMC for Bayesian probability updates and uncertainty quantification.
- Optuna for hyperparameter search, tracked and reproducible.
- Every model registered with: training snapshot ID, feature set version, evaluation report, and an explainability artifact (e.g., SHAP summary).

## 7. LLM Boundary

LLMs sit **outside** the Decision Kernel behind a single gateway module (`explanation`/documentation surfaces only). See SPEC-05. Architectural enforcement: the `decision_kernel` module has no dependency path to any LLM client.

## 8. API

- FastAPI, versioned under `/api/v1`.
- OpenAPI schema is a published contract; UI is built against it (API-first).
- Pydantic v2 models at the boundary; domain objects never serialized directly.

## 9. Cross-Cutting

- 100% type hints; mypy strict.
- Structured logging with decision-trace correlation IDs.
- Every decision output is persisted with full input lineage (auditability).
