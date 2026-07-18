# FE-ADR-0003 — MockProvider for unavailable endpoints

- Status: Accepted · Date: 2026-07-18

## Decision
Endpoints that return `501 NotImplemented` (market data, company factors,
backtests — pending real data feeds / R1) are handled by
`withMockFallback`: try the real endpoint, fall back to labelled sample data
**only** on 501, and flag `mocked: true` so the UI shows a "sample data"
badge. Non-501 errors propagate (real failures are never masked).

## Consequences
- No fabricated business logic (directive requirement): mocks are inert
  sample DTOs at the service boundary, never in components.
- When the backend endpoint ships, the real path succeeds and the fallback
  stops firing automatically — zero code change.
