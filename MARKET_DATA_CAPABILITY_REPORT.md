# ATHENA — Market Data Capability Report

**Scope:** Audit of the currently installed **`vnstock 4.0.4` (FREE / open-source)**
Market Data API against the datasets the Athena dashboard requires. No code was
written or changed for this audit; findings come from direct inspection of the
installed library source at
`.venv/lib/python3.13/site-packages/vnstock/`.

**Environment note:** outbound access to Vietnamese data hosts is blocked from
the audit sandbox, so example responses below are **schemas reconstructed from
the library's column maps and function signatures** (e.g. `explorer/vci/const.py`,
`explorer/vci/quote.py`), not live captures. They are accurate to the shape
`vnstock` returns; exact values will differ at runtime.

**Active source:** `VCI` (Vietcap) — Athena's configured `VNSTOCK_SOURCE=vci`.
Where a dataset is only reachable through another source or the paid package,
that is called out explicitly.

---

## 1. Executive scoreboard

| # | Required dataset | Available (free vnstock) | Suitable for Dashboard | How |
|---|------------------|:------------------------:|:----------------------:|-----|
| 1 | VNINDEX | ✅ YES | ✅ YES | `quote.history("VNINDEX")` |
| 2 | VN30 | ✅ YES | ✅ YES | `quote.history("VN30")` + `listing.symbols_by_group("VN30")` |
| 3 | HNXINDEX | ✅ YES | ✅ YES | `quote.history("HNXINDEX")` |
| 4 | UPCOMINDEX | ✅ YES | ✅ YES | `quote.history("UPCOMINDEX")` |
| 5 | Top Gainers | ⚠️ NOT a direct API | ⚠️ Derivable | No ranking endpoint; derive from stored OHLCV |
| 6 | Top Losers | ⚠️ NOT a direct API | ⚠️ Derivable | No ranking endpoint; derive from stored OHLCV |
| 7 | Market Breadth | ⚠️ NOT a direct API | ⚠️ Derivable | No endpoint; derive by scanning the universe |
| 8 | Market Liquidity | ⚠️ PARTIAL | ⚠️ Partial | Index bar `volume` only; **no turnover value** |
| 9 | Foreign Trading | ❌ NO | ❌ NO | `foreign_trade` is sponsor-only (`NotImplementedError`) |
| 10 | Sector Summary | ⚠️ PARTIAL | ⚠️ Derivable | Classification only (no performance summary) |
| 11 | Trading Calendar | ❌ NO (in vnstock) | ✅ YES (Athena-owned) | vnstock has no holiday calendar; Athena's domain provides it |

**Bottom line:** **4 of 11** datasets are available as first-class vnstock
calls — and they are exactly the four headline indices. The remaining seven are
**market-analytics aggregates that free vnstock does not expose as endpoints**.
Of those: five are **derivable inside Athena** from per-ticker daily bars it
already syncs (gainers, losers, breadth, liquidity-by-volume, sector summary);
**Foreign Trading is genuinely unavailable** in the free tier and is not
derivable from OHLCV; **Trading Calendar** is already owned by Athena's domain
(`market/domain/vietnam.py`) and does not need vnstock at all.

---

## 2. What free vnstock 4.0.4 actually exposes (VCI)

Entry point: `Vnstock().stock(symbol="VNM", source="vci")`, then:

| Module | Public methods (free) | Serves |
|--------|-----------------------|--------|
| `.quote` | `history()`, `intraday()` | OHLCV incl. indices |
| `.listing` | `all_symbols()`, `symbols_by_group()`, `symbols_by_exchange()`, `symbols_by_industries()`, `industries_icb()`, `market_status()`, `search_symbol()` | universe, groups, ICB classification, session status |
| `.trading` | `price_board()` | real-time board for a **caller-supplied** symbol list |
| `.company` | `overview()`, `trading_stats()`, `ratio_summary()`, `shareholders()`, `officers()`, `events()`, `news()` … | per-symbol company data |
| `.finance` | `ratio()`, `balance_sheet()`, `income_statement()`, `cash_flow()` | fundamentals |

**Explicitly excluded from the free tier** (per `explorer/vci/__init__.py` and
the API-layer `@dynamic_method` stubs that raise
`NotImplementedError: Source 'vci' does not support '<method>'`):

- `trading.foreign_trade`, `trading.prop_trade`, `trading.insider_deal`,
  `trading.price_history` (bulk)
- `listing.events_calendar`
- derivatives / odd-lot / put-through / order-book depth / matched-by-price
- any screener / top-mover / breadth / market-aggregate ranking

These are the "advanced endpoints" the library steers users to the paid
`vnstock_data` sponsor package for.

---

## 3. Dataset-by-dataset findings

### 1. VNINDEX — ✅ Available

