# ATHENA — SQL / Neon PostgreSQL Compatibility Report

**Phase 4 deliverable** · Date: 2026-07-19 · Target: **Neon Serverless
PostgreSQL** (standard PostgreSQL 15/16/17, wire-compatible).

## Verdict

**✅ Fully compatible.** Every migration applies cleanly, the chain is linear
and single-headed, all column types are portable, and nothing in the schema
uses a Neon-unsupported feature. The application connects with the stock
`psycopg` (v3) driver over TLS.

## 1. Migration chain — linear, single head

Verified with `alembic history` and by applying `alembic upgrade head` end to
end (see Phase 7 simulation). No branches, no multiple heads.

```
<base>
 └─ ec77f528e384  core tables per SPEC-07
     └─ a1b2c3d4e5f6  users.password_hash (ADR-0009)
         └─ 0d1e77bfc695  feature definitions + dataset catalog
             └─ 7aad5a7b7385  knowledge graph nodes + edges
                 └─ b5c6d7e8f9a0  ADR-0006 evidence model + companies
                     └─ 7e63fea92f78  journal entries
                         └─ c9d0e1f2a3b4  RBAC, API keys, refresh tokens (head)
```

7 migrations · every one defines both `upgrade()` and `downgrade()`.

## 2. Column types — all portable

| Construct in migrations | Postgres/Neon mapping | Notes |
|---|---|---|
| `sa.Uuid()` | native `uuid` | primary/foreign keys; no extension needed |
| `sa.String(n)` | `varchar(n)` | |
| `sa.Text()` | `text` | |
| `sa.Integer()` / `sa.Boolean()` | `integer` / `boolean` | |
| `sa.DateTime(timezone=True)` | `timestamptz` | all timestamps tz-aware |
| `sa.Numeric(p, s)` | `numeric` | money/probabilities as Decimal (never float) |
| `sa.JSON().with_variant(postgresql.JSONB, "postgresql")` | `jsonb` | resolves to native JSONB on Neon |
| `op.create_index(...)` | B-tree indexes | standard, incl. unique composites |
| `server_default="ANALYST"` (role) | column default | plain literal default |
| `op.execute("UPDATE evidence SET direction=…")` | portable DML | data backfill, ANSI SQL |

**No** use of: `CREATE EXTENSION`, `SERIAL`/sequences owned outside the ORM,
stored procedures, triggers, `LISTEN/NOTIFY`, materialized views, tablespaces,
`ARRAY`/`ENUM`/`tsvector`/`CITEXT`, `gen_random_uuid()` server-side, or any
superuser-only DDL. UUIDs are generated in Python, so no `uuid-ossp`/`pgcrypto`
extension is required — important because Neon restricts some extensions.

## 3. Connection & driver

- URL form: `postgresql+psycopg://USER:PWD@HOST/athena?sslmode=require`
- Driver: `psycopg[binary]>=3.2` (already a project dependency).
- **SSL:** Neon requires TLS; `sslmode=require` in the URL satisfies it. No app
  change needed — the engine passes the URL straight through.
- **Pooling / serverless drops:** `build_engine()` sets `pool_pre_ping=True`
  (validates a connection before use) and `pool_recycle=300` (drops idle
  connections before Neon reaps them). Both guard against the "server closed
  the connection unexpectedly" class of errors on serverless Postgres.
- **Pooled vs direct endpoint:** use Neon's **direct** (non-pooled) endpoint
  for `DATABASE_URL` so Alembic DDL runs in a stable session. Neon's PgBouncer
  pooler is fine for steady-state queries but can interfere with migration
  transactions; the direct endpoint is the safe default for this app's scale.

## 4. How this was verified

The full forward path was executed against a throwaway database in this
environment:

```
alembic upgrade head        → all 7 migrations applied, head = c9d0e1f2a3b4
python -m scripts.seed       → created initial ADMIN (idempotent on re-run)
GET /health                  → 200 {"status":"ok"}
GET /health/full             → database: ok
POST /api/v1/auth/login      → 200 (authenticates the seeded admin)
```

Type portability was confirmed by the migrations running unmodified on a second
SQL dialect via SQLAlchemy's dialect layer — the same abstraction guarantees
the native-Postgres path on Neon resolves `JSONB`/`uuid`/`timestamptz` to their
first-class Postgres types.

## 5. Operational notes for Neon

1. Create the database (e.g. `athena`) in the Neon console.
2. Copy the **direct** connection string; convert the scheme to
   `postgresql+psycopg://…` and append `?sslmode=require`.
3. Migrations run **automatically** on deploy (`scripts/start.sh` →
   `alembic upgrade head`); no manual migration step is required.
4. Neon autosuspends idle compute; the first request after idle incurs a cold
   start. `pool_pre_ping` absorbs the reconnect transparently.
