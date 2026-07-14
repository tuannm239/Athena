# SPEC-02 — Architecture Specification

> Status: Accepted Version: 1.0

# Architecture Specification

## Purpose

Define the software architecture for Athena.

------------------------------------------------------------------------

# Architectural Style

-   Domain Driven Design
-   Clean Architecture
-   Hexagonal Architecture
-   Modular Monolith (v1)
-   Event-driven where appropriate
-   API-first

------------------------------------------------------------------------

# C4 Context

External Systems

-   Market Data Providers
-   News Providers
-   Macro Data Providers
-   LLM Providers
-   Authentication Provider

Primary Users

-   Investor
-   Research Analyst
-   Portfolio Manager
-   Administrator

------------------------------------------------------------------------

# Logical Layers

Presentation

-   Web
-   REST API
-   CLI

Application

-   Use Cases
-   Commands
-   Queries

Domain

-   Decision Kernel
-   Portfolio
-   Risk
-   Market
-   Company
-   Behavior

Infrastructure

-   Database
-   Cache
-   ETL
-   Message Bus
-   External APIs

------------------------------------------------------------------------

# Bounded Contexts

-   Decision
-   Market
-   Company
-   Portfolio
-   Risk
-   Research
-   Identity
-   Notification

No bounded context may directly modify another context's aggregates.

------------------------------------------------------------------------

# Dependency Rule

Presentation ↓ Application ↓ Domain ↑ Infrastructure

Outer layers depend on inner layers only.

------------------------------------------------------------------------

# Core Components

## Decision Kernel

Owns:

-   hypothesis
-   probability
-   utility
-   evidence
-   explanation

## Market Engine

Owns:

-   market regime
-   liquidity
-   breadth
-   volatility

## Company Engine

Owns:

-   fundamentals
-   valuation
-   quality
-   catalysts

## Portfolio Engine

Owns:

-   allocation
-   exposure
-   diversification
-   position sizing

## Risk Engine

Owns:

-   VaR
-   CVaR
-   stress tests
-   drawdown

## Behavior Engine

Owns:

-   bias detection
-   decision review
-   investor profile

------------------------------------------------------------------------

# Data Flow

External Data → ETL → Data Lake → Feature Store → Knowledge Graph →
Decision Kernel → API → UI

------------------------------------------------------------------------

# Repository Layout

backend/ domain/ application/ infrastructure/ api/ frontend/ spec/
tests/

------------------------------------------------------------------------

# Technology

Backend: - Python 3.13 - FastAPI

Data: - PostgreSQL - DuckDB - Redis

ML: - LightGBM - XGBoost - PyMC

Frontend: - Next.js - React

------------------------------------------------------------------------

# Architectural Constraints

-   No business logic in controllers.
-   No ORM entities inside domain.
-   Domain must not depend on infrastructure.
-   Every module has its own README and tests.

------------------------------------------------------------------------

# Acceptance Criteria

-   Architecture diagrams maintained.
-   Dependency rules enforced.
-   Public APIs documented.
-   Domain isolated from infrastructure.
