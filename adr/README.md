# ADR Index

## Accepted

| ADR | Title | Governs |
|---|---|---|
| [0001](0001-modular-monolith.md) | Modular Monolith with Clean Architecture | deployment/package shape |
| [0002](0002-technology-stack.md) | Technology Stack | languages, stores, ML |
| [0003](0003-llm-boundary.md) | LLM Gateway and Decision Kernel Isolation | LLM policy enforcement |
| [0004](0004-canonical-bounded-contexts.md) | Align Bounded-Context Packages with SPEC-03 | package↔context map |

## Planned (triggering sprint in parentheses)

| ADR | Title | Resolves |
|---|---|---|
| 0005 | Decision lifecycle & Risk↔Portfolio contract ruling (S2-01) | C2, C4, R7 |
| 0006 | Evidence model unification (S6-01) | C5 |
| 0007 | Knowledge Graph storage behind `GraphStore` port (S5-01) | RFC-0019 §10, R4 |
| 0008 | Feature Store storage layout (DuckDB artifacts + Postgres metadata) (Sprint 4) | RFC-0023 |
| 0009 | Authentication strategy: OAuth2/JWT first, API keys deferred (S3-01) | SPEC-08, R3 |
| 0010 | Event bus: in-process dispatch pending RFC-0022 (Sprint 9) | RFC-0022 gap |
| 0011 | Formatter gate: `ruff format` fulfills the Black requirement (Sprint 2 / C8) | C8 |
| 0012 | Notification context disposition (spec required or dropped) | C3 |

## Generation triggers

Create an ADR whenever: a new framework is introduced; a database decision is
made; a storage strategy changes; a protocol changes; a breaking architectural
decision is required.
