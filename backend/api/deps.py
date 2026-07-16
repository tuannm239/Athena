"""Dependency container and auth guard (SPEC-02 presentation layer wiring)."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session, sessionmaker

from company.domain.repository import CompanyRepository
from decision_kernel.application.use_cases import DecisionUseCases
from identity.application.ports import AuthenticationError
from identity.application.use_cases import AuthenticateUser, RegisterUser
from identity.domain.user import User
from infrastructure.config import Settings
from infrastructure.db.engine import build_engine, build_session_factory
from infrastructure.db.repositories.company import SqlCompanyRepository
from infrastructure.db.repositories.credentials import SqlCredentialStore
from infrastructure.db.repositories.decision import SqlDecisionRepository
from infrastructure.db.repositories.portfolio import SqlPortfolioRepository
from infrastructure.db.repositories.user import SqlUserRepository
from infrastructure.events import InProcessEventBus
from infrastructure.security import Argon2PasswordHasher, JwtTokenService
from portfolio.application.use_cases import PortfolioUseCases


@dataclass
class Container:
    """Wired application services; one per app instance."""

    settings: Settings
    decisions: DecisionUseCases
    portfolios: PortfolioUseCases
    companies: CompanyRepository
    register_user: RegisterUser
    authenticate: AuthenticateUser
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
    tokens = JwtTokenService(cfg)
    return Container(
        settings=cfg,
        decisions=DecisionUseCases(repository=SqlDecisionRepository(sessions), events=bus),
        portfolios=PortfolioUseCases(repository=SqlPortfolioRepository(sessions), events=bus),
        companies=SqlCompanyRepository(sessions),
        register_user=RegisterUser(users, credentials, hasher),
        authenticate=AuthenticateUser(users, credentials, hasher, tokens),
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
    """JWT bearer guard (ADR-0009): requires a valid access token."""
    if credentials is None:
        raise AuthenticationError("missing bearer token")
    return container(request).authenticate.resolve_access_token(credentials.credentials)
