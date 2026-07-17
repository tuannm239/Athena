# ADR-0018 — Observability Stack (Metrics Pull, OTel Deferred)

- Status: Accepted (Engineering Authorization)
- Date: 2026-07-16
- Deciders: Engineering

## Problem

Phase 2 Module 6 requires production observability: metrics, dashboards,
tracing and a health surface. The platform already has structured JSON
logging with request-id and decision-id correlation (Sprint 16). What
remains open is the metrics transport and whether to adopt the full
OpenTelemetry SDK now.

## Decision

1. **Metrics: Prometheus pull model** via `prometheus-client`. One
   `Metrics` registry per application instance (test isolation), exposed
   at `/metrics` in the exposition format. HTTP metrics
   (`athena_http_requests_total`, `athena_http_request_duration_seconds`)
   are labeled with the *route template*, never the raw path, to bound
   label cardinality.
2. **Dashboards:** Prometheus + Grafana ship in `docker-compose.yml`
   with file-provisioned datasource and an ATHENA API dashboard
   (request rate, P95 latency, error share) under `ops/`.
3. **Health surface:** `/health` stays a bare liveness probe;
   `/health/full` reports per-component status (database, Redis,
   snapshot store) and an aggregate `ok`/`degraded` — it always returns
   200 (reporting, not gating).
4. **Distributed tracing: deferred.** The platform is a modular monolith
   (ADR-0001) with a single-process request path; request-id correlation
   in structured logs currently answers the same questions spans would.
   The full OpenTelemetry SDK (traces + OTLP collector) is adopted when
   the event bus goes out-of-process (RFC-0022) or a second service
   appears — the seams (middleware, kernel logging) are where
   instrumentation will attach.

## Alternatives considered

- **OpenTelemetry metrics + collector now** — heavier moving parts for
  no additional insight in a single process; revisit with RFC-0022.
- **StatsD push** — pull scraping is simpler to operate and the
  de-facto standard with Prometheus/Grafana.

## Consequences

- (+) One new lightweight dependency; dashboards reproducible from the
  repository; per-app registries keep tests hermetic.
- (−) No cross-service traces until OTel lands — acceptable while there
  is exactly one service.
