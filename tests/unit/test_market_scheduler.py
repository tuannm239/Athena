"""Market sync scheduler + CLI — over the existing ProviderSyncService.

Everything runs against an in-memory pipeline and a deterministic price
provider (no network, no vnstock): full / incremental / replay / status,
retry-with-backoff, progress outcome, ticker resolution, and CLI dispatch.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from tests.unit.test_production_sync import MemoryCatalog, MemorySnapshots

from data_pipeline.application.sync import ProviderSyncService
from data_pipeline.application.use_cases import DataPipelineUseCases
from data_pipeline.cli import _parser, main
from data_pipeline.scheduler import MarketSyncScheduler
from data_pipeline.tickers import DEFAULT_SYNC_SPEC, parse_spec, resolve_tickers
from providers.connectors.static import StaticProvider
from providers.sdk.models import PriceBar
from providers.sdk.ports import PriceProvider

END = date(2026, 1, 6)
AS_OF = datetime(2026, 1, 6, 9, 0, tzinfo=timezone.utc)
TICKERS = ["VNINDEX", "FPT", "HPG"]


def _bars() -> tuple[PriceBar, ...]:
    d1, d2 = date(2026, 1, 5), date(2026, 1, 6)
    return tuple(
        PriceBar(ticker=t, day=d, close=Decimal(c), volume=Decimal("1000000"))
        for t, c in (("VNINDEX", "1290"), ("FPT", "138"), ("HPG", "27"))
        for d in (d1, d2)
    )


def _scheduler(provider: PriceProvider | None = None, **kw: object) -> MarketSyncScheduler:
    pipeline = DataPipelineUseCases(catalog=MemoryCatalog(), snapshots=MemorySnapshots())
    sync = ProviderSyncService(pipeline=pipeline, source="provider:test")
    return MarketSyncScheduler(
        sync=sync,
        provider=provider or StaticProvider(bars=_bars()),
        tickers=TICKERS,
        clock=lambda: AS_OF,
        sleeper=lambda _s: None,  # no real backoff sleeps in tests
        **kw,  # type: ignore[arg-type]
    )


# ---- ticker resolution ----------------------------------------------------
class TestTickerResolution:
    def test_exchange_codes_expand_indices_kept(self) -> None:
        resolved = resolve_tickers(DEFAULT_SYNC_SPEC)
        assert "VNINDEX" in resolved and "VN30" in resolved  # indices kept
        assert "FPT" in resolved and "HPG" in resolved  # HOSE expanded
        assert "SHS" in resolved  # HNX expanded
        assert "BSR" in resolved  # UPCOM expanded
        assert len(resolved) == len(set(resolved))  # de-duplicated

    def test_custom_list_used_literally(self) -> None:
        assert resolve_tickers(["FPT", "vnindex", "FPT"]) == ("FPT", "VNINDEX")

    def test_parse_spec_default_and_override(self) -> None:
        assert parse_spec(None) == DEFAULT_SYNC_SPEC
        assert parse_spec("FPT, HPG ,VNINDEX") == ("FPT", " HPG ", "VNINDEX")


# ---- scheduler operations -------------------------------------------------
class TestSchedulerOps:
    def test_full_publishes(self) -> None:
        outcome = _scheduler().full(end=END)
        assert outcome.ok and outcome.published
        assert outcome.mode == "full" and outcome.row_count == 6
        assert outcome.attempts == 1

    def test_status_reflects_watermark(self) -> None:
        sched = _scheduler()
        assert sched.status()["has_published_data"] is False
        sched.full(end=END)
        status = sched.status()
        assert status["has_published_data"] is True
        assert status["watermark"] == "2026-01-06"
        assert status["tickers_configured"] == 3

    def test_incremental_up_to_date_after_full(self) -> None:
        sched = _scheduler()
        sched.full(end=END)
        outcome = sched.incremental(as_of=AS_OF)
        assert outcome.ok and not outcome.published
        assert "up to date" in outcome.detail

    def test_replay_publishes_comparable_version(self) -> None:
        sched = _scheduler()
        sched.full(end=END)
        outcome = sched.replay(date(2026, 1, 5), date(2026, 1, 6))
        assert outcome.ok and outcome.published and outcome.mode == "replay"

    def test_replay_supersedes_when_full_would_collide(self) -> None:
        # Reproduces the ephemeral-loss/backend-switch case: a same-day version
        # already exists, so full() collides (DuplicateDatasetError -> not ok),
        # but replay() mints a unique version and republishes — the basis for
        # `sync ensure` using replay to self-heal.
        sched = _scheduler()
        sched.full(end=END)
        assert not sched.full(end=END).ok  # duplicate version -> fails
        rep = sched.replay(date(2026, 1, 5), END)
        assert rep.ok and rep.published


# ---- retry / failure ------------------------------------------------------
class _FlakyProvider:
    """PriceProvider that raises on the first N whole-sync attempts."""

    def __init__(self, fail_times: int) -> None:
        self._left = fail_times
        self._inner = StaticProvider(bars=_bars())

    def daily_bars(self, ticker: str, start: date, end: date) -> tuple[PriceBar, ...]:
        if self._left > 0:
            self._left -= 1
            raise RuntimeError("transient upstream failure")
        return self._inner.daily_bars(ticker, start, end)


class TestRetry:
    def test_retries_then_succeeds(self) -> None:
        sched = _scheduler(provider=_FlakyProvider(fail_times=2), max_retries=4)
        outcome = sched.full(end=END)
        assert outcome.ok and outcome.published
        assert outcome.attempts == 3  # failed twice, succeeded on the third

    def test_exhausts_retries_and_reports_failure(self) -> None:
        sched = _scheduler(provider=_FlakyProvider(fail_times=99), max_retries=3)
        outcome = sched.full(end=END)
        assert not outcome.ok and not outcome.published
        assert outcome.attempts == 3
        assert "failed after 3 attempts" in outcome.detail


# ---- outcome serialisation ------------------------------------------------
def test_outcome_as_dict_is_json_friendly() -> None:
    outcome = _scheduler().full(end=END)
    payload = outcome.as_dict()
    assert payload["mode"] == "full" and payload["ok"] is True
    assert "duration_seconds" in payload and isinstance(payload["duration_seconds"], float)


# ---- CLI ------------------------------------------------------------------
class TestCli:
    def test_parser_full_and_replay(self) -> None:
        args = _parser().parse_args(["sync", "full"])
        assert args.group == "sync" and args.action == "full"
        args = _parser().parse_args(
            ["sync", "replay", "--start", "2026-01-01", "--end", "2026-01-06"]
        )
        assert args.start == "2026-01-01" and args.end == "2026-01-06"

    def test_main_full_returns_zero(self, monkeypatch: pytest.MonkeyPatch, capsys) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setattr("data_pipeline.cli.build_scheduler", lambda **_kw: _scheduler())
        code = main(["sync", "full"])
        assert code == 0
        assert '"published": true' in capsys.readouterr().out.lower()

    def test_main_failure_returns_one(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "data_pipeline.cli.build_scheduler",
            lambda **_kw: _scheduler(provider=_FlakyProvider(99), max_retries=1),
        )
        assert main(["sync", "full"]) == 1

    def test_main_status_returns_zero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("data_pipeline.cli.build_scheduler", lambda **_kw: _scheduler())
        assert main(["sync", "status"]) == 0

    def test_parser_provider_test(self) -> None:
        args = _parser().parse_args(["provider", "test"])
        assert args.group == "provider" and args.action == "test"

    def test_provider_test_reachable_returns_zero(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys,  # type: ignore[no-untyped-def]
    ) -> None:
        from providers.connectors.vnstock_source import SourceProbe

        def _fake_probe(source: str, **_kw: object) -> SourceProbe:
            return SourceProbe(
                source=source,
                reachable=source == "vci",
                status_code=200 if source == "vci" else 404,
                response_ms=12.3,
                supported_datasets=("prices",),
                rows=5 if source == "vci" else 0,
                detail="ok" if source == "vci" else "down",
            )

        monkeypatch.delenv("VNSTOCK_SOURCE", raising=False)  # -> default vci
        monkeypatch.setattr("data_pipeline.cli.probe_source", _fake_probe)
        code = main(["provider", "test"])
        out = capsys.readouterr().out
        assert code == 0  # configured source (vci) reachable
        assert '"command": "provider.test"' in out
        assert '"configured_source": "vci"' in out

    def test_provider_test_unreachable_configured_returns_one(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from providers.connectors.vnstock_source import SourceProbe

        def _fake_probe(source: str, **_kw: object) -> SourceProbe:
            return SourceProbe(source, False, 500, 9.0, ("prices",), 0, "down")

        monkeypatch.delenv("VNSTOCK_SOURCE", raising=False)
        monkeypatch.setattr("data_pipeline.cli.probe_source", _fake_probe)
        assert main(["provider", "test"]) == 1

    def test_provider_datasets_returns_zero_and_lists_catalog(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys,  # type: ignore[no-untyped-def]
    ) -> None:
        monkeypatch.delenv("VNSTOCK_SOURCE", raising=False)
        code = main(["provider", "datasets"])
        out = capsys.readouterr().out
        assert code == 0
        assert '"command": "provider.datasets"' in out
        assert "Historical Prices" in out
        assert "NOT_SUPPORTED" in out  # foreign/order/side

    def test_parser_sync_scopes(self) -> None:
        assert _parser().parse_args(["sync", "market"]).action == "market"
        assert _parser().parse_args(["sync", "universe"]).action == "universe"
        args = _parser().parse_args(["sync", "symbol", "FPT"])
        assert args.action == "symbol" and args.symbol == "FPT"

    def test_sync_market_scope_uses_indices(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, object] = {}

        def _capture(**kw: object):  # type: ignore[no-untyped-def]
            captured.update(kw)
            return _scheduler()

        monkeypatch.setattr("data_pipeline.cli.build_scheduler", _capture)
        assert main(["sync", "market"]) == 0
        tickers = captured["tickers"]
        assert "VNINDEX" in tickers and "FPT" not in tickers  # indices only

    def test_parser_symbols_and_universe_level(self) -> None:
        args = _parser().parse_args(["sync", "symbols", "FPT", "VCB", "HPG"])
        assert args.action == "symbols" and args.symbols == ["FPT", "VCB", "HPG"]
        args = _parser().parse_args(["sync", "universe", "--level", "REALTIME"])
        assert args.action == "universe" and args.level == "REALTIME"

    def test_sync_symbols_scope_is_the_given_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, object] = {}

        def _capture(**kw: object):  # type: ignore[no-untyped-def]
            captured.update(kw)
            return _scheduler()

        monkeypatch.setattr("data_pipeline.cli.build_scheduler", _capture)
        assert main(["sync", "symbols", "FPT", "VCB", "HPG"]) == 0
        assert captured["tickers"] == ["FPT", "VCB", "HPG"]

    def test_sync_universe_reads_from_repo(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, object] = {}

        def _capture(**kw: object):  # type: ignore[no-untyped-def]
            captured.update(kw)
            return _scheduler()

        monkeypatch.setattr("data_pipeline.cli.build_scheduler", _capture)
        monkeypatch.setattr("data_pipeline.cli.universe_symbols", lambda level: ["VCB", "FPT"])
        assert main(["sync", "universe"]) == 0
        assert captured["tickers"] == ["VCB", "FPT"]

    def test_sync_symbol_scope_is_single_symbol(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, object] = {}

        def _capture(**kw: object):  # type: ignore[no-untyped-def]
            captured.update(kw)
            return _scheduler()

        monkeypatch.setattr("data_pipeline.cli.build_scheduler", _capture)
        assert main(["sync", "symbol", "FPT"]) == 0
        assert captured["tickers"] == ["FPT"]

    def test_sync_ensure_backfills_when_no_prices(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[str] = []
        sched = _scheduler()
        ok = sched.full()
        monkeypatch.setattr(sched, "replay", lambda *a, **k: (calls.append("replay"), ok)[1])
        monkeypatch.setattr(sched, "incremental", lambda: (calls.append("incr"), ok)[1])
        monkeypatch.setattr("data_pipeline.cli.build_scheduler", lambda **_kw: sched)
        monkeypatch.setattr("data_pipeline.cli.published_prices_present", lambda: False)
        assert main(["sync", "ensure"]) == 0
        assert calls == ["replay"]  # no readable prices -> replay backfill (unique version)

    def test_sync_ensure_tops_up_when_prices_present(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[str] = []
        sched = _scheduler()
        ok = sched.full()
        monkeypatch.setattr(sched, "full", lambda: (calls.append("full"), ok)[1])
        monkeypatch.setattr(sched, "incremental", lambda: (calls.append("incr"), ok)[1])
        monkeypatch.setattr("data_pipeline.cli.build_scheduler", lambda **_kw: sched)
        monkeypatch.setattr("data_pipeline.cli.published_prices_present", lambda: True)
        assert main(["sync", "ensure"]) == 0
        assert calls == ["incr"]  # readable prices -> incremental top-up
