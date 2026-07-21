# Universe Sync Report

Production synchronization layer: an **editable investment universe** in the
database driving two sync scopes (**market** and **universe**), all through the
existing `vnstock → Provider SDK → ProviderSyncService → Data Pipeline`
persistence. No architecture, ADR, Provider-interface, engine, or REST change.

---

## 1. vnstock APIs used

Only the installed official modules (`quote, listing, trading, company,
financial`); no scraping, no undocumented endpoints, no reverse engineering.

| Purpose | vnstock API | Persisted |
|---------|-------------|-----------|
| Historical prices (indices + universe symbols) | `Quote.history(interval="1D")` | ✅ `PRICES_DATASET` via ProviderSyncService |
| Source routing | `VNSTOCK_SOURCE` (vci/msn/kbs) | — |

Prices are the dataset wired end-to-end. The universe table only selects
*which* symbols each run covers; the fetch/persist path is unchanged.

---

## 2. Synchronization flow

```
watchlist_universe (DB, editable)         SYNC_TICKERS / --level / args
        │  active symbols                        │
        ▼                                         ▼
   athena sync {market|universe|symbol|symbols}
        │
        ▼
  MarketSyncScheduler ──▶ ProviderSyncService ──▶ Data Pipeline
        │                     (unchanged)              (unchanged)
        ▼                                                 │
   vnstock (Quote.history, VNSTOCK_SOURCE)                ▼
                                          SqlDatasetCatalog + snapshot store (SQL/DuckDB)
                                                          │
                                                          ▼
                              PublishedMarketPriceReader → VnMarketSnapshotQuery
                                                          │
                                                          ▼
                                      Market REST API → Dashboard / Market page
```

Frontend and controllers never call vnstock; they read persisted data only.

---

## 3. Commands

| Command | Scope | Cadence |
|---------|-------|---------|
| `athena sync market` | Indices: VNINDEX, VN30, HNXINDEX, UPCOMINDEX | every 5–15 min |
| `athena sync universe` | **Active** rows of `watchlist_universe` | daily / hourly |
| `athena sync universe --level REALTIME` | Only that tier (REALTIME/HIGH/NORMAL/LOW) | tier-specific |
| `athena sync symbol FPT` | One symbol | on demand |
| `athena sync symbols FPT VCB HPG` | Several symbols | on demand |
| `athena sync ensure` | Self-heal (full if no readable prices, else incremental) | boot |
| `athena sync incremental` / `full` / `replay` | Default spec / window | scheduled |

Only configured symbols are synced — `universe` never pulls the entire market.

---

## 4. Database schema — `watchlist_universe`

Editable at runtime; **never hardcoded in business logic** (the sync reads rows).

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK |
| `symbol` | varchar(32) | unique, indexed |
| `sector` | varchar(64) | BANKING, SECURITIES, … |
| `priority` | int | derived from sync_level (1..4) |
| `sync_level` | varchar(16) | REALTIME / HIGH / NORMAL / LOW (indexed) |
| `is_active` | bool | only active rows are synced (indexed) |
| `created_at` / `updated_at` | timestamptz | |

Migration `e2f3a4b5c6d7` (`0010_watchlist_universe`). Seeded **once**
(idempotent) with the default universe via `scripts/seed.py` on boot.

**Editing** (runtime): `SqlUniverseRepository.upsert(entry)` /
`set_active(symbol, active)` — add symbols, change tier, or deactivate without
touching provider code.

---

## 5. Default universe & sync tiers

**100 symbols across 11 sectors** (Banking 22, Securities 16, Real Estate 15,
Steel & Materials 8, Consumer & Retail 8, Utilities 8, Oil & Gas 7, Logistics
5, Technology 5, Aviation 4, Healthcare 2).

| Tier | Symbols | Intent |
|------|---------|--------|
| REALTIME | FPT, VCB, HPG, SSI, TCB | price sync every market run |
| HIGH | MWG, VNM, MBB, ACB, VHM | frequent price sync |
| NORMAL | all remaining seeded symbols | daily price sync |
| LOW | (reserved) profile / financials only | infrequent |

`priority` is derived from the tier so `active_symbols()` returns REALTIME
first.

---

## 6. Supported vs unsupported datasets

Per `MARKET_DATA_CAPABILITY_REPORT.md` (vnstock 4.0.4 / VCI):

- **Persisted through the pipeline:** Historical Prices (indices + universe).
- **Derived by the read model** from persisted prices: Market Snapshot,
  Breadth, Liquidity (volume), movers, Sector Summary.
- **NOT_SUPPORTED (free tier):** Foreign Trading, Order/Side Statistics
  (sponsor-only `vnstock_data`); Trading Calendar (Athena domain owns it);
  turnover-value liquidity. These return the existing empty state — never
  fabricated.

---

## 7. Incremental policy

- **Historical prices:** incremental by watermark — data already persisted is
  never re-downloaded (`sync incremental` / `universe` / `symbols`).
- **Financial statements:** at most once per day (tier LOW; not yet wired to a
  persisted dataset under the unchanged-pipeline constraint).
- **Company profile:** weekly / on demand (same).

---

## 8. Performance

- `sync market` (4 indices): ~30 s on a small instance; safe every 5–15 min.
- `sync universe` (100 symbols): serial at ~7 s/symbol on a foreign datacenter
  IP (VCI latency) ≈ 10–12 min; use `--level REALTIME`/`HIGH` for fast, frequent
  refreshes and NORMAL less often. On a 512 MB free tier, keep the frequent set
  small (indices + REALTIME) to avoid memory pressure.
- Snapshots persist to Postgres (`SNAPSHOT_BACKEND=sql`) so data survives
  restarts on ephemeral hosts.

---

## 9. Limitations

- Only **Historical Prices** flow through the pipeline; other datasets are
  derived or NOT_SUPPORTED (persisting new datasets would require changing
  ProviderSyncService / the pipeline, which is out of scope).
- Universe editing is via the repository / DB; a management REST/UI is not part
  of this change (REST contracts unchanged).
- VCI reachability/latency from non-VN datacenter IPs governs throughput.

---

## 10. Tests

- All existing tests pass.
- New: `test_universe.py` (default universe composition + tiers; SQL repo
  seed/idempotency/level-filter/edit/ordering), CLI `symbols` + `universe
  --level` + universe-from-repo (`test_market_scheduler.py`).
- Live integration guarded by `VNSTOCK_LIVE=1` (`test_vnstock_live.py`) covers
  provider connectivity + sync + persistence.

---

## 11. Acceptance

| # | Criterion | Status |
|---|-----------|--------|
| 1 | `athena sync market` works | ✅ indices → pipeline |
| 2 | `athena sync universe` works | ✅ active rows from DB |
| 3 | Universe is editable | ✅ `watchlist_universe` + repo upsert/set_active |
| 4 | Only configured symbols synced | ✅ never the whole market |
| 5 | Dashboard shows persisted live data | ✅ VN30/VNINDEX live |
| 6 | No architecture changes | ✅ additive infra + CLI |
| 7 | All existing tests pass | ✅ |
