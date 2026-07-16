# Changelog

All notable changes to ATHENA. Format follows Keep a Changelog; versions are
pre-release sprints until Sprint 15 (production readiness).

## [Unreleased]

## Sprint 4 — Feature Store & Data Pipeline (2026-07-15)

### Added
- Feature Store context (RFC-0023): `FeatureMetadata` (semver-validated),
  lifecycle Draft→Validated→Published→Deprecated→Archived with publication
  gates (docs, tests, benchmark, owner), `FeatureRegistry` port + SQL
  implementation enforcing published-version immutability, read APIs
  (Get/GetVersion/List/Search), idempotent SPEC-06 factor catalogue seeding
  (26 factors across 7 categories).
- Data Pipeline context (RFC-0024): deterministic stages
  ingest→validate→normalize→quality with quarantine (nulls, duplicate keys,
  future timestamps), quality reports (completeness/accuracy/freshness/
  consistency/uniqueness), DP001–DP005 error codes, record-level lineage,
  `DatasetCatalog` port + SQL implementation, public interfaces RunPipeline/
  ValidateDataset/PublishDataset/RollbackDataset/GenerateQualityReport;
  datasets persist as immutable DuckDB snapshots; failed datasets never
  publish.
- Migration 0003 (`feature_definitions`, `datasets`).

## Sprint 3 — Application layer, auth & REST API (2026-07-15)

### Added
- Application layer: identity use cases (RegisterUser, AuthenticateUser),
  DecisionUseCases (create/get/list/update with lifecycle transitions),
  PortfolioUseCases; hexagonal ports (PasswordHasher, CredentialStore,
  TokenService, EventPublisher).
- JWT authentication (ADR-0009): Argon2id hashing, access/refresh pairs,
  `/api/v1/auth/register|login|refresh`; `password_hash` migration 0002.
- SPEC-08 REST resources: decisions (GET list/id, POST, PATCH), portfolios
  (GET list/id/positions, POST) — protected by bearer auth; standard response
  envelope with request-id middleware; full error-code mapping
  (400/401/404/409/422/501).
- SPEC-08 path alignment: companies, market, backtests routers expose spec
  paths returning 501 until their engines land; non-spec placeholder routers
  removed.
- In-process event bus (ADR-0010); pagination support in repositories.
- CTO audit reports: PROJECT_STATUS, GAP_ANALYSIS, IMPLEMENTATION_BACKLOG,
  ARCHITECTURE_REVIEW v2, CODE_QUALITY_REPORT.

### Changed
- `pyproject`: added `pyjwt`, `argon2-cffi`; B008 lint exemption for FastAPI
  dependency idiom.

## Sprint 2 — Persistence (2026-07-15)

### Added
- SQLAlchemy ORM models for SPEC-07 core tables (`users`, `portfolios`,
  `positions`, `decisions`, `evidence`, `factors`) plus immutable `audit_log`.
- Initial Alembic migration `ec77f528e384`; env wired to `Base.metadata`.
- Repository implementations: `SqlDecisionRepository`, `SqlPortfolioRepository`,
  `SqlUserRepository` (with `UserRepository` interface in the identity domain);
  every Decision/Portfolio mutation writes an audit record.
- `DuckDbSnapshotStore` — immutable, versioned analytical snapshots.
- `RedisCache` — cache + idempotency keys (ephemeral state only).
- Typed `Settings` config; CI workflow (ruff, ruff format, mypy, migrations,
  pytest with PostgreSQL/Redis services, coverage gate ≥ 90%).
- ADR-0005 (decision lifecycle/schema, Risk↔Portfolio contract),
  ADR-0011 (`ruff format` as the Black gate).

### Changed
- Codebase formatted with `ruff format` (style commit `f2f3efc`).
- `pyproject`: added `pyarrow`, `pytest-cov`.

## Sprint 1 — Domain model (2026-07-15, `a68ae33`)
- Canonical domain layer per SPEC-03/04/05/10/11/12; ADR-0004.
- Canonical specification set SPEC-00…12 adopted (`34c5b51`); Phase 1
  architecture review (`6eaefb4`); Phase 2 roadmap (`8bc4eb9`).

## Sprint 0 — Bootstrap (2026-07-14, `49ed73a`)
- Repository structure, uv/pyproject, FastAPI 501 skeleton, Docker,
  Alembic scaffold, pytest/ruff/mypy toolchain.
