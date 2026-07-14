# ADR-0001 — Modular Monolith with Clean Architecture

- Status: Accepted
- Date: 2026-07-14
- Deciders: Architecture

## Context

ATHENA has many bounded contexts (SPEC-02, Bounded Contexts) but a small team and an evolving domain. Microservices would impose operational cost and slow domain iteration; a classic layered monolith would erode boundaries.

## Decision

We will build a **modular monolith**: one deployable, with bounded contexts as independent Python packages, Clean Architecture layering inside each context, and import-boundary checks enforced in CI. Service extraction is deferred and requires a future ADR.

## Consequences

- (+) Fast iteration, single deployment, in-process events, easy refactoring across contexts while the domain model matures.
- (+) Boundaries are still enforced, so later extraction remains feasible.
- (−) Requires discipline and tooling (import linting) to prevent boundary erosion.
- (−) Single runtime: a heavy analytical workload can affect API latency; mitigated by running pipeline jobs out-of-process from the API worker.

## Alternatives Considered

- **Microservices from day one** — rejected: operational overhead, premature contract freezing.
- **Unstructured monolith** — rejected: violates DDD/Clean Architecture principles and would make the LLM boundary unenforceable.
