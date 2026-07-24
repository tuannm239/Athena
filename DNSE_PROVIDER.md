# DNSE Market-Data Provider

DNSE OpenAPI is Athena's **primary** market-data provider; **VNStock remains
the fallback**. This is an Infrastructure-only change — no domain model, RFC,
API contract or business logic changed, and no engine required modification.

## Architecture (unchanged)

Business components (Market Engine, Data Pipeline, Feature Store, Decision
Compiler, Probability/Risk/Portfolio/Backtest Engines) consume the existing
**Provider SDK ports** only (`PriceProvider.daily_bars`, …). They never
reference DNSE or VNStock, and never see provider-specific JSON or exceptions.

```
        Data Pipeline / Market Engine
                    │
                    ▼
        Provider SDK ports (PriceProvider …)   ← unchanged interface
                    │  selected by config (ADR-0017)
        ┌───────────┴───────────┐
        ▼                       ▼
   DNSEProvider (primary)   VnstockProvider (fallback)
        │                       │
        ▼                       ▼
   DNSE OpenAPI              vnstock
```

> Note on placement: the connector lives in `backend/providers/connectors/dnse/`
> (with every other connector), **not** `backend/market/providers/`. Putting an
> HTTP adapter inside the `market` domain would violate ADR-0004 (the domain
> never depends on infrastructure) — the spec's own "Infrastructure-only" rule.

## Package

`backend/providers/connectors/dnse/`

| File | Responsibility |
|------|----------------|
| `config.py` | `DnseConfig` from env; secret redaction for logs |
| `exceptions.py` | `DnseError` + `DnseAuthError` / `DnseRateLimitError` / `DnseUnavailableError` (all `DomainError`s) |
| `auth.py` | `DnseAuthenticator` — JWT bearer, cached; `None` when unauthenticated |
| `client.py` | `DnseTransport` seam + `HttpxDnseTransport`; `DnseMarketClient` (transient-only retry, error translation, redacted logging) |
| `models.py` | UDF column-array → `PriceBar` mapping (Decimal, never float) |
| `market_data.py` | `DnseProvider` (implements `PriceProvider`) + `create_dnse_price_provider` factory |

## Configuration (selection is config-only)

| Env var | Default | Meaning |
|---------|---------|---------|
| `MARKET_PROVIDER` | `dnse` | `dnse` or `vnstock` |
| `MARKET_FAILOVER` | `true` | when `dnse`, try DNSE then fall back to VNStock per ticker |
| `DNSE_BASE_URL` | `https://api.dnse.com.vn` | DNSE OpenAPI base |
| `DNSE_API_KEY` / `DNSE_API_SECRET` | — | credentials, env-only, never logged/hardcoded |
| `DNSE_TIMEOUT_SECONDS` / `DNSE_MAX_ATTEMPTS` | `10` / `4` | HTTP timeout, transient-retry cap |

`providers.registry_config.market_selection(provider, failover)` maps the
config to a per-capability selection: `MARKET_PROVIDER=dnse` (with failover)
resolves **PRICE** to the `dnse_chain` (DNSE → VNStock). Fundamentals and sector
classification stay on VNStock — DNSE does not serve those datasets.

## Behaviour

- **Auth** (§2): JWT from credentials, cached until near expiry; public chart
  routes work without credentials (token omitted).
- **Retry** (§9): only transient failures (429/500/502/503/504/timeout/network)
  retry, exponential backoff; permanent errors (401/403/4xx) never retry.
- **Errors** (§7): every httpx/HTTP failure is translated to a typed
  `DnseError`; nothing DNSE-specific escapes Infrastructure.
- **Logging** (§8): logs request, latency, retry count, rate-limit events and
  the selected provider; API key/secret, tokens, Authorization and signatures
  are redacted.
- **Failover** (§5): `ChainedPriceProvider` falls through to VNStock on any DNSE
  error; business layers are unaware.

## Tests

`tests/unit/test_dnse_provider.py` (28 cases) mocks every DNSE response through
the transport/client seams — **no real credentials or network**: config
redaction, auth (token cache / missing-token / unauthenticated), status→error
translation, transient-vs-permanent retry, index routing, UDF→`PriceBar`
mapping, the DNSE→VNStock failover chain, and config-driven selection.

Gates: `pytest` 571 passed / 9 skipped · `ruff` clean · `mypy` clean.

## Not included (per Non-Goals)

Order placement, trading/account/portfolio APIs, LightSpeed features. Market
data only.

## Open item (best-effort HTTP layer)

`RealDnseMarketClient` (`HttpxDnseTransport`) targets DNSE's public chart
(TradingView-UDF) OHLC routes and the JWT login route to the best of the
public API's documented behaviour. The exact endpoint paths / response fields
should be confirmed against DNSE's official docs; they are isolated behind the
`DnseTransport` seam, so correcting them touches only `client.py` and requires
no change to the adapter, wiring, tests, or any business layer.

**STOP — VNStock is not removed or deprecated.** Awaiting approval before any
VNStock removal.
