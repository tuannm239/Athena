# ADR-0005 — Decision Lifecycle, Decision Schema, and Risk↔Portfolio Contract

- Status: Accepted (recommendation adopted with Phase-2 plan approval; reversible by ruling)
- Date: 2026-07-15
- Deciders: Architecture
- Resolves: ARCHITECTURE_REVIEW.md C2, C4, R7

## Context

SPEC-03 and SPEC-04 state different Decision lifecycles (C2), three documents
state different Decision field sets (C4), and SPEC-10/SPEC-11 sequence diagrams
call each other (potential cycle, R7).

## Decision

1. **Lifecycle (C2):** SPEC-03 governs the aggregate:
   `Draft → UnderReview → Approved | Rejected → Archived`. SPEC-04's
   `Evaluated`/`Reviewed` are interpreted as *kernel pipeline stages* (steps
   1–11 of SPEC-04 §Decision Pipeline), not persisted aggregate states.
2. **Schema (C4):** the persisted Decision carries the union of SPEC-03 and
   SPEC-04 fields (as implemented in `decision_kernel.domain.decision`).
   RFC-0020's field list (with `compiler_version`) describes the *compiled*
   Decision emitted by the Decision Compiler and will be layered on top in
   Sprint 8 without removing aggregate fields.
3. **Risk↔Portfolio (R7):** the Risk context depends only on the
   **PortfolioState contract** (a published DTO of the portfolio context),
   never on the Portfolio Engine service; the Portfolio Engine calls the Risk
   Engine service. This removes the module-level cycle while preserving both
   sequence diagrams.

## Consequences

- (+) `decisions` table can be frozen for the Sprint-2 migration.
- (+) No import cycle; import-linting can enforce the direction.
- (−) If a future ruling prefers SPEC-04 states, a data migration will be
  required (forward-only per SPEC-07).
