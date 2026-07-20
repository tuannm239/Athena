"""Domain → API schema mappers (domain objects never serialized directly)."""

from __future__ import annotations

from api.schemas import (
    CompanyResponse,
    DecisionResponse,
    EvidenceOut,
    PortfolioResponse,
    PositionOut,
    ReviewRecordOut,
    RiskAssessmentModel,
    VnBreadth,
    VnFlow,
    VnIndexQuote,
    VnMarketSnapshotResponse,
    VnMover,
)
from company.domain.company import Company
from decision_kernel.domain.decision import Decision
from decision_kernel.domain.evidence import Evidence
from market.application.read_model import MarketSnapshotView, MoverView
from portfolio.domain.portfolio import Portfolio
from risk.domain.risk_assessment import RiskAssessment
from shared_kernel.money import Currency

_NO_FLOW = VnFlow(buy_value=0.0, sell_value=0.0, net_value=0.0)


def _movers_out(movers: tuple[MoverView, ...]) -> list[VnMover]:
    return [
        VnMover(
            ticker=m.ticker,
            price=float(m.price),
            change_pct=float(m.change_pct),
            volume=float(m.volume),
        )
        for m in movers
    ]


def vn_snapshot_out(view: MarketSnapshotView) -> VnMarketSnapshotResponse:
    """Read-model view → API response. Fields without a persisted source
    (foreign/proprietary flows, sector heatmap, 52-week highs/lows) are
    returned empty — an honest empty state, never sample values — because
    the pipeline does not yet persist them."""
    return VnMarketSnapshotResponse(
        as_of=view.as_of,
        indices=[
            VnIndexQuote(
                code=i.code,
                value=float(i.value),
                change=float(i.change),
                change_pct=float(i.change_pct),
            )
            for i in view.indices
        ],
        breadth=VnBreadth(
            advancers=view.breadth.advancers,
            decliners=view.breadth.decliners,
            unchanged=view.breadth.unchanged,
        ),
        sector_heatmap=[],
        foreign=_NO_FLOW,
        proprietary=_NO_FLOW,
        liquidity_value=float(view.liquidity_value),
        top_gainers=_movers_out(view.top_gainers),
        top_losers=_movers_out(view.top_losers),
        top_volume=_movers_out(view.top_volume),
        new_high=0,
        new_low=0,
    )


def evidence_out(item: Evidence) -> EvidenceOut:
    return EvidenceOut(
        id=item.id.value,
        source=item.source,
        category=item.category,
        explanation=item.explanation,
        reliability=item.reliability.value,
        direction=item.direction,
        metadata=dict(item.metadata),
        timestamp=item.timestamp,
    )


def risk_out(assessment: RiskAssessment | None) -> RiskAssessmentModel | None:
    if assessment is None:
        return None
    return RiskAssessmentModel(
        var=assessment.var,
        cvar=assessment.cvar,
        max_drawdown=assessment.max_drawdown,
        stress_score=assessment.stress_score,
        liquidity_score=assessment.liquidity_score,
        level=assessment.level,
        confidence=assessment.confidence.value,
    )


def decision_out(decision: Decision) -> DecisionResponse:
    return DecisionResponse(
        id=decision.id.value,
        hypothesis=decision.hypothesis,
        probability=decision.probability.value,
        confidence=decision.confidence.value,
        status=decision.status,
        decision_type=decision.decision_type,
        expected_return=decision.expected_return,
        expected_drawdown=decision.expected_drawdown,
        expected_utility=decision.expected_utility,
        position_size=decision.position_size.value if decision.position_size else None,
        portfolio_impact=decision.portfolio_impact,
        assumptions=list(decision.assumptions),
        invalidation_conditions=list(decision.invalidation_conditions),
        explanation=decision.explanation,
        evidence=[evidence_out(e) for e in decision.evidence],
        risk_assessment=risk_out(decision.risk_assessment),
        review_history=[
            ReviewRecordOut(outcome=r.outcome, at=r.at, note=r.note)
            for r in decision.review_history
        ],
        created_at=decision.created_at,
    )


def portfolio_out(portfolio: Portfolio) -> PortfolioResponse:
    return PortfolioResponse(
        id=portfolio.id.value,
        owner_id=portfolio.owner_id.value,
        base_currency=Currency(portfolio.cash_balance.currency),
        cash=portfolio.cash_balance.amount,
        allocation=portfolio.allocation,
        positions=[
            PositionOut(
                ticker=p.ticker,
                quantity=p.quantity,
                average_cost=p.average_cost.amount,
                market_value=p.market_value.amount,
                unrealized_pnl=p.unrealized_pnl.amount,
                currency=Currency(p.market_value.currency),
            )
            for p in portfolio.positions
        ],
    )


def company_out(company: Company) -> CompanyResponse:
    return CompanyResponse(
        id=company.id.value,
        ticker=company.ticker,
        name=company.name,
        exchange=company.exchange,
        sector=company.sector,
        industry=company.industry,
        currency=company.currency,
        status=company.status,
        created_at=company.created_at,
    )
