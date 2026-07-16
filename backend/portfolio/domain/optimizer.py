"""Portfolio construction — ALG-008 (SPEC-10).

Deterministic greedy allocator with SPEC-10 priority order:
1. constraint satisfaction, 2. risk reduction, 3. expected utility,
4. expected return. Candidates are considered in descending expected
utility (ties broken by ticker) and only while every constraint holds;
cash never goes negative; every capped or skipped candidate is reported.
Only candidates with positive expected utility are allocated —
maximizing utility never allocates into negative expected utility.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from portfolio.domain.constraints import PortfolioConstraints
from portfolio.domain.sizing import position_size
from shared_kernel.identifiers import DecisionId
from shared_kernel.probability import Confidence, Probability

_ZERO = Decimal(0)
_ONE = Decimal(1)


@dataclass(frozen=True, slots=True)
class Candidate:
    """A decision's sizing inputs (SPEC-10 §Inputs, Decision Objects)."""

    decision_id: DecisionId
    ticker: str
    sector: str
    posterior: Probability
    confidence: Confidence
    expected_return: Decimal
    expected_drawdown: Decimal
    expected_utility: Decimal
    liquidity_factor: Decimal = _ONE


@dataclass(frozen=True, slots=True)
class Allocation:
    ticker: str
    weight: Decimal
    expected_utility_contribution: Decimal


@dataclass(frozen=True, slots=True)
class PortfolioProposal:
    """SPEC-10 §Output: allocation, sizes, cash, utility, drawdown,
    constraint violations, explanation."""

    allocations: tuple[Allocation, ...]
    cash_weight: Decimal
    expected_utility: Decimal
    expected_drawdown: Decimal
    constraint_violations: tuple[str, ...]
    explanation: str


def propose_portfolio(
    candidates: tuple[Candidate, ...],
    *,
    constraints: PortfolioConstraints,
    risk_budget: Decimal,
) -> PortfolioProposal:
    """Greedy utility-descending allocation under SPEC-10 constraints."""
    ordered = sorted(candidates, key=lambda c: (-c.expected_utility, c.ticker))
    max_weight = constraints.max_position_weight.value if constraints.max_position_weight else None
    max_sector = constraints.max_sector_exposure.value if constraints.max_sector_exposure else None
    min_cash = constraints.min_cash_reserve.value if constraints.min_cash_reserve else _ZERO

    allocations: list[Allocation] = []
    notes: list[str] = []
    sector_totals: dict[str, Decimal] = {}
    invested = _ZERO

    for candidate in ordered:
        if candidate.expected_utility <= 0:
            notes.append(f"{candidate.ticker}: skipped (non-positive expected utility)")
            continue
        size = position_size(
            posterior=candidate.posterior,
            expected_return=candidate.expected_return,
            expected_drawdown=candidate.expected_drawdown,
            risk_budget=risk_budget,
            liquidity_factor=candidate.liquidity_factor,
            confidence=candidate.confidence,
            max_position_weight=max_weight,
        ).value
        if size == 0:
            notes.append(f"{candidate.ticker}: skipped (sized to zero)")
            continue

        available = _ONE - min_cash - invested
        if available <= 0:
            notes.append(f"{candidate.ticker}: skipped (cash reserve reached)")
            continue
        if size > available:
            notes.append(f"{candidate.ticker}: capped by cash reserve to {available}")
            size = available

        sector_used = sector_totals.get(candidate.sector, _ZERO)
        if max_sector is not None and sector_used + size > max_sector:
            capped = max_sector - sector_used
            if capped <= 0:
                notes.append(f"{candidate.ticker}: skipped (sector cap {candidate.sector})")
                continue
            notes.append(f"{candidate.ticker}: capped by sector exposure to {capped}")
            size = capped

        allocations.append(
            Allocation(
                ticker=candidate.ticker,
                weight=size,
                expected_utility_contribution=size * candidate.expected_utility,
            )
        )
        sector_totals[candidate.sector] = sector_used + size
        invested += size

    utility = sum((a.expected_utility_contribution for a in allocations), _ZERO)
    by_ticker = {c.ticker: c for c in candidates}
    drawdown = sum((a.weight * by_ticker[a.ticker].expected_drawdown for a in allocations), _ZERO)
    explanation = (
        f"Allocated {len(allocations)} of {len(candidates)} candidates in descending "
        f"expected-utility order under risk_budget={risk_budget}; invested={invested}, "
        f"cash={_ONE - invested}. " + ("; ".join(notes) if notes else "No constraints binding.")
    )
    return PortfolioProposal(
        allocations=tuple(allocations),
        cash_weight=_ONE - invested,
        expected_utility=utility,
        expected_drawdown=drawdown,
        constraint_violations=tuple(notes),
        explanation=explanation,
    )