- **Function:** `Vnstock().stock(symbol="VNINDEX", source="vci").quote.history(start=..., end=..., interval="1D")`
- **Source:** VCI (`_VCI_INDEX_MAPPING["VNINDEX"] = "VNINDEX"`).
- **Example response (schema):**
  ```
  time        open      high      low       close     volume
  2026-07-17  1291.20   1298.44   1288.10   1295.66   612,340,000
  2026-07-18  1295.66   1302.05   1293.02   1300.11   588,120,000
  ```
  Columns: `time, open, high, low, close, volume` (`_OHLC_MAP`).
- **Missing fields:** no index `value` (turnover), no advance/decline breadth,
  no foreign flow embedded in the index bar.
- **Suitable for Athena Dashboard:** ✅ YES — index level, change, and history.

### 2. VN30 — ✅ Available (index **and** constituents)

- **Index history:** `quote.history("VN30")` → same OHLCV schema as above.
- **Constituents:** `listing.symbols_by_group("VN30")` → `pd.Series` of 30 symbols
  (e.g. `["ACB","BID","CTG","FPT","GAS","HPG","MWG","VCB","VHM","VIC","VNM",...]`).
- **Source:** VCI.
- **Missing fields:** the constituents call returns **symbols only** — no weights,
  no per-member price in the same call (join with `quote`/`price_board`).
- **Suitable for Athena Dashboard:** ✅ YES.

### 3. HNXINDEX — ✅ Available

- **Function:** `quote.history("HNXINDEX")` (mapped internally to `"HNXIndex"`).
- **Source:** VCI.
- **Example response (schema):** identical OHLCV columns to VNINDEX.
- **Missing fields:** same as VNINDEX (no value/breadth/foreign).
- **Suitable for Athena Dashboard:** ✅ YES.

### 4. UPCOMINDEX — ✅ Available

- **Function:** `quote.history("UPCOMINDEX")` (mapped to `"HNXUpcomIndex"`).
- **Source:** VCI.
- **Example response (schema):** identical OHLCV columns.
- **Missing fields:** same as VNINDEX.
- **Suitable for Athena Dashboard:** ✅ YES.

### 5. Top Gainers — ⚠️ No direct API (derivable)

- **Function:** **none.** Free vnstock has no screener/ranking endpoint.
- **Source:** n/a.
- **Closest primitive:** `trading.price_board(symbols_list)` returns per-symbol
  `price_change_pct` — but the caller must **supply the symbol list**; it does
  not rank or scan the market.
- **Example response (schema, `price_board` per symbol):**
  ```
  listing.symbol  listing.ref_price  match.match_price  match.match_vol  listing.price_change_pct
  FPT             138.0              140.6              5,300,000        +1.88
  ```
- **Missing fields:** no market-wide ranking, no "top N" selection.
- **Suitable for Athena Dashboard:** ⚠️ Only if **derived inside Athena** by
  sorting the persisted daily-bar universe by daily return. No out-of-box call.

### 6. Top Losers — ⚠️ No direct API (derivable)

- Identical situation to **Top Gainers** (same `price_board` primitive, no
  ranking endpoint). Derivable inside Athena from stored OHLCV. Not out-of-box.
- **Suitable for Athena Dashboard:** ⚠️ Derivable only.

### 7. Market Breadth — ⚠️ No direct API (derivable)

- **Function:** **none.** No advancers/decliners/unchanged endpoint.
- **Closest primitive:** count up/down/flat by scanning the whole universe via
  repeated `quote`/`price_board` calls.
