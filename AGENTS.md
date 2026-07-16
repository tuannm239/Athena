# AGENTS.md — Operating Guide for AI Agents

Read before any task. `CLAUDE.md` carries the constitution summary; this file
carries the working protocol.

## Read order (before writing code)

1. `CLAUDE.md`, then `spec/00…12`, then every `/rfc`, then `adr/README.md`.
2. `SPRINT_PLAN.md` (authoritative sprint sequence) and `SPRINT_REPORT.md`
   (latest state); `IMPLEMENTATION_BACKLOG.md` for open items.

## Rules

- Specifications are the single source of truth. Conflict ⇒ stop and report.
- Never invent business rules; parameters come from RFCs (0025/0026/0027).
- Do not change module boundaries, public contracts, or RFC semantics
  without an approved ADR.
- Direction of evidence is explicit (ADR-0006) — never inferred.
- Domain imports nothing from infrastructure/FastAPI/SQLAlchemy.

## Workflow per module

Read RFCs → design → implement → unit tests → integration tests →
`ruff check` + `ruff format --check` → `mypy` → `pytest --cov` (≥ 90%) →
update docs (README, CHANGELOG, TRACEABILITY_MATRIX, SPRINT_REPORT) →
Conventional Commit (one module, one commit) → push.

## Environment notes

- `uv` manages the environment (Python 3.13). Local integration tests run on
  SQLite; CI runs PostgreSQL 16 + Redis 7 services and `alembic upgrade head`.
- Docker daemon is typically unavailable in agent sandboxes — do not block on
  `docker compose`; CI covers service-backed tests.
- Redis-dependent tests skip locally by design.
