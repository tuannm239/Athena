"""Structured logging with correlation ids (SPEC-00 auditability; B-31).

Every API request is logged with its request id; decision evaluations
log the decision id so any Decision Object is traceable end-to-end in
the logs (decision-trace correlation).
"""

from __future__ import annotations

import json
import logging
import sys
import time
from datetime import datetime, timezone
from typing import Any


class _JsonFormatter(logging.Formatter):
    """Single-line JSON records — machine-parseable, deterministic keys."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("request_id", "decision_id", "duration_ms", "status_code", "path", "method"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    """Idempotent root configuration; safe to call from create_app()."""
    root = logging.getLogger("athena")
    if root.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    root.addHandler(handler)
    root.setLevel(level)
    root.propagate = False


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"athena.{name}")


class RequestTimer:
    """Context helper for access logging."""

    def __init__(self) -> None:
        self.started = time.perf_counter()

    @property
    def duration_ms(self) -> int:
        return int((time.perf_counter() - self.started) * 1000)
