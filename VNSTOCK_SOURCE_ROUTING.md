# VNSTOCK_SOURCE Routing

How ATHENA selects which upstream data source `vnstock` uses for the Vietnamese
market, and how to verify a source before relying on it.

> **One provider, many sources. No automatic failover.** There is a single
> `VnstockProvider`. It is routed to exactly one upstream source per run via the
> `VNSTOCK_SOURCE` environment variable. If that source fails, the error is
> raised with the source named — the platform never silently switches to a
> different source.

---

## 1. Configuration

| Variable | Default | Meaning |
|----------|---------|---------|
| `VNSTOCK_SOURCE` | `vci` | The upstream `vnstock` data source for all VN datasets. |

```bash
# Example: route to VCI (Vietcap) — the default.
VNSTOCK_SOURCE=vci
```

The value is **case-insensitive** and trimmed (`  VCI  ` → `vci`). An
unsupported value is a **hard error** at startup of a sync/probe — it is never
coerced to a working source.

---

## 2. Supported sources

The supported set is **discovered from the installed `vnstock` package on disk**
(`vnstock/explorer/<source>/…`), so it always reflects the version actually
installed rather than a hand-maintained list that can drift. A source is
accepted for `VNSTOCK_SOURCE` only if it can serve **equity price history**
(`explorer/<source>/quote.py`), because the market sync needs OHLCV.

For the pinned **vnstock 4.0.4**, the supported equity sources are:

| Source | Value | Notes |
|--------|-------|-------|
| Vietcap | `vci` | Default. Full coverage (prices, symbols, sector, fundamentals, profile). |
| MSN | `msn` | Global market feed — prices/symbols only, no fundamentals/profile. |
| KBS | `kbs` | Prices, symbols, fundamentals, profile. |

**Not supported by vnstock 4.x** (reported as an error, not guessed):

- `ssi` — no explorer in this version.
- `tcbs` — removed from vnstock 4.x (the old public route was retired upstream).

> Setting `VNSTOCK_SOURCE=ssi` (or `tcbs`) fails fast with:
> `VNSTOCK_SOURCE='ssi' is not supported by the installed vnstock. Supported
> equity sources: vci, msn, kbs. Automatic failover is disabled — set
> VNSTOCK_SOURCE to one of these.`

---

## 3. Dataset support matrix (vnstock 4.0.4)

Which Athena dataset each source can serve, derived from the explorer modules
present on disk (`quote`, `listing`, `financial`, `company`):

| Dataset (adapter call)              | `vci` | `msn` | `kbs` |
|-------------------------------------|:-----:|:-----:|:-----:|
| prices — `quote.history`            |  ✅   |  ✅   |  ✅   |
| symbols — `listing.all_symbols`     |  ✅   |  ✅   |  ✅   |
| sector — `listing.symbols_by_industries` | ✅ | ✅ |  ✅   |
| fundamentals — `finance.ratio`      |  ✅   |  —    |  ✅   |
| profile — `company.overview`        |  ✅   |  —    |  ✅   |

`athena provider test` prints the live matrix for the installed version, so this
table is a snapshot, not the source of truth.

---

## 4. Verifying a source: `athena provider test`

Probes each supported source with a small daily-history call and reports, per
source: **reachable**, **status code** (best-effort), **response time (ms)**,
and **supported datasets**.

```bash
# Probe every supported source:
athena provider test

# Probe specific sources / with a specific symbol:
athena provider test --source vci,msn
athena provider test --source vci --symbol FPT
```

Output is one JSON object (for log/cron scraping):

```json
{
  "command": "provider.test",
  "configured_source": "vci",
  "supported_sources": ["vci", "msn", "kbs"],
  "results": [
    {
      "source": "vci",
      "reachable": true,
      "status_code": 200,
      "response_ms": 412.7,
      "supported_datasets": ["prices", "symbols", "sector", "fundamentals", "profile"],
      "rows": 5,
      "detail": "5 rows for VCI"
    },
    {
      "source": "msn",
      "reachable": false,
      "status_code": 404,
      "response_ms": 138.2,
      "supported_datasets": ["prices", "symbols", "sector"],
      "rows": 0,
      "detail": "VnstockError: vnstock[msn] history failed for VCI: ..."
    }
  ]
}
```

**Exit code:** `0` iff the **configured** source (`VNSTOCK_SOURCE`) is reachable
— i.e. the one a real sync would use — otherwise `1`. This makes it usable as a
pre-flight gate before a sync.

---

## 5. Error reporting (no silent switching)

Every upstream failure is raised as `VnstockError` with the source embedded:

```
vnstock[vci] history failed for FPT: <upstream error>
```

The scheduler logs this reason in the message body (the JSON logger drops
`extra`), so a failed sync shows exactly which source and symbol failed. There
is **no fallback to another source** — fixing a failing source is an explicit
operator action (change `VNSTOCK_SOURCE`, or resolve the upstream issue).

---

## 6. Relationship to the direct-HTTP price connectors

The repository also contains standalone direct-HTTP VN price connectors
(`vci_provider`, `vndirect_provider`, `tcbs_provider`) and a
`ChainedPriceProvider`. These remain registered as an **explicit opt-in** (set
the price capability's provider selection to `vn_chain`) but are **never the
default**, precisely because the chain performs automatic failover, which this
directive disables by default. The default price provider is single-source
`vnstock`, routed by `VNSTOCK_SOURCE`.

---

## 7. Files

| File | Role |
|------|------|
| `backend/providers/connectors/vnstock_source.py` | Source discovery, validation (`resolve_source`), dataset matrix, `probe_source`. |
| `backend/providers/connectors/vnstock_provider.py` | The single `VnstockProvider`; `RealVnstockClient` routes to `VNSTOCK_SOURCE` and names the source in every error. |
| `backend/data_pipeline/cli.py` | `athena provider test` command. |
| `backend/providers/registry_config.py` | Default price selection = `vnstock` (failover off). |
| `tests/unit/test_vnstock_source.py` | Routing, validation, matrix, and probe tests. |
