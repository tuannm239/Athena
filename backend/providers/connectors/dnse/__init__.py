"""DNSE OpenAPI market-data connector (Vietnam market).

Infrastructure adapter only (ADR-0003/0017): it maps DNSE OpenAPI responses to
the Athena Provider SDK DTOs and implements the SDK ports. The decision kernel,
risk, portfolio and behaviour packages never import it, and business layers
never see DNSE-specific JSON or exceptions.

DNSE is the *primary* market-data source (prices/indices); VNStock remains the
fallback. Selection is configuration-only (`MARKET_PROVIDER`, `MARKET_FAILOVER`)
via `providers.registry_config` — no business or architecture change.
"""

from __future__ import annotations

from providers.connectors.dnse.exceptions import (
    DnseAuthError,
    DnseError,
    DnseRateLimitError,
    DnseUnavailableError,
)
from providers.connectors.dnse.market_data import DnseProvider, create_dnse_price_provider

__all__ = [
    "DnseAuthError",
    "DnseError",
    "DnseProvider",
    "DnseRateLimitError",
    "DnseUnavailableError",
    "create_dnse_price_provider",
]
