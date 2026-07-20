# VNSTOCK Integration Report

Integration of the **`vnstock 4.0.4`** library as Athena's single Vietnam
market-data provider, inside the existing Provider SDK and ingestion pipeline.
No architecture, ADR, REST contract, engine, or frontend redesign — additive
work in the Provider layer + the operational CLI only.

---

## 1. vnstock APIs used (official modules only)

Entry point: `Vnstock().stock(symbol, source=<VNSTOCK_SOURCE>)` (equivalently
`vnstock.api.{quote,listing,trading,company,financial}`). No scraping, no
undocumented HTTP endpoints, no broker reverse-engineering.

| vnstock API | Used for |
|-------------|----------|
| `Quote.history(interval="1D")` | Historical OHLCV incl. indices (VNINDEX/VN30/HNXINDEX/UPCOMINDEX) |
| `Listing.all_symbols()` | Listed symbols |
| `Listing.symbols_by_industries()` | Industry (ICB) classification |
| `Listing.symbols_by_group("VN30")` | Index constituents |
| `Listing.market_status()` | Session status (open/closed + hours) |
| `Trading.price_board(symbols_list=[...])` | Real-time board for a supplied symbol list |
| `Company.overview()` | Company information |
| `Company.trading_stats()` | Per-symbol trading statistics |
| `Financial.balance_sheet()/income_statement()/cash_flow()/ratio()` | Financial statements |

The source is **never hardcoded** — it comes from `settings.vnstock_source`
(`VNSTOCK_SOURCE`, default `vci`), validated against the installed vnstock's
supported sources by `providers.connectors.vnstock_source.resolve_source`.

---

## 2. Supported datasets (`athena provider datasets`)

Support is discovered from the installed vnstock package layout on disk (does
the source define the backing method?), so it is version-accurate and never
fabricated. For `VCI` on vnstock 4.0.4 — **8 SUPPORTED / 5 NOT_SUPPORTED**:

| Dataset | Support | vnstock API | Athena model |
|---------|:-------:|-------------|--------------|
| Historical Prices | ✅ | `Quote.history()` | `PriceBar` → `PRICES_DATASET` |
| Market Status | ✅ | `Listing.market_status()` | market read model (session) |
| Price Board | ✅ | `Trading.price_board()` | adapter records |
| Trading Statistics | ✅ | `Company.trading_stats()` | adapter records |
| Company Information | ✅ | `Company.overview()` | `CompanyProfile` |
| Industry Classification | ✅ | `Listing.symbols_by_industries()` | `SectorMapping` |
| Financial Statements | ✅ | `Financial.*` | `FundamentalRecord` |
| Listed Symbols | ✅ | `Listing.all_symbols()` | `SymbolInfo` |

## 3. Unsupported datasets → `NOT_SUPPORTED` (never fabricated)

| Dataset | Why NOT_SUPPORTED |
|---------|-------------------|
| Foreign Trading | `Trading.foreign_trade` is an API stub that raises `NotImplementedError` on VCI (sponsor-only `vnstock_data`). |
| Order Statistics | `Trading.order_stats` — sponsor-only; not implemented for VCI. |
| Side Statistics | `Trading.side_stats` — sponsor-only; not implemented for VCI. |
| Market Snapshot | Not a vnstock endpoint — **derived** by Athena's read model from persisted prices. |
| Trading Calendar | vnstock has no exchange holiday calendar (`market_status` is session-only; `events_calendar` is corporate events). **Athena owns it** in `market/domain/vietnam.py::TradingCalendar`. |

The catalog is the single source of truth (`vnstock_datasets.py`); a
`NOT_SUPPORTED` dataset never claims a working API or persistence target.

---

## 4. Athena model mapping

```
vnstock (VCI)
  → RealVnstockClient (records; pandas stays inside the seam)
  → VnstockProvider (maps to SDK DTOs: PriceBar, FundamentalRecord,
                     SectorMapping, SymbolInfo, CompanyProfile — Decimal only)
  → Resilient* wrappers (retry / rate-limit / TTL cache / health)
  → ProviderSyncService  (UNCHANGED)
  → Data Pipeline        (UNCHANGED — SqlDatasetCatalog + DuckDbSnapshotStore)
  → PRICES_DATASET (persisted)
  → PublishedMarketPriceReader → VnMarketSnapshotQuery (read model)
  → Market API (existing REST contract) → Dashboard / Market pages
```

**Only Historical Prices is wired end-to-end** through the existing
ProviderSync + Data Pipeline, because persisting a *new* dataset would require
changing `ProviderSyncService` / the pipeline, which the directive forbids. The
dashboard's Market Snapshot, breadth, movers, liquidity and sector summary are
**derived by the existing read model** from those persisted prices — no new
persisted dataset and no new endpoint. The other supported datasets (price
board, trading stats, market status, company, industry, financials, symbols)
are available as adapter/library capabilities and catalogued, but are not given
a new persistence path under the unchanged-pipeline constraint.

---

## 5. Synchronization strategy (`athena sync`)

All scopes run through the **same unchanged** `MarketSyncScheduler →
ProviderSyncService → Data Pipeline`; a scope only selects *which* tickers a run
covers. Incremental by watermark — data already persisted is not re-downloaded.

