"""Unit tests — Provider connectors (Phase 2, Module 2)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from providers.connectors.local_files import LocalDataError, LocalFileProvider
from providers.connectors.resilience import (
    HealthMonitor,
    ProviderCallError,
    RetryPolicy,
    TokenBucketRateLimiter,
    TtlCache,
)
from providers.connectors.resilient import ResilientPriceProvider
from providers.connectors.static import StaticProvider
from providers.sdk.models import PriceBar, SectorMapping

D = date(2026, 1, 5)


def bars() -> tuple[PriceBar, ...]:
    return (
        PriceBar(ticker="AAA", day=date(2026, 1, 6), close=Decimal("11")),
        PriceBar(ticker="AAA", day=D, close=Decimal("10")),
        PriceBar(ticker="BBB", day=D, close=Decimal("50")),
    )


class TestRetryPolicy:
    def test_retries_then_succeeds(self) -> None:
        attempts: list[int] = []

        def flaky() -> str:
            attempts.append(1)
            if len(attempts) < 3:
                raise ConnectionError("boom")
            return "ok"

        sleeps: list[float] = []
        result = RetryPolicy(max_attempts=3, base_delay_seconds=0.5).execute(
            flaky, sleeper=sleeps.append
        )
        assert result == "ok"
        assert sleeps == [0.5, 1.0]  # exponential backoff

    def test_exhaustion_raises(self) -> None:
        with pytest.raises(ProviderCallError):
            RetryPolicy(max_attempts=2).execute(
                lambda: (_ for _ in ()).throw(ConnectionError("x")), sleeper=lambda _s: None
            )


class TestRateLimiterAndCache:
    def test_token_bucket(self) -> None:
        now = [0.0]
        limiter = TokenBucketRateLimiter(rate_per_second=1, capacity=2, clock=lambda: now[0])
        assert limiter.try_acquire() and limiter.try_acquire()
        assert not limiter.try_acquire()
        now[0] += 1.0
        assert limiter.try_acquire()

    def test_ttl_cache_expiry(self) -> None:
        now = [0.0]
        cache = TtlCache(ttl_seconds=10, clock=lambda: now[0])
        cache.put("k", "v")
        assert cache.get("k") == "v"
        now[0] += 11
        assert cache.get("k") is None


class TestHealthMonitor:
    def test_transitions(self) -> None:
        monitor = HealthMonitor(name="price", unhealthy_after=2)
        assert monitor.healthy
        monitor.record_failure("timeout")
        monitor.record_failure("timeout")
        assert not monitor.healthy
        assert monitor.status().consecutive_failures == 2
        monitor.record_success()
        assert monitor.healthy and monitor.status().last_success_at is not None


class TestStaticProvider:
    def test_ports_are_deterministic(self) -> None:
        provider = StaticProvider(
            bars=bars(), sectors=(SectorMapping(ticker="AAA", sector="Tech", industry="SW"),)
        )
        series = provider.daily_bars("AAA", D, date(2026, 1, 31))
        assert [b.day.day for b in series] == [5, 6]  # sorted
        assert provider.classification("AAA") is not None
        assert provider.classification("ZZZ") is None


class TestLocalFileProvider:
    def test_reads_csv_dumps(self, tmp_path: Path) -> None:
        (tmp_path / "prices.csv").write_text(
            "ticker,day,close,volume\nAAA,2026-01-06,11,100\nAAA,2026-01-05,10,90\n"
        )
        (tmp_path / "sectors.csv").write_text("ticker,sector,industry\nAAA,Tech,Software\n")
        (tmp_path / "calendar.csv").write_text("day\n2026-01-05\n2026-01-06\n")
        provider = LocalFileProvider(directory=tmp_path)
        series = provider.daily_bars("AAA", D, date(2026, 1, 31))
        assert [str(b.close) for b in series] == ["10", "11"]
        mapping = provider.classification("AAA")
        assert mapping is not None and mapping.sector == "Tech"
        assert provider.trading_days(D, date(2026, 1, 6)) == (D, date(2026, 1, 6))

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(LocalDataError):
            LocalFileProvider(directory=tmp_path).daily_bars("AAA", D, D)


class TestResilientDecorator:
    def test_cache_then_limit_then_retry_then_health(self) -> None:
        calls: list[int] = []

        class Flaky:
            def daily_bars(self, ticker: str, start: date, end: date) -> tuple[PriceBar, ...]:
                calls.append(1)
                if len(calls) == 1:
                    raise ConnectionError("first call fails")
                return bars()[:1]

        now = [0.0]
        provider = ResilientPriceProvider(
            inner=Flaky(),
            retry=RetryPolicy(max_attempts=2, base_delay_seconds=0),
            limiter=TokenBucketRateLimiter(rate_per_second=100, capacity=10, clock=lambda: now[0]),
            cache=TtlCache(ttl_seconds=60, clock=lambda: now[0]),
        )
        first = provider.daily_bars("AAA", D, D)
        assert len(calls) == 2  # one retry
        assert provider.status().healthy
        second = provider.daily_bars("AAA", D, D)  # cache hit: no new calls
        assert len(calls) == 2
        assert first == second

    def test_rate_limit_and_health_failure(self) -> None:
        class Dead:
            def daily_bars(self, ticker: str, start: date, end: date) -> tuple[PriceBar, ...]:
                raise ConnectionError("down")

        provider = ResilientPriceProvider(
            inner=Dead(),
            retry=RetryPolicy(max_attempts=1),
            health=HealthMonitor(name="price", unhealthy_after=1),
        )
        with pytest.raises(ProviderCallError):
            provider.daily_bars("AAA", D, D)
        assert not provider.status().healthy
