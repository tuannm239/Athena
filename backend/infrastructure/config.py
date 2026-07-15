"""Typed runtime configuration (SPEC-07 stores).

Values come from the environment; defaults match docker-compose.yml so a
local checkout works without extra setup. No secrets are hardcoded —
these defaults are development-only credentials.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    redis_url: str
    duckdb_dir: str
    jwt_secret: str
    access_token_ttl_seconds: int
    refresh_token_ttl_seconds: int

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            database_url=os.environ.get(
                "DATABASE_URL", "postgresql+psycopg://athena:athena@localhost:5432/athena"
            ),
            redis_url=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
            duckdb_dir=os.environ.get("DUCKDB_DIR", "data/snapshots"),
            jwt_secret=os.environ.get("JWT_SECRET", "dev-only-secret-change-me"),
            access_token_ttl_seconds=int(os.environ.get("ACCESS_TOKEN_TTL", "900")),
            refresh_token_ttl_seconds=int(os.environ.get("REFRESH_TOKEN_TTL", "1209600")),
        )
