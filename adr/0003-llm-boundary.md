# ADR-0003 — LLM Gateway and Decision Kernel Isolation

- Status: Accepted
- Date: 2026-07-14
- Deciders: Architecture

## Context

Core Principle 7: LLMs never make investment decisions. Policy alone is insufficient; the architecture must make violations structurally difficult.

## Decision

1. A single **LLM Gateway** module is the only permitted import site for LLM clients.
2. `decision_kernel`, `risk`, `portfolio`, and `behavior` have no import path to the gateway; CI import-linting fails the build on violation.
3. All LLM-derived data entering the pipeline is lineage-tagged (`source: llm`, model ID, prompt version).
4. Explanations are generated from structured decision facts; claims that cannot be mapped to lineage fail validation.

## Consequences

- (+) The constitution's LLM policy is machine-enforced, not just documented.
- (+) Full auditability of LLM influence on any artifact.
- (−) Some friction when adding new LLM-assisted features; accepted by design.

## Alternatives Considered

- **Policy-only (code review)** — rejected: too easy to violate accidentally.
- **Separate LLM microservice** — deferred; the gateway module achieves isolation within the modular monolith (ADR-0001).
