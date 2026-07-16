# ADR-0017 — Provider Synchronization Conventions

- Status: Accepted (Engineering Authorization)
- Date: 2026-07-16
- Deciders: Engineering

## Problem

Phase 2 Module 3 connects providers to the platform. RFC-0024 fixes the
pipeline stages, quality metrics and public interfaces but not how
recurring synchronization tracks progress, how replays are versioned, or
how provider Decimals survive columnar snapshots. Authorization permits
designing these; documented here.

## Chosen conventions

1. **Sync runs are pipeline runs.** Every sync (full, incremental,
   replay) executes the unchanged RFC-0024 pipeline
   (ingest → validate → normalize → quality), so quality gates, lineage
   and quarantine apply to provider data with no special path.
2. **Watermark = latest published version.** Dataset versions encode the
   sync-window end date (`YYYY-MM-DD`). The incremental watermark is
   recovered from the latest *published* version — there is no separate
   sync-state store, so the watermark survives restarts, is transactional
   with publication, and rolling back a version automatically rewinds the
   watermark.
3. **Replay versions.** A replay re-fetches an identical window and lands
   as `{end}#rN` (N = 1, 2, …). Published history is never overwritten
   (forward-only, like migrations); replays are comparable side-by-side
   with the original run.
4. **Decimal fidelity.** Numeric provider values are stored as canonical
   strings in snapshots; floats never enter. Consumers re-hydrate with
   `Decimal(str(value))` (the connector convention since Module 2).
5. **Empty windows.** A full sync over an empty provider window is an
   error (`SyncError`); an incremental sync with nothing new is a no-op
   returning `None`, leaving the watermark untouched.
6. **Decision-pipeline bridge.** Published price data reaches the
   decision side only as fact mappings (`PublishedPriceFacts`,
   implementing the backtest `FactProvider` signature); no provider type
   crosses into guarded contexts.
7. **KG sync idempotency.** Company/sector sync materializes the
   RFC-0019 chain COMPANY→INDUSTRY→SECTOR; nodes upsert by id and edges
   are added only when no identical active edge exists, so repeated syncs
   do not advance the graph version.

## Alternatives considered

- A dedicated sync-state table (extra migration, second source of truth
  that can drift from the catalog) — rejected in favor of convention 2.
- Polars Decimal dtype in snapshots — deferred; DuckDB round-trip scale
  behavior is not guaranteed across versions, strings are.

## Consequences

- (+) Rollback and replay come for free from the dataset catalog; no new
  storage or migration.
- (−) One dataset version per sync day (fine at daily cadence; intraday
  sync would need a finer version scheme).
