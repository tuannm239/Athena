# ADR-0009 — Authentication Strategy

- Status: Accepted
- Date: 2026-07-15
- Deciders: Engineering
- Resolves: SPEC-08 §Authentication scope for the API sprint (R3)

## Context

SPEC-08 names OAuth2/JWT, role-based authorization, refresh tokens, and API
keys. SPEC-07's `users` table defines no credential storage and no role
column; no spec defines role semantics.

## Decision

1. **JWT bearer auth first**: OAuth2 password flow — register/login issue an
   access token (short TTL) and a refresh token (long TTL); `POST /auth/refresh`
   rotates the pair. Library: **PyJWT** (typed, minimal).
2. **Password hashing: Argon2id** via `argon2-cffi`.
3. **Credential storage**: nullable `password_hash` column added to `users`
   (forward-only migration 0002). Credentials are infrastructure state — the
   domain `User` entity stays credential-free.
4. **Roles deferred**: no spec defines roles; the auth guard authenticates and
   requires `status == "active"`. Role claims will be added when a spec
   defines them (SPEC-02 names an Administrator persona only).
5. **API keys deferred** to the integration phase.

## Consequences

- (+) SPEC-08 endpoints ship protected now; scope creep avoided.
- (−) Role-based authorization and API keys remain open items (GAP F8/T4
  partially; tracked in IMPLEMENTATION_BACKLOG B-05 follow-ups).
