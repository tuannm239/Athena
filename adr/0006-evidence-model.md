# ADR-0006 — Unified Evidence Model

- Status: Accepted (Executive Implementation Directive v1.0)
- Date: 2026-07-16
- Deciders: Product/Architecture (directive), Engineering
- Resolves: ARCHITECTURE_REVIEW C5, GAP R3

## Context

SPEC-03 modelled Evidence with `confidence` and encoded polarity through two
collections (`evidence` / `counter_evidence`); RFC-0018 modelled
`reliability` and `direction`. The directive rules the unified model.

## Decision

Evidence attributes: `id, source, category, reliability (0..1),
direction (SUPPORTING | CONTRADICTING | NEUTRAL), timestamp, explanation,
metadata`.

- **Direction is an explicit property** — never inferred from collection
  membership. The Decision aggregate holds a single `evidence` collection;
  `supporting`/`contradicting` are filtered views.
- `reliability` replaces the former per-evidence `confidence`;
  `Decision.confidence` continues to describe the whole decision (RFC-0018:
  probability and confidence are never merged).
- `explanation` replaces the former `description` as the human-readable text.
- SPEC-04's "counter evidence is mandatory" maps to: approval requires at
  least one SUPPORTING and one CONTRADICTING evidence item.

## Consequences

- (+) One evidence vocabulary across Decision Kernel and Probability Engine.
- (−) Breaking change to the decisions API payloads and the `evidence` table
  (migration 0005 renames kind→direction, confidence→reliability,
  description→explanation, adds metadata). Approved by the directive.
