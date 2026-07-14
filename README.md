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

## Sprint 0 Status

Sprint 0 delivers **documents only**: repository structure, specifications, architecture documents, and the engineering constitution. No business logic is implemented in Sprint 0.

## Governance

- All architectural changes require an ADR.
- Major changes wait for review before implementation.
- The LLM Policy in `CLAUDE.md` and `spec/05-llm-policy.md` is non-negotiable: LLMs never make investment decisions.
