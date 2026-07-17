# ATHENA — OWASP Top 10 (2021) Security Review

Reviewed: 2026-07-16 (Phase 2 Module 7). Scope: backend API, auth stack,
data pipeline, LLM gateway. Verdicts: **Mitigated** (controls in place,
tested) · **Partial** (controls in place, known limitation) ·
**N/A** (surface does not exist yet).

| # | Category | Verdict | Evidence / Notes |
|---|----------|---------|------------------|
| A01 | Broken Access Control | Mitigated | RBAC via `require_roles` on write endpoints (403 tested); portfolios scoped to owner (`get_owned`); API keys resolvable only to their owning user. Admin surface does not exist yet, so no vertical-escalation path is exposed. |
| A02 | Cryptographic Failures | Mitigated | Argon2id password hashing (ADR-0009); API keys stored as sha256 of 256-bit random values, raw shown once; JWT HS256 with production secret policy (≥32 chars, no dev default — startup-enforced); no PII beyond email is stored. TLS termination is deployment-level (RUNBOOK). |
| A03 | Injection | Mitigated | SQLAlchemy 2.x bound parameters everywhere; architecture test proves no SQL outside `infrastructure`; Pydantic v2 validates every request body; no shell-outs, no string-built queries. |
| A04 | Insecure Design | Mitigated | Decision Kernel isolated from LLMs by import-path tests (ADR-0003, both directions); evidence requires explicit human review before it can influence a decision; risk-before-return enforced by the kernel. |
| A05 | Security Misconfiguration | Partial | Production refuses dev secrets (`InsecureConfigurationError`); rate limits and TTLs are configuration with safe defaults. Remaining: `/metrics` and `/health/full` should be network-restricted in deployment (documented in RUNBOOK); CORS not configured (no browser frontend yet). |
| A06 | Vulnerable & Outdated Components | Partial | Dependency set is small and pinned by `uv.lock`; CI installs from the lock. No automated CVE scanning yet — recommended follow-up: `pip-audit`/Dependabot in CI. |
| A07 | Identification & Authentication Failures | Mitigated | Argon2id; login throttled (20/min/host bucket); refresh tokens single-use with reuse detection (tested); access tokens 15 min; API keys revocable; all auth events audited. No password-reset flow exists yet (no email channel) — tracked in backlog. |
| A08 | Software & Data Integrity Failures | Mitigated | Forward-only migrations; insert-only audit trail; immutable dataset snapshots with lineage and quality gates; LLM-derived artifacts lineage-tagged and inert until human review. CI runs lint/type/test gates on every push. |
| A09 | Security Logging & Monitoring Failures | Mitigated | Structured JSON logs with request-id correlation; security audit trail (registrations, logins, rotations, key lifecycle); Prometheus metrics with error-share dashboard. Alerting rules are deployment-specific (RUNBOOK). |
| A10 | Server-Side Request Forgery | Partial | The only outbound HTTP surfaces are provider connectors and LLM adapters, both with fixed, configuration-supplied base URLs — no user-supplied URLs are fetched anywhere. If document-by-URL ingestion is ever added to the Research Copilot, an allowlist is mandatory. |

## Prioritized follow-ups

1. CVE scanning in CI (`pip-audit` or Dependabot) — A06.
2. Network policy for `/metrics`, `/health/full`, Prometheus and
   Grafana in production deployments — A05.
3. Shared (Redis) rate limiter when the API scales horizontally —
   A07 (per-process buckets today, ADR-0019).
4. Password reset + email verification once a notification channel
   exists (C3/ADR-0012) — A07.
