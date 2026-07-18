# ATHENA — Observability (Phase 5, W3)

The pilot ships a complete metrics → dashboards → alerting stack, plus
structured request-correlated logging. This document is the operator's map of
what is emitted, where it lands, and how it is alerted.

## Stack

| Component | Image | Role |
|---|---|---|
| Prometheus | `prom/prometheus:v2.53.0` | scrape + rules + routing to Alertmanager |
| Alertmanager | `prom/alertmanager:v0.27.0` | dedupe, group, route (pager / ops channel) |
| Grafana | `grafana/grafana:11.1.0` | 8 provisioned dashboards |
| postgres_exporter | `…/postgres-exporter:v0.15.0` | PostgreSQL metrics **+ custom domain-state queries** |
| redis_exporter | `oliver006/redis_exporter:v1.62.0` | cache metrics |

All are in `docker-compose.prod.yml` on the ops network only — none is
published to the host. Grafana is reached through an ops-side tunnel/VPN.

## Metrics sources

**1. Application metrics (native, ADR-0018)** — the FastAPI app exposes a
Prometheus registry at `GET /metrics`:

- `athena_http_requests_total{method,path,status}` — request counter, labelled
  by **route template** (bounded cardinality, never raw paths).
- `athena_http_request_duration_seconds_bucket{method,path}` — latency
  histogram (p50/p95/p99 via `histogram_quantile`).
- `athena_app_info{version}` — static build metadata.

**2. Infrastructure metrics** — `postgres_exporter` and `redis_exporter`
provide the standard `pg_*` and `redis_*` families.

**3. Domain-state metrics (custom, read-only)** — the domain layer must not
import infrastructure (clean-architecture / ADR-0003), so we do **not**
instrument domain code with Prometheus. Instead `postgres_exporter` runs
read-only queries over the system of record
(`ops/postgres_exporter/queries.yaml`) and turns persisted state into gauges:

| Metric | Source table | Powers |
|---|---|---|
| `athena_decisions_by_status_total{status}` | `decisions` | Decision Pipeline |
| `athena_datasets_by_status_total{status}` | `datasets` | Data Pipeline |
| `athena_kg_nodes_by_type_total{type}` / `athena_kg_edges_active_total` | `kg_nodes` / `kg_edges` | Knowledge Graph |
| `athena_feature_definitions_by_status_total{status}` | `feature_definitions` | Feature Store |
| `athena_audit_events_total{entity_type}` | `audit_log` | Decision Pipeline, Security |
| `athena_users_total` | `users` | System Health |

This keeps the architecture intact while giving every named dashboard real
data.

## Dashboards (8, provisioned from `ops/grafana/dashboards/`)

| # | Dashboard | UID | Primary signals |
|---|---|---|---|
| 1 | System Health | `athena-system-health` | `up` per target, version, global RPS, 5xx share, users |
| 2 | API Performance | `athena-api` | request rate, p95 latency, error share by route |
| 3 | Decision Pipeline | `athena-decision-pipeline` | decisions by status, approvals/rejections, review backlog, decision-API latency, audit trail |
| 4 | Data Pipeline | `athena-data-pipeline` | published vs quarantined datasets, publish trend, ingestion-API traffic |
| 5 | Database | `athena-database` | pg_up, backends, cache hit ratio, commit/rollback, deadlocks |
| 6 | Redis | `athena-redis` | redis_up, clients, memory, keyspace hit ratio, cmd/s |
| 7 | Knowledge Graph | `athena-knowledge-graph` | nodes by type, active edges, growth |
| 8 | Feature Store | `athena-feature-store` | feature definitions by status, active count |

They auto-load via `ops/grafana/provisioning/` into the **ATHENA** folder.

## Alerting

Rules: `ops/prometheus/alerts.yml` (loaded by `prometheus.prod.yml`).

| Alert | Severity | Condition |
|---|---|---|
| `AthenaApiDown` | critical | `up{job="athena-api"}==0` for 1m |
| `PostgresDown` | critical | `up{job="postgres"}==0` for 2m |
| `RedisDown` | warning | `up{job="redis"}==0` for 2m |
| `HighErrorRate` | critical | 5xx share > 5% for 5m |
| `HighLatencyP95` | warning | p95 > 1s for 10m |
| `AuthAbuse` | warning | sustained 429 on `/auth*` |
| `DatasetsQuarantined` | warning | any `QUARANTINED` dataset for 15m |
| `NoDecisionActivity` | info | no decisions created in 24h |

Routing: `ops/alertmanager/alertmanager.yml` — `critical` → pager (1h repeat),
`warning`/`info` → ops channel (4h repeat), with an inhibit rule so an API-down
alert suppresses its dependent latency/error alerts. Receiver endpoints
(Slack webhook, PagerDuty key) are injected from secrets at deploy time;
the file ships with them commented as templates.

## Logging & request correlation ("tracing")

Structured JSON logs on stdout (`configure_logging`, `athena.*` loggers).
Every request carries a `request_id`, echoed in the `X-Request-ID` response
header and included on the access-log line and any error; kernel evaluations
log `decision_id`. Nginx re-emits the upstream `X-Request-ID` in its own JSON
access log, so a single id correlates edge → app → decision trace across the
stack. Ship stdout to your aggregator and alert on `level=ERROR`.

> **Scope note (honest):** correlation is via structured logs + request-id,
> not OpenTelemetry spans. Full distributed tracing (OTel traces/exporters) is
> **not** wired in this pilot and is recorded as a post-pilot enhancement in
> `PILOT_RELEASE_v1.0.md`. It is not required for the human-in-the-loop pilot.

## Health checks

- `GET /health` — liveness (public; used by container HEALTHCHECK + Nginx).
- `GET /health/full` — per-component dashboard (database, redis, snapshots)
  with `pilot_mode`; **degraded ≠ down** — it names the failing component.
  Restricted to the ops network (blocked at the Nginx edge).
- `GET /pilot/status` — pilot posture (W6), also ops-network only.

## Verification (on the deployed host)

```bash
# API metrics present
docker compose -f docker-compose.prod.yml exec api curl -fsS localhost:8000/metrics | grep athena_http_requests_total
# exporters up
curl -fsS http://prometheus:9090/api/v1/targets | jq '.data.activeTargets[].health'
# domain gauges populated
curl -fsS 'http://prometheus:9090/api/v1/query?query=athena_decisions_by_status_total'
```
