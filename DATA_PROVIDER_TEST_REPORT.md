# Data Provider Test Report — VnstockProvider

**Date:** 2026-07-20 · **Provider:** `vnstock` 4.0.4 (Vietnam market) ·
**Status:** ✅ Integrated, all deterministic tests pass · ⚠️ live calls validated
out-of-sandbox (see §5)

## 1. What was built

A `VnstockProvider` adapter that maps the official **`vnstock`** library to the
existing Athena Provider SDK. It is an **adapter only** — no business logic; the
`decision_kernel`, `risk`, `portfolio`, and `behavior` packages have no import
path to it (ADR-0003/0017 preserved).

| File | Purpose |
|---|---|
| `backend/providers/connectors/vnstock_provider.py` | adapter + `VnstockClient` seam + `RealVnstockClient` + resilient factories |
| `backend/providers/sdk/models.py` | new DTOs `SymbolInfo`, `CompanyProfile` |
| `backend/providers/sdk/ports.py` | new ports `SymbolListProvider`, `CompanyProfileProvider` |
| `backend/providers/connectors/resilient.py` | new `ResilientFundamentalProvider`, `ResilientSectorProvider` |
| `backend/providers/registry_config.py` | registers vnstock for PRICE / FUNDAMENTAL / SECTOR |
| `tests/unit/test_vnstock_provider.py` | 24 deterministic tests + 1 opt-in live smoke |
| `pyproject.toml` | `vnstock` dependency + mypy override for the un-stubbed lib |

## 2. Capabilities (requirement 3)

| Capability | SDK port / method | vnstock source |
|---|---|---|
| **Historical OHLCV** | `PriceProvider.daily_bars` | `stock.quote.history(interval="1D")` |
| **VNINDEX** | `daily_bars("VNINDEX", …)` | index treated as a symbol |
| **VN30** | `daily_bars("VN30", …)` | index treated as a symbol |
| **Financial Statements** | `FundamentalProvider.fundamentals` | `stock.finance.ratio(period="year")` |
| **Industry Classification** | `SectorProvider.classification` | `stock.listing.symbols_by_industries()` |
| **Symbol List** | `SymbolListProvider.symbols` | `stock.listing.all_symbols()` |
| **Company Profile** | `CompanyProfileProvider.profile` | `stock.company.overview()` |

Financial-statement coverage is a curated allowlist of ratios (roe, roa, pe, pb,
eps, bvps, margins, debt/equity, current ratio, revenue, net income); unknown
vendor columns are ignored so a schema change narrows coverage instead of
crashing ingestion ("where available", requirement 3).

## 3. Retry, cache, storage (requirements 4–6)

- **Retry on transient failures (4):** each production capability is wrapped by
  the existing Module-2 resilience stack (`RetryPolicy`, exponential backoff,
  4 attempts) via `create_vnstock_*` factories — the adapter does not
  re-implement it. Verified: `test_retry_then_succeed`, `test_retry_exhausted_raises`.
- **Caching (5):** `TtlCache` (1 h) fronts every capability. Verified a second
  identical call is served from cache with no upstream hit:
  `test_cache_avoids_second_call`, `test_fundamental_cache_and_health`,
  `test_sector_cache`.
- **Rate limiting:** token bucket (1 req/s, burst 5) — courteous to the free
  VCI/TCBS endpoints.
- **Data Pipeline storage (6):** the provider is fed to the existing
  `ProviderSyncService`; no new storage path. Verified end-to-end that prices
  (incl. VNINDEX) and fundamentals land as **published, quality-gated dataset
  versions**: `test_full_sync_prices_stores_published_version`,
  `test_sync_fundamentals_stores_records`.

## 4. Test results (requirement 8)

```
tests/unit/test_vnstock_provider.py .......................s   [24 passed, 1 skipped]
Full suite:                                                     415 → 439 passed, 3 skipped
Coverage (backend): 95% TOTAL  (gate ≥ 90% ✓)
  providers/connectors/vnstock_provider.py  75%  (uncovered = RealVnstockClient network seam, §5)
ruff check ✓   ruff format ✓   mypy strict ✓
```

Test groups: OHLCV window/sort · VNINDEX/VN30 · financial-ratio mapping ·
industry classification · symbol list · company profile · retry (succeed &
exhaust) · cache-hit · registry wiring · **Data Pipeline storage** ·
`RealVnstockClient` DataFrame→records normalization (incl. MultiIndex
flattening) exercised against **real pandas** with no network.

## 5. The sandbox network limitation (honest disclosure)

**"Integration tests using real vnstock responses where feasible" — it was NOT
feasible to hit the live network in this build environment.** `vnstock` reaches
VN data hosts (`iq.vietcap.com.vn`, `apipubaws.tcbs.com.vn`) eagerly, even on
construction, and this environment's **policy-enforcing egress proxy blocks them
with `403 Forbidden` on CONNECT**. Verified directly.

