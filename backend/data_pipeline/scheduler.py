"""Market synchronisation scheduler (operational orchestration).

A thin, production-ready orchestrator over the *existing* `ProviderSyncService`.
It NEVER fetches data itself: it hands an injected price provider to
`ProviderSyncService`, which owns all provider access. Responsibilities:

  * full / incremental / replay runs (delegated to ProviderSyncService);
  * retry with exponential backoff around a whole run (transient DB/provider
    failures) — the provider also retries internally (resilience stack);
  * structured logging + progress reporting at each stage;
  * a status/health snapshot (watermark, last published version, provider health).

No business logic and no market logic live here — it only schedules and reports.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from data_pipeline.application.sync import PRICES_DATASET, ProviderSyncService
from providers.sdk.ports import PriceProvider

_LOG = logging.getLogger("athena.sync")


@dataclass(frozen=True, slots=True)
class SyncOutcome:
    """Result of one scheduled run — the unit of progress/health reporting."""

    mode: str
    ok: bool
    published: bool
    version: str | None
    row_count: int | None
    tickers: int
    attempts: int
    started_at: datetime
    finished_at: datetime
    detail: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "ok": self.ok,
            "published": self.published,
            "version": self.version,
            "row_count": self.row_count,
            "tickers": self.tickers,
            "attempts": self.attempts,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat(),
            "duration_seconds": round((self.finished_at - self.started_at).total_seconds(), 3),
            "detail": self.detail,
        }


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class MarketSyncScheduler:
    """Schedules market price syncs through `ProviderSyncService`."""

    sync: ProviderSyncService
    provider: PriceProvider
    tickers: Sequence[str]
    lookback_days: int = 365
    max_retries: int = 3
    base_delay_seconds: float = 2.0
    clock: Callable[[], datetime] = _now
    sleeper: Callable[[float], None] = time.sleep
    logger: logging.Logger = _LOG

    # -- public operations --------------------------------------------------
    def full(self, *, end: date | None = None) -> SyncOutcome:
        end = end or self.clock().date()
        start = end - timedelta(days=self.lookback_days)
        self.logger.info(
            "sync.full.start",
            extra={
                "tickers": len(self.tickers),
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
        )
        return self._run(
            "full",
            lambda: self.sync.full_sync_prices(
                self.provider, self.tickers, start, end, as_of=self.clock()
            ),
        )

    def incremental(self, *, as_of: datetime | None = None) -> SyncOutcome:
        as_of = as_of or self.clock()
        initial_start = as_of.date() - timedelta(days=self.lookback_days)
        self.logger.info("sync.incremental.start", extra={"tickers": len(self.tickers)})
        return self._run(
            "incremental",
            lambda: self.sync.incremental_sync_prices(
                self.provider, self.tickers, as_of=as_of, initial_start=initial_start
            ),
            allow_none=True,
        )

    def replay(self, start: date, end: date) -> SyncOutcome:
        self.logger.info(
            "sync.replay.start",
            extra={
                "tickers": len(self.tickers),
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
        )
        return self._run(
            "replay",
            lambda: self.sync.replay_prices(
                self.provider, self.tickers, start, end, as_of=self.clock()
            ),
        )

    def status(self) -> dict[str, object]:
        """Health snapshot: watermark, provider health, checked-at."""
        watermark = self.sync.watermark(PRICES_DATASET)
        provider_status = getattr(self.provider, "status", None)
        health = provider_status() if callable(provider_status) else None
        return {
            "dataset": PRICES_DATASET,
            "watermark": watermark.isoformat() if watermark else None,
            "has_published_data": watermark is not None,
            "tickers_configured": len(self.tickers),
            "provider_healthy": bool(getattr(health, "healthy", True)) if health else None,
            "provider_detail": getattr(health, "detail", "") if health else "",
            "checked_at": self.clock().isoformat(),
        }

    # -- retry / progress machinery ----------------------------------------
    def _run(
        self,
        mode: str,
        operation: Callable[[], object],
        *,
        allow_none: bool = False,
    ) -> SyncOutcome:
        started = self.clock()
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                version = operation()
                if version is None and allow_none:
                    finished = self.clock()
                    self.logger.info("sync.%s.up_to_date", mode, extra={"attempt": attempt})
                    return SyncOutcome(
                        mode=mode,
                        ok=True,
                        published=False,
                        version=None,
                        row_count=None,
                        tickers=len(self.tickers),
                        attempts=attempt,
                        started_at=started,
                        finished_at=finished,
                        detail="no new data — already up to date",
                    )
                row_count = getattr(getattr(version, "quality", None), "row_count", None)
                ver = getattr(version, "version", None)
                finished = self.clock()
                self.logger.info(
                    "sync.%s.published",
                    mode,
                    extra={"version": ver, "rows": row_count, "attempt": attempt},
                )
                return SyncOutcome(
                    mode=mode,
                    ok=True,
                    published=True,
                    version=ver,
                    row_count=row_count,
                    tickers=len(self.tickers),
                    attempts=attempt,
                    started_at=started,
                    finished_at=finished,
                    detail="published",
                )
            except Exception as error:  # noqa: BLE001 — orchestrator boundary
                last_error = error
                # Put the reason in the message itself (the JSON logger drops
                # `extra`), so the failure is visible in the deploy logs.
                self.logger.warning(
                    "sync.%s.attempt_failed (%d/%d): %s: %s",
                    mode,
                    attempt,
                    self.max_retries,
                    type(error).__name__,
                    error,
                )
                if attempt < self.max_retries:
                    self.sleeper(self.base_delay_seconds * (2 ** (attempt - 1)))
        finished = self.clock()
        self.logger.error(
            "sync.%s.failed after %d attempts: %s: %s",
            mode,
            self.max_retries,
            type(last_error).__name__,
            last_error,
        )
        return SyncOutcome(
            mode=mode,
            ok=False,
            published=False,
            version=None,
            row_count=None,
            tickers=len(self.tickers),
            attempts=self.max_retries,
            started_at=started,
            finished_at=finished,
            detail=f"failed after {self.max_retries} attempts: {last_error}",
        )
