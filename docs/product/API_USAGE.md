# Athena — API Usage Guide

The backend is API-first (SPEC-08). All application endpoints live under
`/api/v1` and share a standard envelope. This guide shows the common flows.
Operational endpoints (`/health`, `/metrics`, `/pilot/status`) sit outside the
envelope and the ops network restricts the sensitive ones.

> Athena's API produces Decision Objects and reads market/portfolio data. It
> exposes **no** trade-execution or broker endpoints — none exist.

## Response envelope

Every `/api/v1` response is wrapped:

```json
{
  "request_id": "…",
  "timestamp": "2026-07-18T00:00:00Z",
  "status": "ok",
  "data": { },
  "errors": null
}
```

On error, `status` is `"error"` and `errors` is a list of `{code, detail}`.
The `X-Request-ID` response header correlates a call with backend logs — quote
it in bug reports.

## Authentication

JWT bearer tokens. Access tokens are short-lived; refresh tokens are single-use
and rotate on every refresh (reuse is detected).

```bash
# Register (first user is ANALYST; elevate to ADMIN out-of-band)
curl -X POST $BASE/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"…"}'

# Login → access + refresh tokens
curl -X POST $BASE/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"…"}'

# Use the access token
curl $BASE/api/v1/decisions -H "Authorization: Bearer $ACCESS"

# Refresh when the access token expires
curl -X POST $BASE/api/v1/auth/refresh \
  -H 'Content-Type: application/json' \
  -d '{"refresh_token":"'"$REFRESH"'"}'
```

## Decisions

```bash
# List (paginated; optional status filter)
GET /api/v1/decisions?limit=20&offset=0&status=UNDER_REVIEW

# Get one
GET /api/v1/decisions/{id}

# Create (ANALYST/ADMIN)
POST /api/v1/decisions
{ "hypothesis": "…", "probability": 0.62, "confidence": 0.55,
  "decision_type": "ENTRY", "evidence": [ { "source": "…", "category": "…",
  "explanation": "…", "reliability": 0.8, "direction": "SUPPORTING" } ] }

# Update / add evidence / review (ANALYST/ADMIN)
PATCH /api/v1/decisions/{id}
{ "status": "APPROVED", "review_note": "Approved after review" }
```

Decision lifecycle: `DRAFT → UNDER_REVIEW → APPROVED | REJECTED → ARCHIVED`.
Money/probability fields are **decimal strings** on the wire — parse exactly,
don't coerce through binary float where precision matters.

## Portfolios & companies

```bash
GET /api/v1/portfolios?limit=20&offset=0
GET /api/v1/portfolios/{id}
GET /api/v1/companies/{ticker}
GET /api/v1/market/context
```

Some data endpoints return `501 NotImplemented` until their live feed lands;
clients should treat 501 as "not yet available" (the web app falls back to
clearly-labelled sample data).

## Operational endpoints

```bash
GET /health          # liveness → {"status":"ok"}
GET /health/full     # per-component status + pilot_mode (ops network)
GET /pilot/status    # decision-support posture (order_execution:false)
GET /metrics         # Prometheus exposition (ops network)
```

## Errors & retries

- `401` → refresh the token once, then retry; if refresh fails, re-authenticate.
- `403` → insufficient role (RBAC).
- `429` → rate-limited; honor `Retry-After`.
- `5xx`/network → retry with backoff (the official web client retries twice).

## Client reference
The typed TypeScript client in `web/lib/api-client.ts` and services in
`web/services/` implement all of the above (envelope unwrapping, refresh
rotation, retries, request-id surfacing) and are the reference implementation.
