# Changelog

All notable changes to ATHENA. Format follows Keep a Changelog; versions are
pre-release sprints until Sprint 15 (production readiness).

## [Unreleased]

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
