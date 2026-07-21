"""Dependency container and auth guard (SPEC-02 presentation layer wiring)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session, sessionmaker

from company.domain.repository import CompanyRepository
from data_pipeline.application.use_cases import DataPipelineUseCases
from data_pipeline.universe import UniverseRepository
from decision_kernel.application.use_cases import DecisionUseCases
from identity.application.ports import AuthenticationError, AuthorizationError
from identity.application.use_cases import ApiKeyService, AuthenticateUser, RegisterUser
from identity.domain.user import Role, User
from infrastructure.config import Settings
from infrastructure.db.engine import build_engine, build_session_factory
from infrastructure.db.repositories.company import SqlCompanyRepository
from infrastructure.db.repositories.credentials import SqlCredentialStore
from infrastructure.db.repositories.dataset_catalog import SqlDatasetCatalog
from infrastructure.db.repositories.decision import SqlDecisionRepository
from infrastructure.db.repositories.portfolio import SqlPortfolioRepository
from infrastructure.db.repositories.security_stores import (
    SqlApiKeyStore,
    SqlRefreshTokenStore,
    SqlSecurityAuditLog,
)
from infrastructure.db.repositories.universe import SqlUniverseRepository
from infrastructure.db.repositories.user import SqlUserRepository
from infrastructure.events import InProcessEventBus
from infrastructure.market_read import PublishedMarketPriceReader
from infrastructure.security import Argon2PasswordHasher, JwtTokenService
from infrastructure.sql_snapshot_store import build_snapshot_store
from market.application.read_model import VnMarketSnapshotQuery
from portfolio.application.use_cases import PortfolioUseCases


@dataclass
class Container:
    """Wired application services; one per app instance."""

    settings: Settings
    sessions: sessionmaker[Session]
    decisions: DecisionUseCases
    portfolios: PortfolioUseCases
    companies: CompanyRepository
    universe: UniverseRepository
    market_snapshot: VnMarketSnapshotQuery
    register_user: RegisterUser
    authenticate: AuthenticateUser
    api_keys: ApiKeyService
    event_bus: InProcessEventBus


def build_container(
    settings: Settings | None = None,
    session_factory: sessionmaker[Session] | None = None,
) -> Container:
    cfg = settings or Settings.from_env()
    sessions = session_factory or build_session_factory(build_engine(cfg))
    bus = InProcessEventBus()
    users = SqlUserRepository(sessions)
    credentials = SqlCredentialStore(sessions)
    hasher = Argon2PasswordHasher()
    audit = SqlSecurityAuditLog(sessions)
    api_key_store = SqlApiKeyStore(sessions)
    tokens = JwtTokenService(cfg, refresh_store=SqlRefreshTokenStore(sessions))
    # Read-only market snapshot query over the pipeline's *published* prices
    # (composition root wiring; the query depends only on the reader port).
    pipeline_read = DataPipelineUseCases(
        catalog=SqlDatasetCatalog(sessions),
        snapshots=build_snapshot_store(cfg, sessions),
    )
    market_snapshot = VnMarketSnapshotQuery(reader=PublishedMarketPriceReader(pipeline_read))
    return Container(
        settings=cfg,
        sessions=sessions,
        decisions=DecisionUseCases(repository=SqlDecisionRepository(sessions), events=bus),
        portfolios=PortfolioUseCases(repository=SqlPortfolioRepository(sessions), events=bus),
        companies=SqlCompanyRepository(sessions),
        universe=SqlUniverseRepository(sessions),
        market_snapshot=market_snapshot,
        register_user=RegisterUser(users, credentials, hasher, audit=audit),
        authenticate=AuthenticateUser(
            users, credentials, hasher, tokens, audit=audit, api_keys=api_key_store
        ),
        api_keys=ApiKeyService(users, api_key_store, audit=audit),
        event_bus=bus,
    )


def container(request: Request) -> Container:
    result = request.app.state.container
    assert isinstance(result, Container)
    return result


_bearer = HTTPBearer(auto_error=False)


def current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> User:
    """Auth guard (ADR-0009/0019): JWT bearer token or X-API-Key."""
    api_key = request.headers.get("X-API-Key")
    if api_key is not None:
        return container(request).authenticate.resolve_api_key(api_key)
    if credentials is None:
        raise AuthenticationError("missing bearer token or API key")
    return container(request).authenticate.resolve_access_token(credentials.credentials)


def require_roles(*roles: Role) -> Callable[..., User]:
    """RBAC guard (ADR-0019): authenticated user must hold one of the roles."""

    def guard(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise AuthorizationError(f"requires one of roles: {', '.join(roles)}")
        return user

    return guard


writer = require_roles(Role.ANALYST, Role.ADMIN)
"""Write access to decisions and portfolios (VIEWER is read-only)."""
