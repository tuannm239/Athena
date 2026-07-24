"""DNSE provider — auth, retry/error-translation, mapping, failover, selection.

Every DNSE response is mocked through the injectable transport/client seams, so
these tests never require real credentials or a network (spec §10).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Mapping

import pytest

from providers.connectors.chained_price import create_chained_price_provider
from providers.connectors.dnse.auth import DnseAuthenticator
from providers.connectors.dnse.client import DnseMarketClient, raise_for_status
from providers.connectors.dnse.config import DnseConfig, redact_headers
from providers.connectors.dnse.exceptions import (
    DnseAuthError,
    DnseError,
    DnseRateLimitError,
    DnseUnavailableError,
)
from providers.connectors.dnse.market_data import DnseProvider, create_dnse_price_provider
from providers.registry_config import DNSE, DNSE_CHAIN, VNSTOCK, market_selection
from providers.sdk.models import PriceBar

Json = Mapping[str, object]


class FakeTransport:
    """Scripted transport: each call pops the next result (or raises it)."""

    def __init__(self, get: list[object] | None = None, post: list[object] | None = None) -> None:
        self._get = list(get or [])
        self._post = list(post or [])
        self.get_calls: list[tuple[str, dict[str, str], dict[str, str]]] = []
        self.post_calls: list[tuple[str, dict[str, object], dict[str, str]]] = []

    def get_json(
        self, url: str, params: Mapping[str, str], headers: Mapping[str, str], timeout: float
    ) -> Json:
        self.get_calls.append((url, dict(params), dict(headers)))
        item = self._get.pop(0)
        if isinstance(item, Exception):
            raise item
        assert isinstance(item, dict)
        return item

    def post_json(
        self, url: str, body: Mapping[str, object], headers: Mapping[str, str], timeout: float
    ) -> Json:
        self.post_calls.append((url, dict(body), dict(headers)))
        item = self._post.pop(0)
        if isinstance(item, Exception):
            raise item
        assert isinstance(item, dict)
        return item


def _client(transport: FakeTransport, config: DnseConfig | None = None) -> DnseMarketClient:
    cfg = config or DnseConfig(base_url="https://dnse.test", max_attempts=3, base_delay_seconds=0.0)
    slept: list[float] = []
    return DnseMarketClient(
        config=cfg,
        transport=transport,
        auth=DnseAuthenticator(cfg, transport),
        sleeper=slept.append,
    )


_OHLC = {"s": "ok", "t": [1735689600], "o": [100], "h": [110], "l": [99], "c": [105], "v": [1000]}


# ---- config / redaction ---------------------------------------------------
class TestConfig:
    def test_redacts_secret_headers(self) -> None:
        masked = redact_headers({"Authorization": "Bearer x", "Accept": "application/json"})
        assert masked["Authorization"] == "***redacted***"
        assert masked["Accept"] == "application/json"

    def test_from_env_reads_credentials(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DNSE_BASE_URL", "https://api.dnse.test/")
        monkeypatch.setenv("DNSE_API_KEY", "k")
        monkeypatch.setenv("DNSE_API_SECRET", "s")
        cfg = DnseConfig.from_env()
        assert cfg.base_url == "https://api.dnse.test"  # trailing slash trimmed
        assert cfg.has_credentials

    def test_no_credentials_is_unauthenticated(self) -> None:
        assert DnseConfig().has_credentials is False


# ---- auth -----------------------------------------------------------------
class TestAuth:
    def test_no_credentials_returns_none_and_makes_no_call(self) -> None:
        transport = FakeTransport()
        auth = DnseAuthenticator(DnseConfig(), transport)
        assert auth.token() is None
        assert transport.post_calls == []

    def test_obtains_and_caches_token(self) -> None:
        cfg = DnseConfig(base_url="https://dnse.test", api_key="k", api_secret="s")
        transport = FakeTransport(post=[{"token": "jwt-123"}])
        auth = DnseAuthenticator(cfg, transport)
        assert auth.token() == "jwt-123"
        assert auth.token() == "jwt-123"  # cached — no second login
        assert len(transport.post_calls) == 1
        url, body, _ = transport.post_calls[0]
        assert url.endswith("/auth-service/login") and body == {"username": "k", "password": "s"}

    def test_missing_token_raises(self) -> None:
        cfg = DnseConfig(api_key="k", api_secret="s")
        auth = DnseAuthenticator(cfg, FakeTransport(post=[{"nope": 1}]))
        with pytest.raises(DnseAuthError):
            auth.token()


# ---- status translation ---------------------------------------------------
class TestStatusTranslation:
    @pytest.mark.parametrize(
        "status,exc",
        [
            (401, DnseAuthError),
            (403, DnseAuthError),
            (429, DnseRateLimitError),
            (500, DnseUnavailableError),
            (503, DnseUnavailableError),
            (504, DnseUnavailableError),
            (418, DnseError),
        ],
    )
    def test_maps_status_to_typed_error(self, status: int, exc: type[DnseError]) -> None:
        with pytest.raises(exc):
            raise_for_status(status, "boom")

    def test_ok_status_does_not_raise(self) -> None:
        raise_for_status(200, "ok")


# ---- client retry ---------------------------------------------------------
class TestClientRetry:
    def test_retries_transient_then_succeeds(self) -> None:
        transport = FakeTransport(get=[DnseUnavailableError("503"), _OHLC])
        result = _client(transport).ohlc("FPT", 0, 1, "1D", is_index=False)
        assert result == _OHLC
        assert len(transport.get_calls) == 2

    def test_rate_limit_is_retried(self) -> None:
        transport = FakeTransport(get=[DnseRateLimitError("429"), _OHLC])
        assert _client(transport).ohlc("FPT", 0, 1, "1D", is_index=False) == _OHLC

    def test_non_transient_is_not_retried(self) -> None:
        transport = FakeTransport(get=[DnseAuthError("401")])
        with pytest.raises(DnseAuthError):
            _client(transport).ohlc("FPT", 0, 1, "1D", is_index=False)
        assert len(transport.get_calls) == 1  # no retry on a permanent error

    def test_exhausts_retries_and_raises_last(self) -> None:
        cfg = DnseConfig(base_url="https://dnse.test", max_attempts=2, base_delay_seconds=0.0)
        transport = FakeTransport(get=[DnseUnavailableError("a"), DnseUnavailableError("b")])
        with pytest.raises(DnseUnavailableError):
            _client(transport, cfg).ohlc("FPT", 0, 1, "1D", is_index=False)
        assert len(transport.get_calls) == 2

    def test_index_symbol_uses_index_route(self) -> None:
        transport = FakeTransport(get=[_OHLC])
        _client(transport).ohlc("VNINDEX", 0, 1, "1D", is_index=True)
        assert transport.get_calls[0][0].endswith("/chart-api/v2/ohlcs/index")


# ---- provider mapping -----------------------------------------------------
class _FakeClient:
    def __init__(self, payload: Json) -> None:
        self.payload = payload
        self.calls: list[tuple[str, bool]] = []

    def ohlc(self, symbol: str, frm: int, to: int, resolution: str, *, is_index: bool) -> Json:
        self.calls.append((symbol, is_index))
        return self.payload


class TestProvider:
    def test_daily_bars_maps_udf(self) -> None:
        provider = DnseProvider(client=_FakeClient(_OHLC))  # type: ignore[arg-type]
        bars = provider.daily_bars("FPT", date(2024, 12, 1), date(2025, 1, 31))
        assert bars == (
            PriceBar(
                ticker="FPT",
                day=date(2025, 1, 1),
                close=Decimal("105"),
                open=Decimal("100"),
                high=Decimal("110"),
                low=Decimal("99"),
                volume=Decimal("1000"),
            ),
        )

    def test_routes_index_symbols(self) -> None:
        fake = _FakeClient(_OHLC)
        DnseProvider(client=fake).daily_bars("VN30", date(2024, 12, 1), date(2025, 1, 31))  # type: ignore[arg-type]
        assert fake.calls == [("VN30", True)]

    def test_empty_payload_returns_no_bars(self) -> None:
        provider = DnseProvider(client=_FakeClient({"s": "no_data"}))  # type: ignore[arg-type]
        assert provider.daily_bars("FPT", date(2025, 1, 1), date(2025, 1, 31)) == ()

    def test_factory_builds_resilient_provider(self) -> None:
        prov = create_dnse_price_provider(client=_FakeClient(_OHLC))  # type: ignore[arg-type]
        bars = prov.daily_bars("FPT", date(2024, 12, 1), date(2025, 1, 31))
        assert bars and bars[0].ticker == "FPT"


# ---- failover + selection -------------------------------------------------
class _FailingProvider:
    def daily_bars(self, ticker: str, start: date, end: date) -> tuple[PriceBar, ...]:
        raise DnseUnavailableError("dnse down")


class _StubProvider:
    def __init__(self, bar: PriceBar) -> None:
        self._bar = bar

    def daily_bars(self, ticker: str, start: date, end: date) -> tuple[PriceBar, ...]:
        return (self._bar,)


class TestFailoverAndSelection:
    def test_chain_falls_back_to_vnstock_on_dnse_failure(self) -> None:
        fallback = PriceBar(ticker="FPT", day=date(2025, 1, 2), close=Decimal("120"))
        chain = create_chained_price_provider(_FailingProvider(), _StubProvider(fallback))
        assert chain.daily_bars("FPT", date(2025, 1, 1), date(2025, 1, 31)) == (fallback,)

    def test_selection_dnse_default_uses_failover_chain(self) -> None:
        assert market_selection("dnse", failover=True)["price"] == DNSE_CHAIN

    def test_selection_dnse_without_failover_is_dnse_only(self) -> None:
        assert market_selection("dnse", failover=False)["price"] == DNSE

    def test_selection_vnstock_keeps_vnstock(self) -> None:
        assert market_selection("vnstock", failover=True)["price"] == VNSTOCK

    def test_selection_leaves_fundamentals_on_vnstock(self) -> None:
        # DNSE does not serve fundamentals/sectors — those stay on vnstock.
        sel = market_selection("dnse", failover=True)
        assert sel["fundamental"] == VNSTOCK and sel["sector"] == VNSTOCK
