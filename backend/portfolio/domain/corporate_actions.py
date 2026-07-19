"""Vietnamese corporate actions on portfolio holdings (Phase 7, WS5).

Pure domain logic for the cash and share effects a Vietnamese long-term
investor actually encounters: cash dividends, bonus (stock) dividends, rights
issues, and stock splits — plus sector exposure and simple total return.

Deliberately **excludes derivatives and margin** (out of scope for this
edition): there are no futures/covered-warrants, no leverage, and no
margin-interest maths here. Everything is cash-and-shares, Decimal money.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from shared_kernel.money import Currency, Money

_ZERO = Decimal(0)


@dataclass(frozen=True, slots=True)
class Holding:
    """A long, unleveraged holding of a Vietnamese equity."""

    ticker: str
    quantity: Decimal
    average_cost: Money  # per-share cost basis

    def __post_init__(self) -> None:
        if not self.ticker:
            raise ValueError("holding ticker must not be empty")
        if self.quantity < _ZERO:
            raise ValueError("quantity must not be negative (no short positions)")

    @property
    def cost_basis(self) -> Money:
        return self.average_cost.scaled(self.quantity)


def apply_cash_dividend(holding: Holding, dividend_per_share: Money) -> Money:
    """Cash received from a cash dividend. The holding itself is unchanged."""
    if dividend_per_share.currency is not holding.average_cost.currency:
        raise ValueError("dividend currency must match the holding currency")
    return dividend_per_share.scaled(holding.quantity)


def apply_stock_dividend(holding: Holding, ratio: Decimal) -> Holding:
    """Bonus shares: quantity grows by `ratio` (0.10 == +10%).

    Total cost basis is preserved, so per-share average cost is diluted.
    """
    if ratio < _ZERO:
        raise ValueError("stock-dividend ratio must not be negative")
    new_qty = holding.quantity * (Decimal(1) + ratio)
    if new_qty == _ZERO:
        return holding
    new_avg_amount = holding.cost_basis.amount / new_qty
    return Holding(
        ticker=holding.ticker,
        quantity=new_qty,
        average_cost=Money(new_avg_amount, holding.average_cost.currency),
    )


def apply_stock_split(holding: Holding, factor: Decimal) -> Holding:
    """Split by `factor` (2 == 2-for-1). Cost basis preserved."""
    if factor <= _ZERO:
        raise ValueError("split factor must be positive")
    new_qty = holding.quantity * factor
    new_avg_amount = holding.cost_basis.amount / new_qty if new_qty else _ZERO
    return Holding(
        ticker=holding.ticker,
        quantity=new_qty,
        average_cost=Money(new_avg_amount, holding.average_cost.currency),
    )


@dataclass(frozen=True, slots=True)
class RightsOutcome:
    holding: Holding
    cash_outflow: Money  # cash paid to subscribe (zero if not subscribed)


def apply_rights_issue(
    holding: Holding,
    ratio: Decimal,
    subscription_price: Money,
    *,
    subscribe: bool = True,
) -> RightsOutcome:
    """A rights issue entitling `ratio` new shares per share held.

    If `subscribe`, the investor pays `subscription_price` per entitled share;
    quantity increases and average cost is recomputed from total cash outlay.
    If not, the holding is unchanged (we do not model selling the rights).
    """
    if ratio < _ZERO:
        raise ValueError("rights ratio must not be negative")
    if subscription_price.currency is not holding.average_cost.currency:
        raise ValueError("subscription currency must match the holding currency")
    if not subscribe or ratio == _ZERO:
        return RightsOutcome(holding, Money(_ZERO, holding.average_cost.currency))

    entitled = holding.quantity * ratio
    cash_paid = subscription_price.scaled(entitled)
    new_qty = holding.quantity + entitled
    new_total_cost = holding.cost_basis.amount + cash_paid.amount
    new_avg_amount = new_total_cost / new_qty if new_qty else _ZERO
    new_holding = Holding(
        ticker=holding.ticker,
        quantity=new_qty,
        average_cost=Money(new_avg_amount, holding.average_cost.currency),
    )
    return RightsOutcome(new_holding, cash_paid)


def sector_exposure(
    market_values: dict[str, Money], sector_of: dict[str, str]
) -> dict[str, Decimal]:
    """Weight of each sector by market value (0..1). Unknown tickers → 'Other'."""
    total = sum((mv.amount for mv in market_values.values()), _ZERO)
    if total == _ZERO:
        return {}
    weights: dict[str, Decimal] = {}
    for ticker, mv in market_values.items():
        sector = sector_of.get(ticker, "Other")
        weights[sector] = weights.get(sector, _ZERO) + mv.amount / total
    return weights


def total_return(cost_basis: Money, market_value: Money, dividends: Money) -> Decimal | None:
    """Simple total return incl. dividends: (MV − cost + dividends) / cost.

    Returns ``None`` if there is no cost basis. Long-only, no leverage — so this
    is a straight money-weighted-free total return, appropriate for a
    buy-and-hold Vietnamese investor.
    """
    for m in (cost_basis, market_value, dividends):
        if m.currency is not cost_basis.currency:
            raise ValueError("all amounts must share one currency")
    if cost_basis.amount == _ZERO:
        return None
    return (market_value.amount - cost_basis.amount + dividends.amount) / cost_basis.amount


def _zero(currency: Currency = Currency.VND) -> Money:
    return Money(_ZERO, currency)
