"""Engine and session factory (SPEC-07).

Sessions are provided through a context manager so repositories never
manage global state (no hidden state rule).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from infrastructure.config import Settings


def build_engine(settings: Settings | None = None) -> Engine:
    cfg = settings or Settings.from_env()
    # pool_pre_ping validates a connection before use, and pool_recycle drops
    # connections older than 5 min — both guard against a managed/serverless
    # Postgres (e.g. Neon) silently closing idle connections. TLS (sslmode) is
    # carried in the DATABASE_URL, so no code change is needed to require it.
    return create_engine(cfg.database_url, pool_pre_ping=True, pool_recycle=300)


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    """Transactional scope: commit on success, rollback on error."""
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
