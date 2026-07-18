"""Production provider registry assembly (Phase 5, W5).

Registers the available connectors as configuration-selectable factories.
The active provider per capability is chosen by configuration (env /
Settings), so vendors swap without code changes (ADR-0017). Factories are
lazy — nothing hits the network or requires credentials until resolved.
"""

from __future__ import annotations

from providers.connectors.alphavantage import (
    create_alphavantage_fx_provider,
    create_alphavantage_price_provider,
)
from providers.connectors.static import StaticProvider
from providers.sdk.registry import Capability, ProviderRegistry

ALPHAVANTAGE = "alphavantage"
STATIC = "static"


def build_registry() -> ProviderRegistry:
    """The default registry: Alpha Vantage (production) + static (offline)."""
    registry = ProviderRegistry()
    # production HTTP adapter (credentials read from env at resolve time)
    registry.register(Capability.PRICE, ALPHAVANTAGE, create_alphavantage_price_provider)
    registry.register(Capability.FX, ALPHAVANTAGE, create_alphavantage_fx_provider)
    # deterministic offline fallback for dev / tests / demos
    registry.register(Capability.PRICE, STATIC, StaticProvider)
    registry.register(Capability.FX, STATIC, StaticProvider)
    return registry


# Default selection maps a capability -> provider name; overridable via config.
DEFAULT_SELECTION = {
    Capability.PRICE.value: ALPHAVANTAGE,
    Capability.FX.value: ALPHAVANTAGE,
}
