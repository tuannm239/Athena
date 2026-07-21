"""Idempotent production seed (Phase 3 — automatic seed on deploy).

Bootstraps the *minimum* state a fresh deployment needs to be usable:
an initial ADMIN user, created only from environment-provided credentials.
No business data (decisions, portfolios, evidence) is seeded — those are
the user's system of record and must never be fabricated.

Design rules honoured:
  * **Idempotent** — safe to run on every boot. If the admin already
    exists, it is left untouched and the script exits 0.
  * **No hardcoded secrets** — the admin email and password come from
    ATHENA_SEED_ADMIN_EMAIL / ATHENA_SEED_ADMIN_PASSWORD. If either is
    unset, seeding is skipped (exit 0), so a deploy without seed vars
    boots normally.
  * **No business logic** — this is operational bootstrap only.

Usage:
    uv run python -m scripts.seed          # or: python scripts/seed.py
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime, timezone

# Ensure `backend/` is importable when invoked as a bare script.
_BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from sqlalchemy import select  # noqa: E402

from data_pipeline.universe import DEFAULT_UNIVERSE  # noqa: E402
from infrastructure.config import Settings  # noqa: E402
from infrastructure.db.engine import build_engine, build_session_factory  # noqa: E402
from infrastructure.db.models import UserRow  # noqa: E402
from infrastructure.db.repositories.universe import SqlUniverseRepository  # noqa: E402
from infrastructure.security import Argon2PasswordHasher  # noqa: E402

_ACTIVE = "active"
_ADMIN = "ADMIN"


def seed_universe(sessions: object) -> int:
    """Seed the default investment universe once (idempotent). Returns rows added."""
    repo = SqlUniverseRepository(sessions)  # type: ignore[arg-type]
    added = repo.seed_if_empty(DEFAULT_UNIVERSE)
    if added:
        print(f"[seed] Seeded default investment universe: {added} symbols.")
    else:
        print("[seed] Investment universe already populated — nothing to do.")
    return added


def seed() -> int:
    settings = Settings.from_env()
    sessions = build_session_factory(build_engine(settings))

    # The investment universe is operational config, seeded regardless of the
    # optional admin-user vars (idempotent).
    seed_universe(sessions)

    email = os.environ.get("ATHENA_SEED_ADMIN_EMAIL", "").strip().lower()
    password = os.environ.get("ATHENA_SEED_ADMIN_PASSWORD", "")

    if not email or not password:
        print("[seed] ATHENA_SEED_ADMIN_EMAIL/PASSWORD not set — skipping admin seed.")
        return 0

    if len(password) < 8:
        print("[seed] ERROR: ATHENA_SEED_ADMIN_PASSWORD must be at least 8 characters.")
        return 1

    with sessions() as session:
        existing = session.execute(
            select(UserRow).where(UserRow.email == email)
        ).scalar_one_or_none()
        if existing is not None:
            print(f"[seed] Admin user already present ({email}) — nothing to do.")
            return 0

        session.add(
            UserRow(
                id=uuid.uuid4(),
                email=email,
                status=_ACTIVE,
                role=_ADMIN,
                password_hash=Argon2PasswordHasher().hash(password),
                created_at=datetime.now(timezone.utc),
            )
        )
        session.commit()
        print(f"[seed] Created initial ADMIN user: {email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(seed())
