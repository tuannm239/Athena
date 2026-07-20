# Market Integration Report — persisted VN data → Market API & dashboard

**Date:** 2026-07-20 · **Scope:** wire the VnstockProvider's *persisted* output
into the Market API and dashboard (option b). **Status:** ✅ endpoint live,
all tests pass.

## 1. What was wired

The Market page and every listed dashboard widget now read a real backend
endpoint that projects the **Data Pipeline's persisted prices** — no sample
data, no vnstock in the request path.

```
VnstockProvider ──sync──▶ Data Pipeline (published "prices" dataset)
                                   │  read-only
                                   ▼
        PublishedMarketPriceReader (infra adapter)
                                   ▼
        VnMarketSnapshotQuery (market read model — pure projection)
                                   ▼
        GET /api/v1/market/vn/snapshot  (controller → mapper → schema)
                                   ▼
        web: vnMarketService.snapshot()  → Market page + dashboard widgets
```

## 2. Files

| File | Role |
|---|---|
| `backend/market/application/read_model.py` | `VnMarketSnapshotQuery` + `MarketPriceReader` port + view DTOs (read side, no domain rules) |
| `backend/infrastructure/market_read.py` | `PublishedMarketPriceReader` — reads `read_published("prices")`, maps `NotFoundError`→empty |
| `backend/api/schemas.py` | `VnMarketSnapshotResponse` (+ nested) response schema |
| `backend/api/mappers.py` | `vn_snapshot_out(view)` — view → schema |
| `backend/api/routes/market.py` | `GET /market/vn/snapshot` controller |
| `backend/api/deps.py` | composition-root wiring of the query into the container |
| `web/services/vn-market.ts` | consumes the real endpoint only; empty state on error (sample removed) |
| `tests/integration/test_market_vn.py` | integration tests for the endpoint |

## 3. Requirements → evidence

| # | Requirement | Result |
|---|---|---|
| 1 | Do not modify the VnstockProvider | ✅ untouched |
| 2 | Do not modify the Data Pipeline | ✅ untouched (only `read_published` is called) |
| 3 | Consume only persisted data | ✅ reads the published `prices` dataset via the pipeline; nothing else |
| 4 | Replace all sample data on the Market page with DB data | ✅ indices, breadth, movers, liquidity now come from the DB; the `vnMarketService` sample fallback is removed (see §6 for the one out-of-scope exception) |
| 5 | Implement the existing `/market/vn/*` endpoints the frontend needs | ✅ `GET /api/v1/market/vn/snapshot` (the only `/market/vn/*` the frontend calls) |
| 6 | Dashboard widgets read persisted data | ✅ VNINDEX, VN30, Top Gainers, Top Losers, Market Breadth, Liquidity all read the snapshot; **Market Heatmap** → §6 |
| 7 | Preserve Clean Architecture & SDK boundaries | ✅ controller→read model→port→infra adapter; no provider/SQL/vnstock in the controller; ADR-0003 verified |
| 8 | Empty state instead of sample when nothing synced | ✅ `read_published` `NotFoundError` → empty snapshot (200), asserted by test |
| 9 | Integration tests for every new endpoint | ✅ 4 tests (data projection, empty fields, empty state, auth) |
| 10 | `MARKET_INTEGRATION_REPORT.md` | ✅ this file |

Also honoured: **no new market logic** (the read model is arithmetic
aggregation — change %, breadth counts, liquidity sum, mover sorts — not a
regime/probability engine); **no vnstock fetch from controllers**; **frontend
consumes only backend APIs**.

## 4. What the snapshot derives from persisted prices

Persisted `prices` columns are `ticker, day, close, volume`. From the latest two
days per ticker the read model computes:

- **Indices** (VNINDEX/VN30/HNX…): latest close, change, change % — split out by
  the `market.domain.vietnam.Index` reference set.
- **Top Gainers / Losers / Volume**: non-index tickers ranked by change % / volume.
- **Market Breadth**: advancers / decliners / unchanged over the stocks.
- **Liquidity**: Σ(close × volume) over the stocks.
- **as_of**: latest day present.

## 5. Tests

```
tests/integration/test_market_vn.py ....                         [4 passed]
Full suite: 425 passed, 3 skipped (0 failed)   coverage 95% (gate ≥ 90%)
ruff ✓   ruff format ✓   mypy strict ✓   web typecheck ✓   web build ✓
```

The integration tests populate the pipeline exactly like a production sync
(`ProviderSyncService.full_sync_prices` over the same `SqlDatasetCatalog` +
`DuckDbSnapshotStore` the app reads), then assert the endpoint returns the
computed indices/movers/breadth/liquidity; a separate test asserts the empty
state; another asserts authentication is required.

## 6. Honest gaps (fields with no persisted source)

The persisted pipeline datasets are **prices** and **fundamentals** only. The
following are therefore returned as **explicit empties, never sample values**:

- **Sector heatmap** — needs a persisted ticker→sector mapping; the pipeline's
  `ProviderSyncService` has no sector-persistence path (and req 2 forbids
  changing it). Returned as `[]`.
- **Foreign / proprietary flows** — not provided by vnstock and not persisted.
  Returned as zeros.
- **52-week new highs / lows** — would need a long price history projection;
  returned as `0`.
- **Market Regime gauge** (shown on the Market page and the dashboard's Market
  Regime widget) — owned by ALG-001, a **separate engine explicitly out of
  scope** ("do not implement new market logic"). It still returns 501 and shows
  a labelled sample; that is why a "sample data" badge may remain on the page.
  It is **not** one of the req-6 widgets.

Enabling the first three is a future step: persist sector mappings / flows
through the pipeline (a pipeline change, deliberately not made here), after
which this same read model picks them up with no controller change.

## 7. Deploy note

Pushing to `main` triggers Render (backend) + Vercel (frontend) redeploys. The
Market page shows real data **after a VN sync has published a `prices` dataset**;
until then it correctly shows an empty state (not sample). Running the sync is a
separate operational step (e.g. a scheduled `ProviderSyncService.full_sync_prices`
job using the already-integrated VnstockProvider).