- **Missing fields:** everything — there is no aggregate breadth object.
- **Suitable for Athena Dashboard:** ⚠️ Derivable inside Athena from the stored
  price universe (Athena's read model already computes breadth this way). No
  vnstock endpoint.

### 8. Market Liquidity — ⚠️ Partial

- **Function:** index `quote.history(...)` returns a `volume` column (index-level
  matched volume). There is **no turnover-value (VND) aggregate** and no
  whole-market liquidity object.
- **Source:** VCI.
- **Example response (schema):** the `volume` column of the index bar (see #1).
- **Missing fields:** **traded value (turnover in VND)**, buy/sell split,
  exchange-level totals.
- **Suitable for Athena Dashboard:** ⚠️ Partial — a volume proxy is available;
  value-based liquidity must be derived (sum of `close × volume` over the
  persisted universe) or sourced elsewhere.

### 9. Foreign Trading — ❌ Not available

- **Function:** `Trading.foreign_trade(...)` exists at the API layer but for the
  VCI source raises `NotImplementedError: Source 'vci' does not support
  'foreign_trade'` (it is a sponsor-only endpoint).
- **Source:** none in free tier. (KBS `const.py` defines foreign fields
  `FB/FR = foreign_buy/sell_volume`, but the free KBS explorer exposes no
  foreign-flow method either.)
- **Partial fragment:** `company.ratio_summary()` / price-info map carries a
  static per-symbol `foreign_volume` / `foreign_room` snapshot — **not** net
  foreign buy/sell **flow**, and not aggregated.
- **Missing fields:** foreign net buy/sell value & volume, per-market and
  per-symbol daily flow — all of it.
- **Suitable for Athena Dashboard:** ❌ NO. Not available and **not derivable**
  from OHLCV. Requires the paid `vnstock_data` package or a different provider.

### 10. Sector Summary — ⚠️ Partial (classification only)

- **Function:** `listing.symbols_by_industries()` → symbol ↔ ICB industry map;
  `listing.industries_icb()` → the ICB taxonomy.
- **Source:** VCI.
- **Example response (schema, `symbols_by_industries`):**
  ```
  symbol  icb_name2            icb_name3               icb_name4
  FPT     Technology           Software & Comp Svcs    Computer Services
  VCB     Financials           Banks                   Banks
  ```
- **Missing fields:** **no sector-level performance summary** — no aggregate
  sector return, market-cap, breadth, or flow. Only the static membership map.
- **Suitable for Athena Dashboard:** ⚠️ The **classification** is usable and
  suitable; a **sector performance summary** must be derived inside Athena
  (group persisted constituent returns by ICB sector). No vnstock summary call.

### 11. Trading Calendar — ❌ Not in vnstock (Athena already owns it)

- **Function:** vnstock has **no** holiday-aware trading calendar.
  `listing.market_status()` returns only the current session open/closed status
  and hours (from `core.utils.market.trading_hours("HOSE")`);
  `listing.events_calendar()` is a sponsor-only stub (and is corporate events —
  dividends/AGM — not the exchange calendar).
- **Source:** none.
- **Example response (`market_status`, schema):**
  ```
  exchange  is_open  session       open_time  close_time
  HOSE      True     CONTINUOUS     09:00      15:00
  ```
- **Missing fields:** trading-day list, public/lunar holidays (Tết, Hùng Kings),
  early-close days.
- **Suitable for Athena Dashboard:** ✅ YES — but via **Athena's own**
  `market/domain/vietnam.py::TradingCalendar` (weekends + configurable
  holidays), **not** vnstock. vnstock is not needed for this dataset.

---

## 4. Grouping the gaps

| Group | Datasets | Status | Path to fill |
|-------|----------|--------|--------------|
| **A. First-class vnstock** | VNINDEX, VN30, HNXINDEX, UPCOMINDEX | ✅ Ready | `quote.history` (+ `symbols_by_group` for VN30 members) |
| **B. Derivable inside Athena from OHLCV** | Top Gainers, Top Losers, Market Breadth, Market Liquidity (volume), Sector Summary | ⚠️ No endpoint, but computable | Sync per-ticker daily bars for the universe; Athena's read model aggregates (it already derives breadth/movers/liquidity from persisted prices) |
| **C. Genuinely unavailable (free)** | Foreign Trading | ❌ Missing | Paid `vnstock_data` package, or a foreign-flow-capable source |
| **D. Athena-owned, not a vnstock concern** | Trading Calendar | ✅ Ready | `market/domain/vietnam.py::TradingCalendar` |

---

## 5. Conclusions (no code — audit only)

1. **The four required indices are fully covered** by free vnstock/VCI via
   `quote.history`, with a clean OHLCV schema. These are dashboard-ready.
2. **Gainers, Losers, Breadth, Liquidity(volume), Sector Summary have no
   dedicated vnstock endpoint**, but are **derivable inside Athena** from the
   per-ticker daily bars it already ingests — the raw material (OHLCV +
   `symbols_by_industries` classification) is available; the aggregation is
   Athena's, not vnstock's.
3. **Market Liquidity by *value* (turnover VND)** and **Foreign Trading** are the
   two true data gaps in the free tier: turnover-value is only partially
   recoverable (derive `close × volume`), and **foreign flow is unavailable and
   not derivable** — it needs the paid `vnstock_data` package or another source.
4. **Trading Calendar** should continue to come from Athena's domain layer;
   vnstock does not provide it and does not need to.
5. **Blocking caveat (unchanged from prior audits):** all of the above assumes
   the deployment can actually reach VCI. From a non-VN datacenter IP (e.g.
   Render US) VCI has been observed to time out. Confirm reachability with
   `athena provider test` (or `PROVIDER_TEST_ON_START=true`) before relying on
   any of these datasets in production.

**Recommended dataset → source mapping for a build phase (for decision, not yet
implemented):**

| Dataset | Proposed source of truth |
|---------|--------------------------|
| VNINDEX / VN30 / HNXINDEX / UPCOMINDEX | vnstock `quote.history` (VCI) |
| Top Gainers / Losers / Breadth / Liquidity(vol) / Sector Summary | Derived in Athena from persisted OHLCV + ICB classification |
| Foreign Trading | **Out of scope for free vnstock** — needs `vnstock_data` or alternate provider (decision required) |
| Trading Calendar | Athena domain `TradingCalendar` |

*End of audit. No provider or synchronization code written, per directive.*