Consequences and how they are handled:

1. **Deterministic tests use recorded, real-shaped `vnstock` 4.x records**
   (the exact columns the library returns) driven through the injectable
   `VnstockClient` seam. This exercises all parsing, resilience, and pipeline
   storage without a network — the same seam pattern as the Alpha Vantage adapter.
2. **The `RealVnstockClient` network methods (the seam's live half) are not
   executed here** (hence the 75% file coverage). They are covered by an
   **opt-in live smoke test**, `TestLiveSmoke`, skipped unless `VNSTOCK_LIVE=1`.
3. **Column-name tolerance:** because live shapes could not be verified in-sandbox,
   every parser reads through alias lists (`time|date|tradingDate`,
   `ticker|symbol`, `icb_name2..4`, …) so minor vendor/version differences do not
   break ingestion.

### Running the live validation (on open internet)

```bash
# locally or on Render — anywhere with outbound access to VN data hosts
VNSTOCK_LIVE=1 uv run pytest tests/unit/test_vnstock_provider.py::TestLiveSmoke -q
```

This fetches real VNINDEX bars and the real symbol list and asserts they are
non-empty. If VN hosts geo-block the runner's IP, run it from a VN-reachable
network. Selection is configured in `registry_config.DEFAULT_SELECTION`
(`price/fundamental/sector → vnstock`).

## 6. Dependency & privacy notes

- Installing `vnstock` pulls a large transitive set (pandas, matplotlib,
  seaborn, mplfinance) and the **`vnai` telemetry package**. The `vnstock`
  import is **lazy** (inside `RealVnstockClient`), so the API process pays no
  import cost at boot and no telemetry runs unless a VN sync executes. If the
  telemetry or image size is unwanted, move `vnstock` to an optional dependency
  group and run VN ingestion as a separate job — the seam makes this a
  config-only change, no adapter edits.

## 7. Constitution compliance

- **No business logic modified** (requirement 7): all changes live under
  `providers/` (+ one mypy override); the Data Pipeline is used, not changed;
  no engine/kernel edits.
- Money/ratios are `Decimal`, never float.
- Credentials/telemetry: none hardcoded; `VNSTOCK_SOURCE` (default `VCI`) is the
  only config.

**Conclusion:** the VnstockProvider is fully integrated behind the existing SDK,
resilient, cached, stores through the Data Pipeline, and passes all deterministic
tests. Live-network validation is a single opt-in command to run wherever
outbound access to VN data hosts is available.

---

## 8. Addendum — VN price source switched to VNDirect (TCBS route retired)

**Context.** In production (Render) the TCBS public endpoint
`apipubaws.tcbs.com.vn/stock-insight/{v1,v2}/stock/bars-long-term` returned a
clean **`404 Not Found`** for *every* ticker (indices and stocks alike) — the
host is reachable (not geo-blocked; a 404, not a 403/timeout), but the route has
been retired. vnstock was already unusable in-container (`$HOME`/telemetry
writes), so a token-free HTTP source was needed.

**Change.** The default VN price source is now a **resilient chain**
(`ChainedPriceProvider`, ADR-0017): for each ticker it tries sources in order
and returns the first non-empty result.

1. **VNDirect** (`vndirect_provider.py`) — primary. Public TradingView-UDF feed
   `dchart-api.vndirect.com.vn/dchart/history`, **no credentials**, covers
   indices (`VNINDEX`, `VN30`, `HNXINDEX`, …) and stocks via one `symbol` param.
2. **TCBS** (`tcbs_provider.py`) — fallback, kept for when its route returns.

FireAnt was considered and rejected as primary: it requires a Bearer JWT token
(expires / can be revoked), whereas VNDirect's dchart feed is token-free.

**Registry.** `registry_config.py`: `VNDIRECT` and `VN_CHAIN` registered;
`DEFAULT_SELECTION[PRICE] = VN_CHAIN`. Each source stays per-ticker tolerant
(returns `()` on failure) so one bad symbol never aborts a sync; the chain also
falls through a *raising* source to the next.

**Tests.** `tests/unit/test_vndirect_provider.py` — UDF parsing (stock + index),
window filter, `s != "ok"` guard, per-ticker tolerance, chain fallback
(empty → next, raising → next, first-non-empty short-circuits), pipeline
storage, and the registry default resolving to the chain. Opt-in live smoke:
`VNDIRECT_LIVE=1`. All deterministic tests pass; ruff/format/mypy green.

**No business logic modified** — changes live under `providers/` only; the Data
Pipeline is used, not changed.
