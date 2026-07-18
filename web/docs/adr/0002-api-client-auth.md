# FE-ADR-0002 — Typed API client, JWT + refresh rotation

- Status: Accepted · Date: 2026-07-18

## Decision
A single typed `apiRequest` (SPEC-08 envelope unwrap) with: bearer auth
from an in-memory access token; **transparent single-flight refresh-token
rotation** on 401; retry-with-backoff for transient network/5xx; and
`X-Request-ID` surfaced on errors for backend log correlation. Wire types
in `types/api.ts` mirror the backend Pydantic schemas.

## Consequences
- Access token in memory (XSS-safer); refresh token in localStorage — a
  future hardening moves it to an httpOnly cookie once the backend sets one.
- RBAC is displayed client-side but **enforced server-side**; the client is
  never the authority.
