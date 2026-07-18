# ADR-0020 — Production Data Provider (Alpha Vantage), closes R1

- Status: Accepted (Phase 5 Deployment) · Date: 2026-07-18

## Problem
R1 (the sole material production gap through Phases 2–4) is the absence of a
real market-data feed. Phase 5 requires ONE production data-provider adapter.

## Decision
Implement `AlphaVantageProvider` (`providers.connectors.alphavantage`) — an
adapter only, implementing the SDK `PriceProvider` + `FXProvider` ports:
- HTTP behind an injectable `HttpTransport` (unit-testable without network).
- Credentials from environment ONLY (`ALPHAVANTAGE_API_KEY`); never hardcoded
  or logged.
- Vendor's in-band error/rate-limit notes mapped to typed `AlphaVantageError`.
- Composed with the existing Module-2 resilience (`ResilientPriceProvider` /
  new `ResilientFxProvider`: retry/backoff, token-bucket rate limit, TTL cache,
  health monitor).
- All numerics → `Decimal` (constitution). Point-in-time FX (no look-ahead).
- Selectable via the configuration-driven `ProviderRegistry`
  (`registry_config.build_registry`), so vendors swap without code change.

Alpha Vantage chosen for a free tier, documented API, single-env-var auth, and
daily equity + FX coverage — enough to feed the price/FX pipeline paths.

## Consequences
- (+) R1 closed at the adapter layer; the RFC-0024 pipeline consumes it
  unchanged (ADR-0017). Fully tested with a fake transport (11 tests) incl.
  end-to-end publish through the pipeline.
- (−) Live certification still needs a real API key + a network run
  (credential-gated); free tier is rate-limited (5 req/min) — the token
  bucket is tuned under that. Non-VN-native coverage is a known limitation
  for Vietnamese tickers; swapping to a VN-native vendor is a new adapter.

## Business-logic guarantee
No RFC semantics or domain models changed; this is pure adapter + resilience
composition (Phase 5 rules).
