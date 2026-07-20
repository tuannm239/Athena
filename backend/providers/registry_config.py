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
from providers.connectors.tcbs_provider import create_tcbs_price_provider
from providers.connectors.vnstock_provider import (
    create_vnstock_fundamental_provider,
    create_vnstock_price_provider,
    create_vnstock_sector_provider,
)
from providers.sdk.registry import Capability, ProviderRegistry

ALPHAVANTAGE = "alphavantage"
STATIC = "static"
VNSTOCK = "vnstock"
TCBS = "tcbs"


def build_registry() -> ProviderRegistry:
    """The default registry: Alpha Vantage + vnstock (production) + static."""
    registry = ProviderRegistry()
    # production HTTP adapter (credentials read from env at resolve time)
    registry.register(Capability.PRICE, ALPHAVANTAGE, create_alphavantage_price_provider)
    registry.register(Capability.FX, ALPHAVANTAGE, create_alphavantage_fx_provider)
    # TCBS — Vietnam market prices via a light public HTTP API (indices + stocks).
    # Server-friendly (plain httpx/JSON, no library/telemetry/$HOME writes).
    registry.register(Capability.PRICE, TCBS, create_tcbs_price_provider)
    # vnstock — Vietnam market (OHLCV incl. VNINDEX/VN30, fundamentals, sectors).
    # Factories are lazy; nothing imports vnstock or hits the network until resolved.
    registry.register(Capability.PRICE, VNSTOCK, create_vnstock_price_provider)
    registry.register(Capability.FUNDAMENTAL, VNSTOCK, create_vnstock_fundamental_provider)
    registry.register(Capability.SECTOR, VNSTOCK, create_vnstock_sector_provider)
    # deterministic offline fallback for dev / tests / demos
    registry.register(Capability.PRICE, STATIC, StaticProvider)
    registry.register(Capability.FX, STATIC, StaticProvider)
    return registry


# Default selection maps a capability -> provider name; overridable via config.
# Prices default to TCBS (light, server-friendly, works on Render); fundamentals
# and sectors still use vnstock; global FX to Alpha Vantage.
DEFAULT_SELECTION = {
    Capability.PRICE.value: TCBS,
    Capability.FUNDAMENTAL.value: VNSTOCK,
    Capability.SECTOR.value: VNSTOCK,
    Capability.FX.value: ALPHAVANTAGE,
}
