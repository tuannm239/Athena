"""vnstock failure diagnostics — make deployment failures fully observable.

When vnstock works locally but fails in a deployment (e.g. a non-VN datacenter
IP that a VN broker host silently drops), the platform must *not* switch
providers — it must explain, in the logs, exactly why. This module classifies
any exception into an actionable category and can actively probe the network
path (DNS → TCP → TLS → HTTP) to the data host.

Pure classification (`classify_exception`) is deterministic and unit-tested.
Active probing (`diagnose_connectivity`) does real network I/O and is meant to
run in the target environment (via `athena provider diagnose`), where its
structured output lands in the logs.
"""

from __future__ import annotations

import re
import socket
import ssl
import time
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlparse

# The VCI (Vietcap) hosts vnstock talks to (from the installed explorer const).
VCI_HOSTS: tuple[str, ...] = (
    "trading.vietcap.com.vn",
    "mt.vietcap.com.vn",
    "iq.vietcap.com.vn",
)


class FailureCategory(str, Enum):
    DNS = "dns"
    TCP = "tcp"
    TLS = "tls"
    TIMEOUT = "timeout"
    HTTP = "http"
    AUTH = "auth"
    PROVIDER = "provider"
    UNKNOWN = "unknown"
    OK = "ok"


_STATUS_RE = re.compile(r"\b([1-5]\d{2})\b")


def _status_of(exc: BaseException) -> int | None:
    response = getattr(exc, "response", None)
    code = getattr(response, "status_code", None)
    if isinstance(code, int):
        return code
    code = getattr(exc, "status_code", None)
    return code if isinstance(code, int) else None


def classify_exception(error: BaseException) -> tuple[FailureCategory, int | None]:
    """Map an exception (walking its cause chain) to a category + HTTP status.

    Ordering matters: a specific signal (DNS/TLS/timeout) wins over a generic
    HTTP/provider bucket. Detection is by type first, then message text, so it
    works whether or not httpx/requests types are importable here.
    """
    seen: set[int] = set()
    current: BaseException | None = error
    fallback_status: int | None = None
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        name = type(current).__name__
        text = str(current).lower()
        status = _status_of(current)
        if status is not None and fallback_status is None:
            fallback_status = status

        if (
            isinstance(current, socket.gaierror)
            or "getaddrinfo" in text
            or ("name or service not known" in text)
            or "nodename nor servname" in text
            or "temporary failure in name resolution" in text
        ):
            return FailureCategory.DNS, None
        if (
            isinstance(current, ssl.SSLError)
            or "sslerror" in name.lower()
            or ("certificate" in text)
            or "tls" in text
            or "ssl" in text
            or "handshake" in text
        ):
            return FailureCategory.TLS, None
        if (
            isinstance(current, (socket.timeout, TimeoutError))
            or "timeout" in name.lower()
            or ("timed out" in text)
            or "timeout" in text
        ):
            return FailureCategory.TIMEOUT, None
        if (
            status in (401, 403)
            or "unauthorized" in text
            or "forbidden" in text
            or ("api key" in text)
            or "token" in text
            or "authentication" in text
        ):
            return FailureCategory.AUTH, status
        if (
            isinstance(current, ConnectionError)
            or "connection refused" in text
            or ("connection reset" in text)
            or "connection aborted" in text
        ):
            return FailureCategory.TCP, None
        if status is not None or "status" in text or _STATUS_RE.search(text) is not None:
            return FailureCategory.HTTP, status or (
                int(m.group(1)) if (m := _STATUS_RE.search(text)) else None
            )
        if "vnstock" in text or name.startswith("Vnstock") or "not support" in text:
            return FailureCategory.PROVIDER, None
        current = current.__cause__ or current.__context__
    return FailureCategory.UNKNOWN, fallback_status


@dataclass(frozen=True, slots=True)
class StageResult:
    stage: str
    ok: bool
    ms: float
    detail: str


@dataclass(frozen=True, slots=True)
class HostDiagnostic:
    host: str
    port: int
    reachable: bool
    category: FailureCategory
    stages: list[StageResult] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "host": self.host,
            "port": self.port,
            "reachable": self.reachable,
            "category": self.category.value,
            "stages": [
                {"stage": s.stage, "ok": s.ok, "ms": s.ms, "detail": s.detail} for s in self.stages
            ],
        }


def _ms(started: float) -> float:
    return round((time.monotonic() - started) * 1000, 1)


def diagnose_connectivity(host: str, *, port: int = 443, timeout: float = 8.0) -> HostDiagnostic:
    """Probe DNS → TCP → TLS to `host:port`, timing and reporting each stage.

    Never raises — every failure is captured as a stage result plus a category,
    so the whole thing is observable in one structured record.
    """
    stages: list[StageResult] = []

    # 1) DNS
    began = time.monotonic()
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
        addrs = sorted({str(info[4][0]) for info in infos})
        stages.append(StageResult("dns", True, _ms(began), f"resolved {', '.join(addrs)}"))
    except Exception as error:  # noqa: BLE001
        stages.append(StageResult("dns", False, _ms(began), f"{type(error).__name__}: {error}"))
        return HostDiagnostic(host, port, False, FailureCategory.DNS, stages)

    # 2) TCP connect
    began = time.monotonic()
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        stages.append(StageResult("tcp", True, _ms(began), "connected"))
    except Exception as error:  # noqa: BLE001
        cat, _ = classify_exception(error)
        stages.append(StageResult("tcp", False, _ms(began), f"{type(error).__name__}: {error}"))
        return HostDiagnostic(
            host,
            port,
            False,
            cat if cat is not FailureCategory.UNKNOWN else FailureCategory.TCP,
            stages,
        )

    # 3) TLS handshake
    began = time.monotonic()
    try:
        context = ssl.create_default_context()
        with context.wrap_socket(sock, server_hostname=host) as tls:
            cipher = tls.cipher()
            proto = tls.version()
        stages.append(
            StageResult("tls", True, _ms(began), f"{proto} {cipher[0] if cipher else ''}".strip())
        )
    except Exception as error:  # noqa: BLE001
        cat, _ = classify_exception(error)
        stages.append(StageResult("tls", False, _ms(began), f"{type(error).__name__}: {error}"))
        try:
            sock.close()
        except OSError:
            pass
        return HostDiagnostic(
            host,
            port,
            False,
            cat if cat is not FailureCategory.UNKNOWN else FailureCategory.TLS,
            stages,
        )
    finally:
        try:
            sock.close()
        except OSError:
            pass

    return HostDiagnostic(host, port, True, FailureCategory.OK, stages)


def host_from_url(url: str) -> str:
    parsed = urlparse(url)
    return parsed.hostname or url


def diagnose_hosts(
    hosts: tuple[str, ...] = VCI_HOSTS, *, timeout: float = 8.0
) -> list[HostDiagnostic]:
    return [diagnose_connectivity(h, timeout=timeout) for h in hosts]
