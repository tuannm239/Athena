# ATHENA — Go-Live Checklist (Phase 5, W9)

Sign-off gate for the v1.0 pilot. Every box must be ticked (or explicitly
waived with a name + date) before exposing the platform to real users.
Complements `docs/PRODUCTION_CHECKLIST.md` (Phase 2) with the Phase 5 items.

> Pilot posture: decision-support only. No trades executed, no broker
> connected, human approval mandatory (`PILOT_MODE.md`).

## 1. Infrastructure
- [ ] DNS A/AAAA for `$ATHENA_DOMAIN` → host; TLS reachable
- [ ] `docker compose -f docker-compose.prod.yml config` validates (11 services)
- [ ] Images built + pushed to GHCR; deploy pins `ATHENA_IMAGE_TAG=<release sha>`
- [ ] API + web run as non-root; datastores unpublished (only Nginx 80/443 public)
- [ ] Log rotation active (json-file, 10m×5) on every service

## 2. Security
- [ ] `ATHENA_ENV=production`; startup secret policy active
- [ ] `JWT_SECRET` ≥ 32 random chars from secret store (not the dev default)
- [ ] `POSTGRES_PASSWORD` / `REDIS_PASSWORD` / Grafana admin password set
- [ ] `ALPHAVANTAGE_API_KEY` present in env (never in image/repo)
- [ ] TLS 1.2/1.3 only; HSTS + CSP + frame/nosniff/referrer/permissions headers live
- [ ] `/metrics`, `/health/full`, `/pilot/status` blocked at the Nginx edge
- [ ] `pip-audit` = 0 vulns; `pnpm audit` reviewed (2 dev-only accepted)
- [ ] CVE scanning gates the release pipeline (pip-audit + pnpm + Trivy + CodeQL)
- [ ] First ADMIN user created; RBAC understood (ADR-0019)

## 3. Performance
- [ ] `scripts/benchmark.py` run on prod-class hardware; within 2× of docs/BENCHMARKS.md
- [ ] `WEB_CONCURRENCY` tuned for the host; p95 latency acceptable under expected load
- [ ] Rate limits reviewed for the pilot audience (app + Nginx edge zones)

## 4. Backups & DR
- [ ] `scripts/backup.sh` scheduled daily; last run produced db + snapshot + checksum
- [ ] WAL archiving advancing
- [ ] `scripts/restore.sh <dump>` drill passed (scratch DB, schema at head)
- [ ] Backups replicated off-host
- [ ] `docs/DR_CHECKLIST.md` reviewed; one scenario rehearsed

## 5. Monitoring
- [ ] Prometheus scraping api + postgres-exporter + redis-exporter (targets `up`)
- [ ] All 8 Grafana dashboards load and populate
- [ ] Alert rules loaded; Alertmanager routing to a real receiver (Slack/PagerDuty)
- [ ] Test alert fired end-to-end (page received + resolved)
- [ ] Logs shipped from stdout; alert on `level=ERROR`

## 6. Data provider (W5)
- [ ] `ALPHAVANTAGE_API_KEY` verified against the live API (one real fetch)
- [ ] Resilience confirmed (retry/backoff/rate-limit/cache/health) under a real call
- [ ] Coverage limitations understood (equity/FX daily; VN-native tickers — see ADR-0020)
- [ ] Daily incremental sync scheduled (single instance); quarantine alerting on

## 7. Pilot mode (W6)
- [ ] `ATHENA_PILOT_MODE=true`; `/pilot/status` shows order_execution:false
- [ ] `scripts/daily_report.py` scheduled; writes to the pilot-reports volume
- [ ] Human review workflow confirmed with a real decision (approve + reject)
- [ ] Audit trail retaining decision + security events

## 8. Documentation & runbooks
- [ ] DEPLOYMENT.md, OBSERVABILITY.md, PILOT_MODE.md, SECURITY_HARDENING_REPORT.md current
- [ ] INCIDENT_RESPONSE.md + docs/RUNBOOK.md + docs/DR_PLAN.md reviewed by on-call
- [ ] PRODUCTION_VALIDATION_REPORT.md signed off

## 9. Rollback plan
- [ ] Previous good image tag known and reachable in GHCR
- [ ] Rollback rehearsed: `ATHENA_IMAGE_TAG=<good> … up -d api web`
- [ ] Migrations confirmed additive/forward-only (no prod downgrade)

## 10. Known risks (carry to the release register)
- [ ] Web dev-deps (postcss/elliptic) — low/moderate, dev-only, accepted
- [ ] Per-process rate limiter (bounded by Nginx edge) — shared Redis limiter deferred
- [ ] No OTel tracing — request-id log correlation only
- [ ] Provider coverage — VN-native ticker gap (ADR-0020)
- [ ] Images/frontend validated in CI/static, not built in the authoring env

## Go / No-Go
- [ ] **Engineering** sign-off: __________  Date: ______
- [ ] **Security** sign-off: __________  Date: ______
- [ ] **Product owner** sign-off: __________  Date: ______
- [ ] **Decision:**  ☐ GO   ☐ GO WITH CONDITIONS   ☐ NO-GO
