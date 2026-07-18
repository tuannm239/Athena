# Athena — Roadmap (post-v1.0)

Direction after the internal v1.0 pilot. Priorities follow the product
principles: decision quality, risk management, portfolio optimization, and
explainability. **No item here changes the safety posture** — Athena will
continue to generate Decision Objects only, with mandatory human approval and
no trade execution.

## Near term (harden the pilot)

- **Live data feeds** — connect production fundamentals, market context and
  company data so "sample" fallbacks retire; broaden provider coverage
  (additional adapters, incl. VN-native tickers).
- **Backtest & Scenario REST endpoints** — expose their data so the matching
  reports go live.
- **Server-side search** — full-text search across decisions, evidence,
  companies and the knowledge graph, replacing the client-side index.
- **Shared rate limiter** — move from per-process to Redis-backed (ADR-0019).

## Medium term (observability & scale)

- **OpenTelemetry tracing** — distributed spans to complement request-id log
  correlation.
- **Report scheduling** — optional server-side generation/delivery of periodic
  reports.
- **Richer notifications** — user preferences per category; optional digest.
- **Self-service account flows** — password reset, profile management.

## Longer term (decision intelligence depth)

- **Calibration & drift dashboards** in-product (from the research program).
- **Portfolio optimization surfaces** — richer allocation and risk views.
- **Explainability upgrades** — deeper evidence provenance and counterfactuals.
- **Multi-tenant / team features** — shared favorites, review queues, roles.

## Explicitly out of scope (by design)

- Trade execution or broker integration — **never**.
- LLM-authored BUY/SELL decisions — **never** (ADR-0003).
- Business logic outside the Decision Kernel.

Roadmap items are candidates, not commitments; sequencing depends on pilot
feedback.
