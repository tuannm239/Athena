# ADR Index

## Accepted

| ADR | Title | Governs |
|---|---|---|
| [0001](0001-modular-monolith.md) | Modular Monolith with Clean Architecture | deployment/package shape |
| [0002](0002-technology-stack.md) | Technology Stack | languages, stores, ML |
| [0003](0003-llm-boundary.md) | LLM Gateway and Decision Kernel Isolation | LLM policy enforcement |
| [0004](0004-canonical-bounded-contexts.md) | Align Bounded-Context Packages with SPEC-03 | package↔context map |
| [0005](0005-decision-lifecycle-and-risk-portfolio-contract.md) | Decision Lifecycle, Schema, Risk↔Portfolio Contract | C2, C4, R7 |
| [0006](0006-evidence-model.md) | Unified Evidence Model (directive ruling) | C5, R3 |
| [0007](0007-knowledge-graph-storage.md) | Knowledge Graph Storage behind GraphStore Port | RFC-0019 §10, R4 |
| [0009](0009-authentication-strategy.md) | Authentication Strategy (JWT + Argon2id) | SPEC-08, R3 |
| [0010](0010-in-process-event-bus.md) | Interim In-Process Event Bus | RFC-0022 gap |
| [0011](0011-ruff-format-as-black-gate.md) | `ruff format` Fulfills the Black Requirement | C8 |

## Planned (triggering sprint in parentheses)

| ADR | Title | Resolves |
|---|---|---|
| 0008 | Feature Store storage layout (currently: Postgres metadata + DuckDB snapshots, implemented in Sprint 4 without a dedicated ADR) | RFC-0023 |
| 0012 | Notification context disposition (spec required or dropped) | C3 |

## Generation triggers

Create an ADR whenever: a new framework is introduced; a database decision is
made; a storage strategy changes; a protocol changes; a breaking architectural
decision is required.
