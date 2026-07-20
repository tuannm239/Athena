# Market Sync Runbook

Operational guide for synchronising Vietnamese market data into Athena so the
dashboard and Market page show **real** data. The scheduler orchestrates the
existing `ProviderSyncService` (vnstock provider → Data Pipeline); it never
fetches data itself.

## Commands

```bash
athena sync full          # full window resync (SYNC_LOOKBACK_DAYS back, default 365d)
athena sync incremental   # only days newer than the last published watermark
athena sync replay --start 2026-01-01 --end 2026-01-31
athena sync status        # JSON health: watermark, provider health, ticker count
```

`athena` resolves to the CLI in every environment:

| Where | Invocation |
|---|---|
| Local dev | `uv run athena sync full` |
| Inside the container / Render Shell | `python -m data_pipeline.cli sync full` (or `sh scripts/athena sync full`) |
| Cron / scheduled | `scripts/sync_entrypoint.sh` (picks the action from `SYNC_MODE`) |

Every run prints one JSON line (machine-readable) plus structured progress logs.
Exit code is `0` on success (or "already up to date"), `1` on failure.

## Configuration (environment)

| Var | Default | Meaning |
|---|---|---|
| `SYNC_MODE` | `INCREMENTAL` | entrypoint action: `FULL` / `INCREMENTAL` / `MANUAL` |
| `SYNC_TICKERS` | `VNINDEX,VN30,HOSE,HNX,UPCOM` | sync spec (see below) |
| `SYNC_LOOKBACK_DAYS` | `365` | full/initial window length |
| `SYNC_MAX_RETRIES` | `3` | whole-run retry attempts (exp. backoff) |
| `DATABASE_URL`, `DUCKDB_DIR` | (standard) | dataset catalog + snapshot store |

**Ticker spec** — comma list of:
- **index codes** (`VNINDEX`, `VN30`, `HNXINDEX`, `HNX30`, `UPCOMINDEX`) — kept as-is;
- **exchange codes** (`HOSE`, `HNX`, `UPCOM`) — expanded to a curated set of that
  exchange's liquid tickers (static reference, `data_pipeline/tickers.py`);
- **any other token** — used literally, so custom lists work, e.g.
  `SYNC_TICKERS="FPT,HPG,VNINDEX"`.

`SYNC_MODE=MANUAL` makes the entrypoint a no-op (operators run `athena sync …` by hand).

## Fresh deployment → real dashboard data

```
athena sync full   →   publishes the "prices" dataset   →   GET /market/vn/snapshot
                                                            serves real indices/movers/
                                                            breadth/liquidity  →  dashboard
```

1. Deploy the backend (migrations create the `datasets` table automatically).
2. Run a first full sync **co-located with the API** (see the storage note below),
   on a network that can reach the VN data hosts:
   ```bash
   # Render → your athena-api service → Shell
   python -m data_pipeline.cli sync full
   ```
3. Confirm it published: `athena sync status` → `has_published_data: true`, and
   `curl https://<api>/health` is ok.
4. Reload the app — the Market page and dashboard widgets (VNINDEX, VN30, Top
   Gainers/Losers, Breadth, Liquidity) now show real data, no sample.

Until a sync has published, the endpoint returns an honest **empty state** (never
sample values).

## No Shell? (Render free tier) — sync on startup

The free tier has no Shell, so trigger the sync **from inside the API container**
by environment variable (already in `render.yaml`):

| Var | Value | Effect |
|---|---|---|
| `SYNC_ON_START` | `true` | run one market sync in the background on every boot |
| `SYNC_ON_START_MODE` | `incremental` (or `full`) | which sync to run |
| `SYNC_LOOKBACK_DAYS` | `10` | keep small so a fresh ephemeral disk syncs fast |

On boot, `scripts/start.sh` launches the sync in the **background** (it never
delays the port bind / health check) and it writes to the same filesystem the
API reads. The dashboard populates a short while after the service goes live,
and — because the free disk is ephemeral — it repopulates automatically on each
restart/redeploy. Set the vars in the Render dashboard (or keep the defaults in
`render.yaml`) and redeploy; no Shell required.

## ⚠️ Storage / co-location note (important)

The Data Pipeline's snapshot store (`DuckDbSnapshotStore`) writes DuckDB files to
`DUCKDB_DIR` on the **local filesystem**; the dataset catalog lives in Postgres
(shared). Therefore:

- **Run the sync in the same service/filesystem as the API** so the API can read
  the snapshot it wrote. A *separate* container (e.g. a standalone cron worker)
  writes DuckDB files the API cannot see — the catalog row would point at a
  snapshot missing on the API host.
- On a **free Render web service the disk is ephemeral** (no persistent disk):
  data survives until the next restart/redeploy; **re-run `athena sync full`
  after a restart**. For durability, attach a persistent disk at `DUCKDB_DIR`
  (paid plan) on the API service.
- A fully decoupled scheduler (separate worker on its own schedule) requires a
  **shared snapshot store** (object storage / Postgres-backed) — a Data Pipeline
  change, intentionally out of scope here.

## Scheduling options

- **Manual / on-demand:** run `athena sync full` (first load) then
  `athena sync incremental` when you want fresh data.
- **Cron (co-located):** point cron/systemd-timer at `scripts/sync_entrypoint.sh`
  with `SYNC_MODE=INCREMENTAL`, running on the API host after market close
  (~15:15 ICT ⇒ `15 8 * * 1-5` UTC):
  ```cron
  15 8 * * 1-5  SYNC_MODE=INCREMENTAL /app/scripts/sync_entrypoint.sh >> /var/log/athena-sync.log 2>&1
  ```
- **Render Cron Job:** only correct once a shared snapshot store is configured
  (see the storage note); otherwise prefer the co-located cron above.

## Troubleshooting

| Symptom (from `athena sync …` JSON / logs) | Cause | Action |
|---|---|---|
| `detail: "failed after N attempts: … no such table: datasets"` | migrations not applied | run `alembic upgrade head` (the deploy entrypoint does this) |
| `detail: "… returned no prices …"` / provider errors | VN data host unreachable (blocked/geo) or bad ticker | run on an open-internet host; verify `SYNC_TICKERS` |
| Market page still empty after a sync elsewhere | sync ran in a different container/FS | run the sync **on the API host** (storage note) |
| `provider_healthy: false` in status | recent provider failures | check network; re-run; inspect logs |
```
