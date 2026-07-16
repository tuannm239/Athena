"""Unit tests — Data Provider SDK (Phase 2, Module 1)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from providers.sdk.models import PriceBar
from providers.sdk.registry import Capability, ProviderError, ProviderRegistry


class TestModels:
    def test_price_bar_validation(self) -> None:
        with pytest.raises(ValueError):
            PriceBar(ticker="AAA", day=date(2026, 1, 5), close=Decimal(0))


class TestRegistry:
    def test_config_driven_selection(self) -> None:
        registry = ProviderRegistry()
        registry.register(Capability.PRICE, "static", lambda: "static-provider")
        registry.register(Capability.PRICE, "local", lambda: "local-provider")
        assert registry.names(Capability.PRICE) == ("local", "static")
        assert registry.resolve(Capability.PRICE, {"price": "local"}) == "local-provider"

    def test_unknown_provider_and_capability(self) -> None:
        registry = ProviderRegistry()
        registry.register(Capability.PRICE, "static", lambda: object())
        with pytest.raises(ProviderError):
            registry.resolve(Capability.PRICE, {"price": "nope"})
        with pytest.raises(ProviderError):
            registry.resolve(Capability.FX, {"price": "static"})

    def test_duplicate_registration_rejected(self) -> None:
        registry = ProviderRegistry()
        registry.register(Capability.FX, "static", lambda: object())
        with pytest.raises(ProviderError):
            registry.register(Capability.FX, "static", lambda: object())
