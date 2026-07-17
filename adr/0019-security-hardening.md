# ADR-0019 — Security Hardening (RBAC, API Keys, Token Rotation)

- Status: Accepted (Engineering Authorization)
- Date: 2026-07-16
- Deciders: Engineering

## Problem

ADR-0009 established JWT + Argon2id and deferred roles and API keys.
Phase 2 Module 7 requires production-grade authentication and
authorization: RBAC, machine credentials, refresh-token rotation,
secret management, rate limiting and an auditable trail.

## Decisions

1. **RBAC.** Three roles on the user (`VIEWER` read-only, `ANALYST`
   writes decisions/portfolios, `ADMIN` reserved for administration).
   Roles are checked per-request from the user record (immediately
   revocable), not baked into JWT claims. Registration always creates
   ANALYST; role elevation is an operator action (SQL/ops) until an
   admin API is specified. Enforcement is a FastAPI dependency
   (`require_roles`) on write endpoints; violations map to 403.
2. **API keys.** Format `athena_<token_urlsafe(32)>`; only the sha256
   hex of the raw key is stored (`api_keys` table) with a display
   prefix. The raw key is returned exactly once at creation.
   `X-API-Key` authenticates as the owning user; revocation is a
   timestamp, not a delete (auditability).
3. **Refresh rotation.** Refresh tokens are single-use: issuing
   registers the token's `jti` (`refresh_tokens` table), verification
   atomically consumes it, and any reuse — including of a stolen,
   already-used token — is rejected and audited. Access tokens stay
   stateless (15-minute TTL bounds exposure).
4. **Secret management.** `ATHENA_ENV=production` refuses to start on
   the development JWT secret or any secret under 32 characters
   (`InsecureConfigurationError`). Secrets enter only via environment
   variables; nothing is logged or persisted.
5. **Rate limiting.** In-process token buckets per client host: a
   strict bucket for `/api/v1/auth/*` (default 20/min — credential
   stuffing) and a general bucket (default 240/min); `/health` and
   `/metrics` are exempt; 429 with `Retry-After`. Per-process only —
   a shared Redis limiter is the follow-up when horizontal scaling
   lands.
6. **Audit.** Security events (registration, login success/failure,
   refresh rotation/rejection, API-key create/revoke/reject) are
   written to the SPEC-07 insert-only audit trail with entity type
   `security`. Passwords and raw keys never appear in audit rows.

## Alternatives considered

- Role claims inside the JWT — faster, but revocation lags until token
  expiry; rejected while tokens live 15 minutes and the user lookup is
  already on the request path.
- Storing API keys with Argon2 — unnecessary: keys are 256-bit random,
  so preimage resistance of sha256 suffices and lookups stay indexable.
- Redis-backed rate limiting — deferred until more than one API
  process exists (documented limitation).

## Consequences

- (+) Machine-verified authorization on every write; stolen refresh
  tokens are single-use; keys revocable; production cannot boot with
  dev secrets; brute force is throttled; everything security-relevant
  is in the audit trail.
- (−) Role administration is an ops action for now; rate limits are
  per-process.
