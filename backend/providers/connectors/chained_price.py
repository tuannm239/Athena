"""Multi-source price provider — first source that returns bars wins.

A resilience wrapper (ADR-0017): it holds an ordered list of `PriceProvider`
sources and, for each ticker, returns the first source's non-empty result.
This lets the platform survive one Vietnamese data host going down or retiring
a route (e.g. TCBS 404ing its `bars-long-term` endpoint) without a redeploy —
the next source in the chain answers instead.

It is an adapter only: no business logic, no market logic. Each underlying
source is expected to be per-ticker tolerant (return `()` on failure), and
this wrapper is tolerant regardless — an exception from one source falls
through to the next, and an all-empty chain simply returns `()`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Sequence

from providers.sdk.models import PriceBar
from providers.sdk.ports import PriceProvider

_LOG = logging.getLogger("athena.provider.chain")


@dataclass(frozen=True)
class ChainedPriceProvider:
    """Try each source in order; the first non-empty `daily_bars` wins."""

    sources: tuple[PriceProvider, ...]
    logger: logging.Logger = field(default=_LOG)

    def daily_bars(self, ticker: str, start: date, end: date) -> tuple[PriceBar, ...]:
        for source in self.sources:
            try:
                bars = source.daily_bars(ticker, start, end)
            except Exception as error:  # noqa: BLE001 — fall through to the next source
                self.logger.warning(
                    "chain.source_failed %s [%s]: %s: %s",
                    ticker,
                    type(source).__name__,
                    type(error).__name__,
                    error,
                )
                continue
            if bars:
                return bars
        return ()


def create_chained_price_provider(*sources: PriceProvider) -> ChainedPriceProvider:
    """Build a chain from the given sources (highest priority first)."""
    if not sources:
        raise ValueError("ChainedPriceProvider needs at least one source")
    return ChainedPriceProvider(sources=tuple(sources))


__all__: Sequence[str] = ("ChainedPriceProvider", "create_chained_price_provider")
