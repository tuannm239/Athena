# SPEC-03 — Domain Model

> Status: Accepted Version: 1.0

# Domain Model Specification

## Purpose

This document defines the core business domain of Athena.

The Domain Layer is the heart of the platform and contains all business
rules. Infrastructure, APIs and UI must depend on this model---not the
reverse.

------------------------------------------------------------------------

# Bounded Contexts

1.  Decision
2.  Market
3.  Company
4.  Portfolio
5.  Risk
6.  Research
7.  Behavior
8.  Identity

Each context owns its aggregates and exposes behavior through
application services.

------------------------------------------------------------------------

# Core Aggregate: Decision

## Responsibilities

-   Evaluate an investment hypothesis
-   Store evidence and counter-evidence
-   Maintain probability and confidence
-   Record assumptions
-   Track review outcome

### Decision State

Draft → UnderReview → Approved → Rejected → Archived

------------------------------------------------------------------------

# Entities

## Decision

Attributes

-   decision_id
-   hypothesis
-   probability
-   confidence
-   expected_return
-   expected_drawdown
-   expected_utility
-   status
-   created_at

Relations

-   Evidence\[\]
-   CounterEvidence\[\]
-   RiskAssessment
-   PortfolioImpact
-   ReviewHistory

------------------------------------------------------------------------

## Company

-   ticker
-   exchange
-   industry
-   sector
-   quality_score
-   valuation_score
-   growth_score

------------------------------------------------------------------------

## Portfolio

-   portfolio_id
-   owner_id
-   cash_balance
-   positions
-   constraints

------------------------------------------------------------------------

## Position

-   ticker
-   quantity
-   average_cost
-   market_value
-   unrealized_pnl

------------------------------------------------------------------------

## Evidence

-   source
-   category
-   description
-   confidence
-   timestamp

------------------------------------------------------------------------

## RiskAssessment

-   var
-   cvar
-   max_drawdown
-   stress_score
-   liquidity_score

------------------------------------------------------------------------

# Value Objects

-   Probability
-   Confidence
-   Money
-   Percentage
-   TimeRange
-   PositionSize
-   Currency

Value Objects are immutable.

------------------------------------------------------------------------

# Domain Services

DecisionEvaluator

ProbabilityCalculator

PortfolioOptimizer

RiskCalculator

BehaviorAnalyzer

ScenarioSimulator

No persistence logic is allowed in domain services.

------------------------------------------------------------------------

# Repository Interfaces

DecisionRepository

CompanyRepository

PortfolioRepository

MarketRepository

ResearchRepository

Repositories are interfaces only.

Implementations belong to Infrastructure.

------------------------------------------------------------------------

# Domain Events

DecisionCreated

DecisionReviewed

PortfolioUpdated

RiskCalculated

MarketRegimeChanged

EvidenceAdded

BehaviorDetected

All events are immutable.

------------------------------------------------------------------------

# Invariants

-   Probability ∈ \[0,1\]
-   Confidence ∈ \[0,1\]
-   Portfolio allocation ≤ 100%
-   Every approved Decision must have at least one Evidence and one
    RiskAssessment.
-   A Decision cannot transition directly from Draft to Archived.

------------------------------------------------------------------------

# Ubiquitous Language

Decision: A structured evaluation of an investment hypothesis.

Hypothesis: A statement that can be supported or invalidated.

Evidence: Objective information supporting or contradicting a
hypothesis.

Utility: Expected value adjusted for risk.

Confidence: The reliability of the current evaluation.

------------------------------------------------------------------------

# Acceptance Criteria

-   Domain has no infrastructure dependencies.
-   Entities enforce invariants.
-   Value Objects are immutable.
-   Repository interfaces are implementation-agnostic.
-   Domain Events are published through the application layer.
