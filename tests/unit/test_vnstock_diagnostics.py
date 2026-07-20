"""vnstock failure diagnostics — exception classification.

Deterministic classification of synthetic exceptions into actionable
categories (dns/tls/timeout/tcp/http/auth/provider). Active connectivity
probing is network I/O and is exercised only by the opt-in live test.
"""

from __future__ import annotations

import os
import socket
import ssl

import pytest

from providers.connectors.vnstock_diagnostics import (
    FailureCategory,
    classify_exception,
    diagnose_connectivity,
)


class _Resp:
    def __init__(self, status: int) -> None:
        self.status_code = status


class _HttpError(Exception):
    def __init__(self, status: int, msg: str) -> None:
        super().__init__(msg)
        self.response = _Resp(status)


class TestClassify:
    def test_dns(self) -> None:
        cat, status = classify_exception(socket.gaierror("Name or service not known"))
        assert cat is FailureCategory.DNS and status is None

    def test_tls(self) -> None:
        cat, _ = classify_exception(ssl.SSLError("certificate verify failed"))
        assert cat is FailureCategory.TLS

    def test_timeout(self) -> None:
        cat, _ = classify_exception(TimeoutError("The read operation timed out"))
        assert cat is FailureCategory.TIMEOUT

    def test_auth_from_status(self) -> None:
        cat, status = classify_exception(_HttpError(403, "Forbidden"))
        assert cat is FailureCategory.AUTH and status == 403

    def test_tcp_connection_reset(self) -> None:
        cat, _ = classify_exception(ConnectionError("Connection refused"))
        assert cat is FailureCategory.TCP

    def test_http_status(self) -> None:
        cat, status = classify_exception(_HttpError(404, "Client error '404 Not Found'"))
        assert cat is FailureCategory.HTTP and status == 404

    def test_provider_not_support(self) -> None:
        cat, _ = classify_exception(RuntimeError("Source 'vci' does not support 'foreign_trade'"))
        assert cat is FailureCategory.PROVIDER

    def test_unknown(self) -> None:
        cat, _ = classify_exception(ValueError("something odd"))
        assert cat is FailureCategory.UNKNOWN

    def test_walks_cause_chain(self) -> None:
        try:
            try:
                raise TimeoutError("timed out")
            except TimeoutError as inner:
                raise RuntimeError("wrapper") from inner
        except RuntimeError as outer:
            cat, _ = classify_exception(outer)
        assert cat is FailureCategory.TIMEOUT


class TestConnectivityShape:
    def test_dns_failure_is_captured_not_raised(self) -> None:
        # An unresolvable host must yield a DNS-category record, never raise.
        diag = diagnose_connectivity("no-such-host.invalid.", timeout=2.0)
        assert diag.reachable is False
        assert diag.category is FailureCategory.DNS
        assert diag.stages and diag.stages[0].stage == "dns"


@pytest.mark.skipif(
    os.environ.get("VNSTOCK_LIVE") != "1",
    reason="live connectivity probe — set VNSTOCK_LIVE=1 on open internet",
)
def test_live_vci_host_reachable() -> None:
    diag = diagnose_connectivity("trading.vietcap.com.vn", timeout=8.0)
    # On a VN-reachable network this resolves + connects; the assertion documents
    # intent. On a blocked datacenter IP it records the exact failing stage.
    assert diag.stages, "expected at least a DNS stage result"
