# Athena — Architecture Overview

A product-level overview. The authoritative sources are `/spec`, `/rfc`,
`/adr`, and `CLAUDE.md` at the repository root.

## What Athena is

A **Financial Decision Intelligence Platform**: a decision-support system that
turns market data, fundamentals and evidence into explainable, probabilistic,
risk-aware **Decision Objects** for a human to approve. It is **not** a trading
bot, screener, chatbot, or signal generator.

## Shape

A **modular monolith** (ADR-0001) built with **DDD + Clean + Hexagonal**
architecture, API-first and event-driven. Bounded contexts map 1:1 to packages
under `backend/` (ADR-0004):

```
decision_kernel  market  company  portfolio  risk  behavior
research  identity  knowledge  feature_store  data_pipeline
+ shared_kernel  api  infrastructure
```

**Rules that hold everywhere:**
- The domain layer never depends on infrastructure.
- No SQL outside `infrastructure`; no business logic in controllers.
- Money and probabilities are `Decimal`, never `float`.

## The decision flow

```
data providers → data_pipeline (ingest→validate→normalize→quality→publish)
   → feature_store / knowledge graph
   → probability + risk + portfolio engines
   → Decision Kernel  ⇒  Decision Object (hypothesis, probability, evidence, risk)
   → human review (APPROVE / REJECT)         ← the only way anything is acted on
```

The **Decision Kernel** is the sole owner of business logic. The **Behavior
Engine** is advisory only and never overrides the kernel.

## LLM policy (ADR-0003, non-negotiable)

LLMs may summarize, explain, extract, classify and generate reports. They must
**not** produce BUY/SELL decisions, allocate capital, or hold business logic.
The `decision_kernel`, `risk`, `portfolio` and `behavior` packages have **no
import path** to any LLM gateway — this is architecturally enforced.

## Safety posture

No trade execution and no broker integration exist in the codebase. `GET
/pilot/status` reports `order_execution:false` unconditionally. Every decision
requires human approval; every change is recorded in an immutable audit trail.

## Frontend

A **Next.js (App Router) + React** app in `web/`:
- Typed API client over the SPEC-08 REST envelope, with JWT auth and
  transparent refresh-token rotation.
- **TanStack Query** for server state; **Zustand** (persisted) for UX state
  (favorites, recent, pinned, saved filters, preferences, notifications).
- **Tailwind** design system with dark/light themes; pure-SVG/CSS charts for
  cheap, SSR-safe, accessible visuals.
- Productivity layer: command palette, global search, in-app notifications,
  client-side export (CSV/Excel/PDF/JSON) and report generation.

## Platform & operations

Python 3.13 · FastAPI · SQLAlchemy 2 · Pydantic v2 · Alembic · PostgreSQL ·
DuckDB · Redis · Polars. Runs behind an Nginx TLS edge with Prometheus +
Grafana + Alertmanager. See `DEPLOYMENT.md` and `OBSERVABILITY.md`.

## Quality gates

Typed (mypy strict), tested (unit + integration, ≥90% backend coverage),
lint/format clean, forward-only migrations, and an ADR for every architectural
decision. The web app has its own typecheck, lint, unit and e2e suites.
