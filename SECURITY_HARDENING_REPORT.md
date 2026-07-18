# ATHENA — Security Hardening Report (Phase 5, W4)

**Date:** 2026-07-18 · **Scope:** production pilot readiness · **Verdict:**
**PASS with two accepted low/moderate dev-only advisories.**

This report verifies the production security posture item by item, with
evidence. It builds on the Phase 2 `SECURITY_AUDIT_REPORT.md` /
`docs/SECURITY_REVIEW.md` and confirms the W1–W3 edge/CI hardening. No
business logic was changed.

## Summary

| Area | Status | Evidence |
|---|---|---|
| Secret management | ✅ | env-only; prod startup refuses dev/weak JWT |
| JWT / sessions | ✅ | HS256, single-use refresh, reuse detection |
| RBAC | ✅ | `require_roles` guard; 403 on mismatch |
| API keys | ✅ | sha256-only storage, prefixed, revocable |
| Passwords | ✅ | Argon2id |
| TLS | ✅ | Nginx edge, TLS 1.2/1.3, HSTS preload |
| Rate limiting | ✅ | app token-bucket + Nginx edge zones |
| Security headers | ✅ | CSP, HSTS, X-Frame DENY, nosniff, Referrer, Permissions |
| CORS | ✅ (N/A) | same-origin via Nginx; no wildcard exposure |
| Python deps (CVE) | ✅ | `pip-audit`: **0 known vulnerabilities** (29 prod pkgs) |
| Web deps (CVE) | ⚠️ accepted | `pnpm audit`: 1 low + 1 moderate, both dev/build-only |
| Container hardening | ✅ | non-root uids, datastores unpublished |
| CVE scanning in CI | ✅ | pip-audit + pnpm audit + Trivy + CodeQL (cd.yml) |

## Findings & evidence

### 1. Secret management — PASS
Secrets come from the environment only (`Settings.from_env`); none are
hardcoded. `Settings.ensure_safe_for_environment()` (invoked at app startup)
**blocks boot in production** when `JWT_SECRET` is the dev default or shorter
than 32 chars (`backend/infrastructure/config.py`; ADR-0019). Provider keys
(`ALPHAVANTAGE_API_KEY`) are read from env and never logged (W5 adapter).
`.env.production` / `.env.staging` are git-ignored.

### 2. JWT & sessions — PASS
HS256 access/refresh pairs (`JwtTokenService`). Refresh tokens are
**single-use with reuse detection**: the jti is registered on issue, consumed
on verify, and a replayed token is rejected (`RefreshTokenStore`, ADR-0019).
TTLs are configurable (access 15 min, refresh 14 d defaults).

### 3. RBAC — PASS
`require_roles(*roles)` dependency guards write routes; `current_user`
authenticates. Roles `ANALYST`/`ADMIN` (default `ANALYST`); role mismatch
raises `AuthorizationError` → 403 (`backend/api/deps.py`, decision routes use
`writer = require_roles(ANALYST, ADMIN)`).

### 4. API keys — PASS
Only the **sha256** of a key is stored (`ApiKeyRow.key_hash`, unique), with a
short display prefix and a `revoked_at` column — plaintext keys are never
persisted (ADR-0019).

### 5. Passwords — PASS
Argon2id via argon2-cffi (`Argon2PasswordHasher`), verify is
constant-time and mismatch-safe.

### 6. TLS — PASS
Terminated at Nginx (`nginx.conf`): TLS 1.2/1.3 only, modern cipher suite,
HTTP→HTTPS redirect, Let's Encrypt via certbot webroot with auto-renew
(`docker-compose.prod.yml`). HSTS `max-age=2y; includeSubDomains; preload`.

### 7. Rate limiting — PASS (defense in depth)
Application token-bucket per client host with a tighter auth bucket
(`api/ratelimit.py`; 240/min general, 20/min auth) **and** Nginx edge zones
(`20r/s` api, `2r/s` auth). 429 responses carry `Retry-After`. Note: the app
limiter is per-process (ADR-0019) — a shared Redis limiter is a documented
future step; the Nginx edge zone bounds it globally in the interim.

### 8. Security headers — PASS
Set at the Nginx edge, `always`: `Content-Security-Policy` (default-src
'self', frame-ancestors 'none'), `Strict-Transport-Security`,
`X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`,
`Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy`
(geo/mic/camera off). `server_tokens off`.

### 9. CORS — PASS (not applicable by design)
Frontend and API are served **same-origin** behind one Nginx host, so no CORS
is configured and no wildcard `Access-Control-Allow-Origin` is exposed. If a
cross-origin client is ever added, an explicit allow-list `CORSMiddleware`
must be introduced — flagged for change control, not needed for the pilot.

### 10. Dependency vulnerabilities — PASS (python) / ACCEPTED (web)
**Python** — `pip-audit` over the locked production set (29 runtime packages):
**No known vulnerabilities found.**

**Web** — `pnpm audit`: 2 advisories, both **transitive and dev/build-only**,
below the CI `high` gate and **absent from the production runtime image**
(the Next standalone image ships neither):

| Advisory | Severity | Package | Path | Runtime impact |
|---|---|---|---|---|
| GHSA-qx2v-qp2m-jg93 | moderate | postcss `<8.5.10` | `next > postcss` | build-time CSS only; not shipped |
| GHSA-848j-6mx2-7j84 | low | elliptic | `@storybook/nextjs > …` | Storybook (dev tooling) only |

**Disposition:** accepted for the pilot; tracked. Remediate by bumping the
`postcss` transitive pin and updating Storybook when convenient. Neither
affects served traffic.

### 11. Container & network hardening — PASS
API and web images run as **non-root** (uid 10001 / 10002). In
`docker-compose.prod.yml` the datastores (Postgres, Redis) and the entire
observability stack are `expose`-only — **never published to the host**; only
Nginx binds 80/443. Operational surfaces (`/metrics`, `/health/full`,
`/pilot/status`) are additionally blocked at the Nginx edge.

### 12. CVE scanning in CI — PASS
`.github/workflows/cd.yml` gates every release on: `pip-audit` (python),
`pnpm audit --audit-level high` (web), **Trivy** image scan failing on
HIGH/CRITICAL (SARIF uploaded to code scanning), and **CodeQL** static
analysis (python + js/ts).

## Residual risks (for the go-live register)

1. **Web dev-deps** (postcss/elliptic) — low/moderate, dev/build-only,
   accepted & tracked (§10).
2. **Per-process app rate limiter** — bounded globally by the Nginx edge zone;
   shared Redis limiter deferred (ADR-0019).
3. **No OTel tracing** — request-id log correlation only (see OBSERVABILITY.md).

None is a pilot blocker. Verdict: **cleared for the human-in-the-loop pilot.**
