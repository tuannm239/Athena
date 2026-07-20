"""vnstock source routing — validation, capability matrix, and the probe.

No network: the probe is driven through an injected fake history client, so
these tests assert routing/validation behaviour deterministically. They also
assert the real installed vnstock exposes at least `vci` (a sanity check that
the disk-based discovery works against the pinned version).
"""

from __future__ import annotations

from datetime import date

import pytest

from providers.connectors.vnstock_source import (
    DEFAULT_SOURCE,
    SourceProbe,
    VnstockSourceError,
    datasets_for_source,
    probe_source,
    resolve_source,
    supported_sources,
)


class TestSupportedSources:
    def test_vci_is_supported(self) -> None:
        assert "vci" in supported_sources()

    def test_default_source_is_supported(self) -> None:
        assert DEFAULT_SOURCE in supported_sources()

    def test_unsupported_sources_absent(self) -> None:
        # SSI and TCBS are not part of vnstock 4.x.
        supported = supported_sources()
        assert "ssi" not in supported
        assert "tcbs" not in supported


class TestResolveSource:
    def test_none_falls_back_to_default(self) -> None:
        assert resolve_source(None) == DEFAULT_SOURCE

    def test_normalises_case_and_whitespace(self) -> None:
        assert resolve_source("  VCI  ") == "vci"

    def test_unsupported_raises_with_clear_message(self) -> None:
        with pytest.raises(VnstockSourceError) as excinfo:
            resolve_source("ssi")
        message = str(excinfo.value)
        assert "ssi" in message
        assert "Supported equity sources" in message
        # Names the real supported set so the operator can fix it.
        assert "vci" in message

    def test_no_silent_failover(self) -> None:
        # An unsupported source must never quietly become a working one.
        with pytest.raises(VnstockSourceError):
            resolve_source("tcbs")


class TestDatasetMatrix:
    def test_vci_serves_prices_and_fundamentals(self) -> None:
        datasets = datasets_for_source("vci")
        assert "prices" in datasets
        assert "fundamentals" in datasets
        assert "profile" in datasets

    def test_msn_serves_prices_but_not_fundamentals(self) -> None:
        # MSN has quote + listing explorers but no financial/company modules.
        if "msn" not in supported_sources():  # pragma: no cover - version guard
            pytest.skip("msn not present in this vnstock build")
        datasets = datasets_for_source("msn")
        assert "prices" in datasets
        assert "fundamentals" not in datasets


class _FakeHistoryClient:
    def __init__(self, source: str, *, rows: int = 0, boom: Exception | None = None) -> None:
        self.source = source
        self.rows = rows
        self.boom = boom

    def history(self, symbol: str, start: str, end: str, interval: str) -> list[dict]:
        if self.boom is not None:
            raise self.boom
        return [{"time": start, "close": "1"} for _ in range(self.rows)]


class _Clock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        self.t += 0.25  # each call advances 250ms
        return self.t


class TestProbe:
    def test_reachable_when_rows_returned(self) -> None:
        probe = probe_source(
            "vci",
            client_factory=lambda s: _FakeHistoryClient(s, rows=5),
            clock=_Clock(),
            today=date(2026, 1, 15),
        )
        assert isinstance(probe, SourceProbe)
        assert probe.reachable is True
        assert probe.status_code == 200
        assert probe.rows == 5
        assert probe.response_ms == 250.0
        assert "prices" in probe.supported_datasets

    def test_empty_response_is_not_reachable(self) -> None:
        probe = probe_source("vci", client_factory=lambda s: _FakeHistoryClient(s, rows=0))
        assert probe.reachable is False
        assert probe.status_code is None
        assert "empty response" in probe.detail

    def test_error_captured_not_raised(self) -> None:
        boom = RuntimeError("Client error '404 Not Found' for url ...")
        probe = probe_source("vci", client_factory=lambda s: _FakeHistoryClient(s, boom=boom))
        assert probe.reachable is False
        assert probe.status_code == 404  # parsed from the message
        assert "RuntimeError" in probe.detail

    def test_probe_reports_configured_datasets_even_on_failure(self) -> None:
        probe = probe_source(
            "vci", client_factory=lambda s: _FakeHistoryClient(s, boom=RuntimeError("down"))
        )
        assert "prices" in probe.supported_datasets
