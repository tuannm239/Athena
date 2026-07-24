"""Typed runtime configuration (SPEC-07 stores; ADR-0019 secrets).

Values come from the environment; defaults match docker-compose.yml so a
local checkout works without extra setup. No secrets are hardcoded —
these defaults are development-only credentials, and a production
environment refuses to start on the default JWT secret.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

_DEV_JWT_SECRET = "dev-only-secret-change-me"
_MIN_PRODUCTION_SECRET_LENGTH = 32

PRODUCTION = "production"


class InsecureConfigurationError(RuntimeError):
    """Production startup blocked by an unsafe setting (ADR-0019)."""


def normalize_database_url(url: str) -> str:
    """Force the psycopg (v3) driver, whatever Postgres URL form is supplied.

    Managed providers (Neon, Render, Heroku, Supabase) hand out URLs like
    ``postgresql://…`` or ``postgres://…``. SQLAlchemy maps the bare
    ``postgresql://`` scheme to the legacy psycopg2 dialect, which this image
    does not ship (we install psycopg v3). Rewriting the scheme to
    ``postgresql+psycopg://`` makes any of those URLs work unchanged — the
    operator never has to hand-edit the connection string. Non-Postgres URLs
    (e.g. sqlite://) pass through untouched.
    """
    for prefix in ("postgresql+psycopg2://", "postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    redis_url: str
    duckdb_dir: str
    jwt_secret: str
    access_token_ttl_seconds: int
    refresh_token_ttl_seconds: int
    environment: str = "development"
    rate_limit_per_minute: int = 240
    auth_rate_limit_per_minute: int = 20
    # Pilot mode (Phase 5, W6): an operational assertion that the platform is
    # running as a decision-support system only — read-only w.r.t. markets, no
    # order execution, no broker integration, human approval mandatory. Athena
    # has no execution path by construction (Phase 3 Shadow Mode); this flag
    # surfaces the posture to operators and gates the daily pilot report.
    pilot_mode: bool = False
    # Vietnam market data source routed into the vnstock adapter (Quote,
    # Listing, Trading, Company, Financial). Never hardcoded at a call site —
    # the adapter reads this. Validated against the installed vnstock's
    # supported sources by providers.connectors.vnstock_source.resolve_source.
    vnstock_source: str = "vci"
    # Snapshot store backend for the Data Pipeline's immutable snapshots:
    #   "duckdb" (default) — local DuckDB files under DUCKDB_DIR (fast, but lost
    #            when the disk is ephemeral, e.g. a free-tier container restart);
    #   "sql"    — Parquet bytes in the relational DB (Postgres/Neon), durable
    #            across restarts. Set SNAPSHOT_BACKEND=sql on ephemeral hosts.
    snapshot_backend: str = "duckdb"
    # Active market-data provider (ADR-0017; infrastructure-only selection):
    #   "dnse"    (default) — DNSE OpenAPI as the primary source;
    #   "vnstock"           — the VNStock adapter.
    # With `market_failover` true (default) the primary is tried first and
    # VNStock backstops it per ticker, so a DNSE outage never stops the data.
    # Business layers are unaware — they consume the SDK ports only.
    market_provider: str = "dnse"
    market_failover: bool = True

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            database_url=normalize_database_url(
                os.environ.get(
                    "DATABASE_URL", "postgresql+psycopg://athena:athena@localhost:5432/athena"
                )
            ),
            redis_url=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
            duckdb_dir=os.environ.get("DUCKDB_DIR", "data/snapshots"),
            jwt_secret=os.environ.get("JWT_SECRET", _DEV_JWT_SECRET),
            access_token_ttl_seconds=int(os.environ.get("ACCESS_TOKEN_TTL", "900")),
            refresh_token_ttl_seconds=int(os.environ.get("REFRESH_TOKEN_TTL", "1209600")),
            environment=os.environ.get("ATHENA_ENV", "development"),
            rate_limit_per_minute=int(os.environ.get("RATE_LIMIT_PER_MINUTE", "240")),
            auth_rate_limit_per_minute=int(os.environ.get("AUTH_RATE_LIMIT_PER_MINUTE", "20")),
            pilot_mode=os.environ.get("ATHENA_PILOT_MODE", "false").lower() in ("1", "true", "yes"),
            vnstock_source=os.environ.get("VNSTOCK_SOURCE", "vci").strip().lower() or "vci",
            snapshot_backend=os.environ.get("SNAPSHOT_BACKEND", "duckdb").strip().lower()
            or "duckdb",
            market_provider=os.environ.get("MARKET_PROVIDER", "dnse").strip().lower() or "dnse",
            market_failover=os.environ.get("MARKET_FAILOVER", "true").lower()
            in ("1", "true", "yes"),
        )

    def ensure_safe_for_environment(self) -> None:
        """Fail fast in production on development-grade secrets (ADR-0019)."""
        if self.environment != PRODUCTION:
            return
        if self.jwt_secret == _DEV_JWT_SECRET:
            raise InsecureConfigurationError(
                "JWT_SECRET is the development default; set a real secret in production"
            )
        if len(self.jwt_secret) < _MIN_PRODUCTION_SECRET_LENGTH:
            raise InsecureConfigurationError(
                f"JWT_SECRET must be at least {_MIN_PRODUCTION_SECRET_LENGTH} characters "
                "in production"
            )