| Command | Scope | Cadence |
|---------|-------|---------|
| `athena sync market` | Indices only (`VNINDEX, VN30, HNXINDEX, UPCOMINDEX`) — refreshes the derived snapshot/breadth/sector fast | every 5–15 min |
| `athena sync universe` | The **configured** symbol universe (curated ~34; override `SYNC_UNIVERSE`). Never "every listed company". | daily / hourly |
| `athena sync symbol FPT` | A single explicit symbol | on demand |
| `athena sync incremental` | Full default spec, newer-than-watermark | scheduled |
| `athena sync full` | Full window backfill (`SYNC_LOOKBACK_DAYS`) | occasional |
| `athena sync replay --start --end` | Bounded window | ad-hoc |

New symbols are added by configuration (`SYNC_UNIVERSE` / `--tickers` /
`sync symbol`) — **no provider code change** (`tickers.py` scope helpers).

**Incremental cadence (design):** historical prices — only newer than the
watermark; financial statements — at most daily; company profile — weekly / on
demand; market snapshot — derived, so it refreshes with `sync market`.

---

## 6. Configuration

| Setting | Env | Default | Notes |
|---------|-----|---------|-------|
| `settings.vnstock_source` | `VNSTOCK_SOURCE` | `vci` | Routed into every vnstock call; validated; no failover. |
| — | `SYNC_UNIVERSE` | curated ~34 | Comma list for `sync universe`. |
| — | `SYNC_TICKERS` | default spec | Override for the default sync. |
| — | `SYNC_LOOKBACK_DAYS` | 365 | Backfill window. |
| — | `PROVIDER_TEST_ON_START` | false | Run `provider test` at boot (no-shell diagnostics). |

---

## 7. Observability (`athena provider diagnose` / `provider test`)

If vnstock fails, the failure is made fully observable rather than hidden or
worked around by switching providers:

- **Provider errors** are raised as `VnstockError` naming the **source, method
  and symbol** (`vnstock[vci] history failed for FPT: …`), logged in the sync
  message body.
- **`athena provider test`** probes each source and reports reachable / status
  code / **failure category** (dns/tls/timeout/http/auth/provider) / response
  time / supported datasets.
- **`athena provider diagnose`** runs an active **DNS → TCP → TLS** probe of the
  VCI hosts (`trading.vietcap.com.vn`, `mt.vietcap.com.vn`,
  `iq.vietcap.com.vn`), timing and logging each stage, plus a live data probe.
- `classify_exception` categorises any error; `diagnose_connectivity` never
  raises — every stage is captured.

**No silent fallback to another provider** — ever.

---

## 8. UI

The Market snapshot service already consumes only the backend `/market/vn/*`
endpoints (persisted, read-model-derived data) with an **empty state** when
nothing is synced — no sample fallback and no fabricated values. Datasets that
vnstock does not provide keep the existing empty state. No frontend redesign.

---

## 9. Testing

- All existing tests pass (unchanged).
- New deterministic unit tests (no network): dataset catalog
  (`test_vnstock_datasets.py`), diagnostics classification
  (`test_vnstock_diagnostics.py`), sync-scope selection + new CLI commands
  (`test_market_scheduler.py`).
- **Opt-in live integration** (`VNSTOCK_LIVE=1`, `test_vnstock_live.py`):
  verifies provider connectivity, a real sync, and persistence through the
  existing pipeline (in-memory catalog/store — no DB). Skips automatically when
  disabled.

---

## 10. Deployment notes & known limitations

- **Deployment reachability is the operative risk.** vnstock works locally
  (VN IP) but the VCI hosts have been observed to **time out from a non-VN
  datacenter IP** (e.g. Render US). This is an environment/network issue, not a
  provider defect — per directive, we **do not switch providers**; we surface it
  via `athena provider diagnose` (and `PROVIDER_TEST_ON_START=true` for
  no-shell tiers). If diagnosis shows the host is unreachable from the deploy
  region, the fix is infrastructure (run the sync from a VN-reachable host /
  proxy, or a nearer region), not code.
- **Foreign Trading / Order / Side statistics** require the paid `vnstock_data`
  sponsor package — `NOT_SUPPORTED` in the installed free tier.
- **Persistence is limited to Historical Prices** under the "do not modify
  ProviderSyncService / Data Pipeline" constraint; all dashboard market
  analytics are derived from those persisted prices.
- vnstock imports lazily and writes cache under `$HOME`; the production image
  sets a writable `HOME=/app/data/home`.

---

## 11. Acceptance mapping

| # | Criterion | Status |
|---|-----------|--------|
| 1 | `athena sync market` downloads & persists real VN data | ✅ indices via vnstock → pipeline (subject to deploy reachability) |
| 2 | `athena sync universe` — configured symbols only | ✅ curated universe, never all-listed |
| 3 | `athena sync symbol FPT` — only FPT | ✅ |
| 4 | Dashboard drops sample data where live exists | ✅ snapshot reads persisted prices, empty state otherwise |
| 5 | Market page consumes only persisted data | ✅ unchanged read model |
| 6–9 | No architecture / engine / REST / frontend redesign | ✅ additive, Provider layer + CLI only |
| 10 | All existing tests pass | ✅ |

*vnstock is fully integrated into the existing Athena architecture.*
