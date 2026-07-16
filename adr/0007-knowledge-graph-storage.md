# ADR-0007 — Knowledge Graph Storage: PostgreSQL Adjacency behind a GraphStore Port

- Status: Accepted
- Date: 2026-07-15
- Deciders: Engineering
- Resolves: RFC-0019 §2/§10 (storage independence), GAP R4

## Context

RFC-0019 requires the Knowledge Graph to be independent from storage
technology, with versioned, auditable, reproducible updates and historically
queryable relationships. A dedicated graph database adds operational cost the
modular monolith (ADR-0001) does not yet justify.

## Decision

1. Graph reasoning operates on an in-memory `GraphSnapshot` value object;
   traversal algorithms never touch storage.
2. Persistence hides behind a `GraphStore` port. First adapter: PostgreSQL
   adjacency tables (`kg_nodes`, `kg_edges`) where edges carry
   `created_version` / `removed_version` — mutations only append or close
   version ranges, so any historical graph version is reconstructable.
3. Every edge carries provenance (RFC-0019 §5); edge type-pairs are validated
   against the RFC-0019 §4 relationship catalogue in the domain layer.
4. Cycles are rejected unless the mutation explicitly allows them
   (RFC-0019 §5: "cycles are allowed only when explicitly defined").

## Consequences

- (+) Deterministic, versioned, storage-agnostic; swapping in a graph
  database later means one new adapter.
- (+) The RFC-0019 §3 node list omits Evidence while §4 uses it as a target;
  an `EVIDENCE` node type is added and recorded here as the ruling.
- (−) Very large graphs will eventually outgrow in-memory snapshots; revisit
  when node counts warrant it.
