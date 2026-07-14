# ATHENA — Financial Decision Intelligence Platform

ATHENA improves investment decision quality through explainable, probabilistic, and risk-aware analysis.

**ATHENA is not** a trading bot, a chatbot, a stock screener, or a signal generator.

## Repository Layout

| Path | Purpose |
|---|---|
| `/spec` | System specifications (source of truth for behavior) |
| `/rfc` | Requests for Comments — proposals under discussion |
| `/adr` | Architecture Decision Records — accepted decisions |
| `/backend` | Python 3.13 backend (FastAPI, SQLAlchemy 2.x, Pydantic v2) |
| `/frontend` | User interface |
| `/infrastructure` | IaC, deployment, environments |
| `/tests` | Unit and integration tests |
| `/scripts` | Developer and operational tooling |

## Getting Started

1. Read `CLAUDE.md` (Engineering Constitution) — it governs all work in this repo.
2. Read every file in `/spec`.
3. Review accepted decisions in `/adr`.
4. Propose changes via `/rfc` before implementation.

## Development

Requires [uv](https://docs.astral.sh/uv/) and Python 3.13.

```bash
uv sync                                                  # install dependencies
uv run pytest                                            # unit + integration tests
uv run ruff check .                                      # lint
uv run mypy                                              # strict type checking
uv run uvicorn api.main:app --app-dir backend --reload   # API → http://localhost:8000/docs
docker compose up --build                                # full stack: API + PostgreSQL + Redis
```

Database migrations use Alembic (`uv run alembic upgrade head`); the migration environment lives in `backend/infrastructure/alembic`.

## Sprint 0 Status

Sprint 0 (bootstrap, per `IMPLEMENTATION_PLAN.md`) is **complete**: repository structure, specifications, build configuration (uv + pyproject), FastAPI application with placeholder routes returning HTTP 501, Docker, Alembic, and the test/lint/type-check toolchain. No business logic beyond the initial domain models is implemented.

## Governance

- All architectural changes require an ADR.
- Major changes wait for review before implementation.
- The LLM Policy in `CLAUDE.md` and `spec/05-llm-policy.md` is non-negotiable: LLMs never make investment decisions.
