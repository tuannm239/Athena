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
from providers.connectors.chained_price import create_chained_price_provider
from providers.connectors.static import StaticProvider
from providers.connectors.tcbs_provider import create_tcbs_price_provider
from providers.connectors.vci_provider import create_vci_price_provider
from providers.connectors.vndirect_provider import create_vndirect_price_provider
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
VNDIRECT = "vndirect"
VCI = "vci"
VN_CHAIN = "vn_chain"


def _create_vn_price_chain() -> object:
    """VN price source with fallback: VCI → VNDirect → TCBS.

    All three are public, token-free feeds; the chain returns the first source
    with data per ticker, so a single host outage (or a retired route) doesn't
    stop the market data flowing. VCI (Vietcap — vnstock's default source) is
    tried first, then VNDirect's dchart feed, then TCBS. Each source is
    per-ticker tolerant.
    """
    return create_chained_price_provider(
        create_vci_price_provider(),
        create_vndirect_price_provider(),
        create_tcbs_price_provider(),
    )


def build_registry() -> ProviderRegistry:
    """The default registry: Alpha Vantage + vnstock (production) + static."""
    registry = ProviderRegistry()
    # production HTTP adapter (credentials read from env at resolve time)
    registry.register(Capability.PRICE, ALPHAVANTAGE, create_alphavantage_price_provider)
    registry.register(Capability.FX, ALPHAVANTAGE, create_alphavantage_fx_provider)
    # VCI (Vietcap) — Vietnam market prices via the public OHLC chart feed
    # (POST/JSON; vnstock's default source). Token-free; primary VN source.
    registry.register(Capability.PRICE, VCI, create_vci_price_provider)
    # VNDirect — Vietnam market prices via the public dchart (TradingView UDF)
    # feed. Token-free and server-friendly (plain httpx/JSON).
    registry.register(Capability.PRICE, VNDIRECT, create_vndirect_price_provider)
    # TCBS — Vietnam market prices via a light public HTTP API (indices + stocks).
    # Server-friendly, kept as a fallback source inside the VN chain.
    registry.register(Capability.PRICE, TCBS, create_tcbs_price_provider)
    # VN price chain — VCI → VNDirect → TCBS (resilience; ADR-0017).
    registry.register(Capability.PRICE, VN_CHAIN, _create_vn_price_chain)
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
# Prices default to the VN chain (VCI → VNDirect → TCBS — all token-free,
# server-friendly, works on Render); fundamentals and sectors still use vnstock;
# global FX to Alpha Vantage.
DEFAULT_SELECTION = {
    Capability.PRICE.value: VN_CHAIN,
    Capability.FUNDAMENTAL.value: VNSTOCK,
    Capability.SECTOR.value: VNSTOCK,
    Capability.FX.value: ALPHAVANTAGE,
}
