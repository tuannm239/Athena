# CLAUDE.md — ATHENA Engineering Constitution (Operational Copy)

Regenerated from SPEC-00 (`spec/00-engineering-constitution.md`) per the
Executive Implementation Directive. SPEC-00 is authoritative; this file
orients agents and contributors working in this repository.

## Mission

ATHENA is a **Financial Decision Intelligence Platform**. It is **not** a
trading bot, a stock screener, a chatbot, or a signal generator. It exists to
improve investment decision quality through explainable, probabilistic, and
risk-aware reasoning.

## Product Principles (SPEC-00)

1. Decision quality over prediction accuracy.
2. Risk management over return maximization.
3. Portfolio optimization over single-asset selection.
4. Every recommendation explainable; every model backtestable; every business
   rule testable.

## LLM Policy (non-negotiable)

LLMs may summarize, explain, extract, classify, and generate reports.
LLMs must not produce BUY/SELL decisions, allocate capital, or contain
business logic. Business logic belongs exclusively to the Decision Kernel
(architecturally enforced — ADR-0003: `decision_kernel`, `risk`, `portfolio`,
`behavior` have no import path to any LLM gateway).

## Architecture

DDD + Clean + Hexagonal architecture in a modular monolith (ADR-0001), API
first, event driven (ADR-0010 interim bus). Bounded contexts map 1:1 to
packages under `backend/` (ADR-0004): `decision_kernel`, `market`, `company`,
`portfolio`, `risk`, `behavior`, `research`, `identity`, `knowledge`,
`feature_store`, `data_pipeline`, plus `shared_kernel`, `api`,
`infrastructure`. **The domain layer never depends on infrastructure**; no
SQL outside `infrastructure`; no business logic in controllers.

## Source of Truth

- `/spec` — SPEC-00…12 (constitution, product, architecture, domain, engines)
- `/rfc` — RFC-0018…0027 (probability, knowledge graph, compiler, feature
  store, data pipeline, regime/probability/risk parameters)
- `/adr` — accepted decisions (index: `adr/README.md`)
- Plans and status: `SPRINT_PLAN.md`, `TASK_PLAN.md`, `PROJECT_STATUS.md`,
  `TRACEABILITY_MATRIX.md`, `CHANGELOG.md`, `SPRINT_REPORT.md`

If specifications conflict: stop and report; never guess or invent business
rules. Behavioral feedback is advisory only — the Behavior Engine never
overrides the Decision Kernel (SPEC-12 v2).

## Technology & Gates

Python 3.13 · FastAPI · SQLAlchemy 2.x · Pydantic v2 · Alembic · PostgreSQL ·
DuckDB · Redis · Polars. Money and probabilities are Decimal, never float.

```bash
uv sync                       # install
uv run pytest --cov=backend   # tests (coverage gate ≥ 90%)
uv run ruff check . && uv run ruff format --check .   # lint + format (ADR-0011)
uv run mypy                   # strict typing (100% hints)
uv run alembic upgrade head   # forward-only migrations
```

A change is complete only when: typed, tested (unit + integration),
lint/format/mypy green, documentation and RFC traceability updated, and an
ADR exists for any architectural decision.
