# Scheduler Report — market synchronisation

**Date:** 2026-07-20 · **Status:** ✅ production-ready, all tests pass.

## 1. What was built

A production-ready scheduler that runs Vietnamese market synchronisation through
the **existing** `ProviderSyncService` — it never fetches data itself.

```
athena sync {full|incremental|replay|status}
        │
        ▼
MarketSyncScheduler  (retry · logging · progress · health)
        │  delegates every fetch to
        ▼
ProviderSyncService  ──▶  vnstock PriceProvider  ──▶  Data Pipeline (published "prices")
                                                          │
                                                          ▼
                              GET /market/vn/snapshot ──▶ dashboard shows real data
```

## 2. Files

| File | Role |
|---|---|
| `backend/data_pipeline/scheduler.py` | `MarketSyncScheduler` + `SyncOutcome` (orchestration, retry, logging, progress, health) |
| `backend/data_pipeline/tickers.py` | ticker-universe resolution (static reference; index/exchange/custom) |
| `backend/data_pipeline/cli.py` | `athena` CLI (`sync full/incremental/replay/status`) |
| `scripts/athena` | CLI shim for any environment |
| `scripts/sync_entrypoint.sh` | Docker/cron one-shot entrypoint (action from `SYNC_MODE`) |
| `pyproject.toml` | `[project.scripts] athena` console entry |
| `tests/unit/test_market_scheduler.py` | 14 tests (ops, retry, resolution, CLI) |
| `SYNC_RUNBOOK.md` | operator runbook |

## 3. Requirements → evidence

| # | Requirement | Result |
|---|---|---|
| 1 | Do not modify VnstockProvider | ✅ untouched |
| 2 | Do not modify the Market API | ✅ untouched |
| 3 | Use the existing ProviderSyncService only | ✅ scheduler calls `full_sync_prices` / `incremental_sync_prices` / `replay_prices` / `watermark`; no direct fetch |
| 4 | Production-ready scheduler | ✅ full, incremental, manual (`SYNC_MODE=MANUAL`), replay, retry, logging, progress reporting |
| — | CLI command | ✅ `athena sync …` (argparse) |
| — | Docker entrypoint | ✅ `scripts/sync_entrypoint.sh` (in the image; `python` = venv) |
| — | Cron-compatible scheduler | ✅ one-shot, deterministic exit code; crontab example in the runbook |
| — | Health reporting | ✅ `athena sync status` → watermark, provider health, config; JSON |
| — | `SYNC_MODE` FULL/INCREMENTAL/MANUAL | ✅ honoured by the entrypoint |
| — | Ticker list VNINDEX/VN30/HOSE/HNX/UPCOM + custom | ✅ `SYNC_TICKERS`; indices kept, exchanges expanded, custom literal |
| — | Never fetch directly; always ProviderSyncService | ✅ verified — the scheduler holds a `PriceProvider` only to hand to `ProviderSyncService` |
| — | Operational commands | ✅ `athena sync full/incremental/replay/status` |
| 9/10 | `SYNC_RUNBOOK.md`, `SCHEDULER_REPORT.md` | ✅ generated |

Also: **no controller changes, no business-logic changes** (the scheduler is
operational orchestration; it adds new files under `data_pipeline/` and does not
touch the pipeline's domain, the API, or any engine).

## 4. Capabilities in detail

- **Full sync** — resyncs `[today − SYNC_LOOKBACK_DAYS, today]` via `full_sync_prices`.
- **Incremental** — `incremental_sync_prices` from the last published watermark;
  reports "already up to date" (no publish) when nothing is new.
- **Replay** — `replay_prices` re-fetches a window as a new, comparable version.
- **Retry** — whole-run retry with exponential backoff (`SYNC_MAX_RETRIES`, default 3),
  on top of the provider's own per-call resilience.
- **Logging** — structured JSON logs at each stage (`sync.<mode>.start/published/
  up_to_date/attempt_failed/failed`).
- **Progress reporting** — every run returns a `SyncOutcome` (mode, ok, published,
  version, row_count, attempts, duration) emitted as one JSON line.
- **Health** — `status` returns watermark, `has_published_data`, ticker count,
  and provider health.

## 5. Tests

```
tests/unit/test_market_scheduler.py ..............   [14 passed]
Full suite: 439 passed, 3 skipped (0 failed)   coverage 95% (gate ≥ 90%)
  scheduler.py 99% · tickers.py 96% · cli.py 78% (uncovered = real DB/registry
  wiring in build_scheduler, exercised by the offline `athena sync status` smoke)
ruff ✓  ruff format ✓  mypy strict ✓
```

Tests cover: full/incremental/replay/status, retry-then-succeed and
retry-exhausted, JSON-serialisable outcome, ticker resolution (indices kept,
exchanges expanded, de-dup, custom literal), and CLI dispatch/exit codes — all
against an in-memory pipeline and a deterministic provider (no network).

Verified offline against a real SQLite catalog:
`athena sync status` → `{"dataset":"prices","watermark":null,
"has_published_data":false,"tickers_configured":36,"provider_healthy":true,…}`
(36 = indices + curated HOSE/HNX/UPCOM constituents).

## 6. Acceptance path (fresh deployment)

`athena sync full` → publishes the `prices` dataset → `/market/vn/snapshot`
serves real indices/movers/breadth/liquidity → **dashboard shows real Vietnamese
market data, no sample.** Two operational conditions (detailed in the runbook):

1. Run it where **outbound access to VN data hosts** exists (Render has it; this
   build sandbox does not — its egress proxy blocks them, so live fetching is
   validated out-of-sandbox).
2. Run it **co-located with the API** (shared filesystem for the DuckDB snapshot
   store); on the free tier the disk is ephemeral, so re-run after a restart or
   attach a persistent disk.

## 7. Constitution compliance

No provider/API/business-logic changes; the scheduler depends only on
`ProviderSyncService` + a `PriceProvider` port; money stays `Decimal`; the
scheduler never fetches data itself.
