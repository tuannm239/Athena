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

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            database_url=os.environ.get(
                "DATABASE_URL", "postgresql+psycopg://athena:athena@localhost:5432/athena"
            ),
            redis_url=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
            duckdb_dir=os.environ.get("DUCKDB_DIR", "data/snapshots"),
            jwt_secret=os.environ.get("JWT_SECRET", _DEV_JWT_SECRET),
            access_token_ttl_seconds=int(os.environ.get("ACCESS_TOKEN_TTL", "900")),
            refresh_token_ttl_seconds=int(os.environ.get("REFRESH_TOKEN_TTL", "1209600")),
            environment=os.environ.get("ATHENA_ENV", "development"),
            rate_limit_per_minute=int(os.environ.get("RATE_LIMIT_PER_MINUTE", "240")),
            auth_rate_limit_per_minute=int(os.environ.get("AUTH_RATE_LIMIT_PER_MINUTE", "20")),
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
