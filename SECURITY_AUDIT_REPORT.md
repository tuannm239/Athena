# ATHENA — Security Audit Report (Phase 3, Verification 2)

Date: 2026-07-17 · Method: full auth/security test suite (27 passed) +
10 live adversarial probes against the running app (tampered/forged
JWT, SQL injection, credential storage inspection, error-leak checks,
rate limiting). **Every probe passed. No vulnerabilities found.**

## 1. Authentication

- Passwords hashed with **Argon2id** (`argon2-cffi` defaults). Probe
  inspected the stored value: `$argon2id$v=19$m=65536,...` — the
  plaintext never appears. ✅
- Login is constant-response on unknown user vs bad password (both
  `AuthenticationError` → 401), and every attempt is audited
  (`auth.login.success` / `auth.login.failure`). ✅
- Unauthenticated access to a protected route returns 401
  (probe: unauth write → 401). ✅

## 2. Authorization (RBAC — ADR-0019)

- Roles VIEWER/ANALYST/ADMIN enforced per request via `require_roles`;
  a VIEWER's write attempt returns 403 `Forbidden`
  (`test_security.py::TestRbac`). ✅
- Roles are read from the user record on each request (not from JWT
  claims), so revocation/downgrade takes effect immediately. ✅
- Portfolio access is owner-scoped (`get_owned`); one user cannot read
  another's portfolio. ✅

## 3. API keys

- Format `athena_<token_urlsafe(32)>` (256-bit entropy). Probe
  confirmed the DB stores **only** the sha256 hex; the raw key is
  absent from storage and returned exactly once at creation. ✅
- `X-API-Key` authenticates as the owning user; revocation is a
  timestamp and immediately rejects the key (401) — verified in the
  lifecycle test. ✅

## 4. JWT

- HS256 with the decoder **pinned to `algorithms=["HS256"]`**, which
  defeats `alg=none` and RS/HS confusion attacks.
- Probes: tampered token → 401; token forged with the wrong secret →
  401. ✅
- Refresh tokens are single-use (jti registry); reuse of a consumed
  token → 401 (rotation with reuse detection). ✅
- Access-token TTL 15 min bounds exposure of a leaked token.

## 5. Secrets

- Production startup refuses the dev default or any secret < 32 chars
  (`InsecureConfigurationError`) — `test_security.py::TestSecretManagement`. ✅
- Secrets are read from environment only; no secret is written to logs
  (the access log records method/path/status/duration/request-id only —
  never headers or bodies) or persisted. ✅
- Provider/LLM API keys are constructor-injected at the composition
  root; adapters never log them.

## 6. Logging

- Structured JSON logs with `request_id` correlation; kernel logs
  `decision_id`. Probe confirmed `X-Request-ID` is echoed on every
  response for end-to-end correlation. ✅
- Security audit trail (insert-only, SPEC-07) records registrations,
  login success/failure, refresh rotation/rejection and API-key
  lifecycle with `entity_type=security`; subject/detail carry no
  secrets. ✅

## 7. Injection

- All persistence uses SQLAlchemy 2.x bound parameters; an
  architecture test proves no SQL exists outside `infrastructure`.
- Probes:
  - SQLi in login email (`a@x.com' OR '1'='1`) → 401, no bypass. ✅
  - SQLi payload as a decision hypothesis (`'; DROP TABLE decisions; --`)
    → stored **literally** (round-trips byte-for-byte), table intact,
    subsequent list returns 200. ✅
- Request bodies are validated by Pydantic v2 (type/range) before
  reaching any use case.

## 8. OWASP Top 10 (2021) — verified verdicts

| # | Category | Verdict | Probe / test evidence |
|---|---|---|---|
| A01 | Broken Access Control | ✅ Mitigated | 401 unauth write; 403 VIEWER write; owner-scoped portfolios |
| A02 | Cryptographic Failures | ✅ Mitigated | Argon2id password; sha256-only API keys; ≥32-char prod JWT secret |
| A03 | Injection | ✅ Mitigated | SQLi in email and hypothesis both neutralized; bound params only |
| A04 | Insecure Design | ✅ Mitigated | LLM/kernel isolation (both directions, tested); evidence needs human review |
| A05 | Security Misconfiguration | ⚠️ Partial | prod secret policy enforced; **deploy-time**: restrict `/metrics`,`/health/full`, set CORS (no browser client yet) |
| A06 | Vulnerable Components | ⚠️ Partial | small pinned dep set (`uv.lock`); add CVE scanning (pip-audit/Dependabot) in CI |
| A07 | Auth Failures | ✅ Mitigated | throttled login (429); single-use refresh; short access TTL; forged/tampered JWT rejected |
| A08 | Data Integrity Failures | ✅ Mitigated | forward-only migrations; insert-only audit; immutable snapshots + lineage; CI gates |
| A09 | Logging/Monitoring Failures | ✅ Mitigated | request-id logs; security audit trail; Prometheus error-share dashboard |
| A10 | SSRF | ⚠️ Partial | only fixed, config-supplied upstream URLs; **if** URL-ingestion is ever added, allowlist required |

## Probe transcript (verbatim)

```
[PASS] unauth write -> 401
[PASS] tampered JWT -> 401
[PASS] forged JWT (wrong secret) -> 401
[PASS] password stored as $argon2id$v=19$m=655...
[PASS] api key stored as sha256, raw absent
[PASS] SQLi login attempt -> 401
[PASS] SQLi in hypothesis stored literally, table intact (201)
[PASS] error response has no stack/internal leak (400)
[PASS] X-Request-ID echoed for correlation
[PASS] auth rate limit engaged: [401, 401, 429, 429]
```

## Findings & recommendations

No exploitable vulnerability found. Three **deployment-time** hardening
items (not code defects) carry over from the Phase 2 review:

1. **A06** — add CVE scanning (pip-audit / Dependabot) to CI. *(Highest
   priority; ongoing.)*
2. **A05** — network-restrict `/metrics`, `/health/full`, Prometheus
   and Grafana; configure CORS if/when a browser client is introduced.
3. **A10** — if document-by-URL ingestion is ever added to the Research
   Copilot, gate outbound fetches behind an allowlist.

## Verdict

**PASS.** Authentication, authorization, API keys, JWT handling, secret
management, logging and injection defenses are all verified by live
adversarial probes and the automated suite. No defects; implementation
unchanged. Residual items are deployment configuration and CI tooling,
not application vulnerabilities.
