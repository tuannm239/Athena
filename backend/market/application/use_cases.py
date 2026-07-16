"""Market Engine use cases (SPEC-05; RFC-0025).

Evaluates the regime deterministically, persists the latest context via
the MarketRepository port, and emits MarketRegimeChanged when the
classified regime differs from the previous context.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from market.domain.events import MarketRegimeChanged
from market.domain.market_context import MarketContext
from market.domain.regime_engine import RegimeInputs, evaluate_regime
from market.domain.repository import MarketRepository
from shared_kernel.exceptions import NotFoundError
from shared_kernel.ports import EventPublisher


@dataclass
class MarketUseCases:
    repository: MarketRepository
    events: EventPublisher

    def evaluate(self, inputs: RegimeInputs, *, as_of: datetime | None = None) -> MarketContext:
        context = evaluate_regime(inputs, as_of or datetime.now(timezone.utc))
        previous = self.repository.latest_context()
        self.repository.save_context(context)
        if previous is None or previous.regime is not context.regime:
            self.events.publish((MarketRegimeChanged(regime=context.regime),))
        return context

    def current_context(self) -> MarketContext:
        context = self.repository.latest_context()
        if context is None:
            raise NotFoundError("no market context has been evaluated yet")
        return context
