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
from providers.connectors.dnse import create_dnse_price_provider
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
DNSE = "dnse"
# DNSE primary with a VNStock fallback (spec: DNSE is default, VNStock backstops).
DNSE_CHAIN = "dnse_chain"


# Fast per-source settings inside the chain: short timeout + a single attempt so
# a host that *hangs* (e.g. a VN broker silently dropping a foreign datacenter
# IP — seen as ReadTimeout) is abandoned quickly and the next source is tried,
# instead of every ticker stalling for the full default timeout × retries. The
# chain itself is the resilience layer, so per-source retries add little here.
_CHAIN_TIMEOUT = 8.0
_CHAIN_ATTEMPTS = 1


def _create_vn_price_chain() -> object:
    """VN price source with fallback: VNDirect → TCBS → VCI.

    All three are public, token-free feeds; the chain returns the first source
    with data per ticker, so a single host outage (or a retired route) doesn't
    stop the market data flowing. Order reflects what answers a non-VN server
    fastest: VNDirect's CDN-fronted dchart GET first, then TCBS, then VCI
    (Vietcap's trading host — richest source, but slow/hangs from foreign IPs,
    so it is the last resort). Each source is per-ticker tolerant and runs with
    a short timeout so failures fall through quickly.
    """
    return create_chained_price_provider(
        create_vndirect_price_provider(timeout=_CHAIN_TIMEOUT, max_attempts=_CHAIN_ATTEMPTS),
        create_tcbs_price_provider(timeout=_CHAIN_TIMEOUT, max_attempts=_CHAIN_ATTEMPTS),
        create_vci_price_provider(timeout=_CHAIN_TIMEOUT, max_attempts=_CHAIN_ATTEMPTS),
    )


def _create_dnse_price_chain() -> object:
    """DNSE primary with VNStock fallback (spec §4/§5).

    DNSE answers first; if it fails for a ticker (outage, unconfigured creds, a
    changed route) the chain falls through to VNStock so market data never
    stops. Business layers are unaware of the switch (ADR-0017).
    """
    return create_chained_price_provider(
        # Fail fast: openapi.dnse.com.vn can hang for non-VN datacenter IPs
        # (observed as timeouts from Render), so a short timeout + single
        # attempt hands over to VNStock in seconds instead of stalling each
        # ticker for the full retry budget.
        create_dnse_price_provider(timeout=_CHAIN_TIMEOUT, max_attempts=1),
        create_vnstock_price_provider(),
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
    # VN price chain — VNDirect → TCBS → VCI (resilience; ADR-0017).
    registry.register(Capability.PRICE, VN_CHAIN, _create_vn_price_chain)
    # DNSE OpenAPI — the primary market-data source (prices/indices). Lazy: no
    # HTTP or credentials until resolved. `dnse_chain` adds a VNStock fallback.
    registry.register(Capability.PRICE, DNSE, create_dnse_price_provider)
    registry.register(Capability.PRICE, DNSE_CHAIN, _create_dnse_price_chain)
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
# Prices default to vnstock, routed by VNSTOCK_SOURCE (single source, no
# automatic failover — see providers/connectors/vnstock_source.py and
# VNSTOCK_SOURCE_ROUTING.md). The direct-HTTP VN_CHAIN remains registered as an
# explicit opt-in (set the PRICE selection to "vn_chain") but is never the
# default, so sources are never switched silently. Fundamentals and sectors use
# vnstock; global FX to Alpha Vantage.
DEFAULT_SELECTION = {
    Capability.PRICE.value: VNSTOCK,
    Capability.FUNDAMENTAL.value: VNSTOCK,
    Capability.SECTOR.value: VNSTOCK,
    Capability.FX.value: ALPHAVANTAGE,
}


# Registered PRICE sources selectable directly via MARKET_PROVIDER. `vn_chain`
# (VNDirect → TCBS → VCI) is the EOD-friendly option: VNDirect's CDN-fronted
# dchart feed answers from non-VN datacenter IPs (e.g. Render), where VCI and
# DNSE time out — so it keeps daily closes flowing without a VN-local host.
_SELECTABLE_PRICE = frozenset({VNSTOCK, DNSE, VN_CHAIN, VNDIRECT, TCBS, VCI, ALPHAVANTAGE, STATIC})


def market_selection(provider: str | None = None, *, failover: bool = True) -> dict[str, str]:
    """Capability→provider selection for the configured market provider (spec §4).

    `provider` is `MARKET_PROVIDER` (default "dnse"); `failover` is
    `MARKET_FAILOVER`. Only the PRICE capability changes source — DNSE serves
    neither fundamentals nor sector classification, so those stay on VNStock
    (business layers are unaware; ADR-0017).

    * ``dnse``    → DNSE primary, VNStock fallback chain (or DNSE alone if
      failover is off).
    * ``vnstock`` → VNStock alone.
    * any other registered source (``vn_chain``, ``vndirect``, ``tcbs``,
      ``vci``, …) is used directly for PRICE — e.g. ``vn_chain`` for CDN-based
      EOD data that survives a non-VN host.
    """
    chosen = (provider or DNSE).strip().lower()
    if chosen == DNSE:
        price = DNSE_CHAIN if failover else DNSE
    elif chosen in _SELECTABLE_PRICE:
        price = chosen
    else:
        price = VNSTOCK  # unknown value → safe default
    return {**DEFAULT_SELECTION, Capability.PRICE.value: price}
