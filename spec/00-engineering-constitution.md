# SPEC-00 — Engineering Constitution

> Status: Accepted\
> Version: 1.0

# Engineering Constitution

## Purpose

This document defines the non-negotiable engineering principles for
Project Athena.

Every architectural decision, implementation, and review MUST comply
with this constitution.

------------------------------------------------------------------------

# Mission

Athena is a **Financial Decision Intelligence Platform**.

Athena is not:

-   A trading bot
-   A stock screener
-   A chatbot
-   A signal generator

Athena exists to improve investment decision quality through
explainable, probabilistic, and risk-aware reasoning.

------------------------------------------------------------------------

# Product Principles

1.  Decision quality is more important than prediction accuracy.
2.  Risk management has higher priority than return maximization.
3.  Portfolio optimization has higher priority than single asset
    selection.
4.  Every recommendation must be explainable.
5.  Every model must be backtestable.
6.  Every business rule must be testable.

------------------------------------------------------------------------

# Architecture Principles

-   Domain-Driven Design (DDD)
-   Clean Architecture
-   Hexagonal Architecture
-   SOLID
-   API-first
-   Event-driven where appropriate
-   Modular Monolith for v1
-   Easy migration to microservices

------------------------------------------------------------------------

# Engineering Rules

## Domain First

Order of implementation:

1.  Domain
2.  Application
3.  Infrastructure
4.  API
5.  UI

Business rules never belong in controllers or UI.

## LLM Policy

LLMs may:

-   Summarize
-   Explain
-   Extract
-   Classify
-   Generate reports

LLMs must not:

-   Produce BUY/SELL decisions
-   Allocate capital
-   Contain business logic

Business logic belongs exclusively to the Decision Kernel.

------------------------------------------------------------------------

# Decision Philosophy

Every decision must include:

-   Hypothesis
-   Evidence
-   Counter Evidence
-   Probability
-   Confidence
-   Risk
-   Expected Utility
-   Portfolio Impact
-   Invalidation Conditions

------------------------------------------------------------------------

# Coding Standards

-   Python 3.13
-   FastAPI
-   SQLAlchemy 2.x
-   Pydantic v2
-   Strict typing
-   Unit tests required
-   Integration tests required
-   OpenAPI documentation
-   No circular dependencies

------------------------------------------------------------------------

# Data Stack

-   PostgreSQL
-   DuckDB
-   Redis

------------------------------------------------------------------------

# ML Stack

-   LightGBM
-   XGBoost
-   PyMC
-   Optuna

------------------------------------------------------------------------

# Repository Layout

/spec /rfc /adr /backend /frontend /tests /scripts /infrastructure

------------------------------------------------------------------------

# Acceptance Criteria

A change is accepted only if:

-   Architecture remains consistent.
-   Tests pass.
-   Documentation is updated.
-   ADR is created for architectural changes.
-   Public APIs remain documented.

------------------------------------------------------------------------

# Definition of Done

A feature is complete only when:

-   Domain model implemented.
-   Business rules tested.
-   API documented.
-   Observability added.
-   Documentation updated.
-   Backtest added if decision logic changes.

------------------------------------------------------------------------

# Governance

This constitution has the highest priority within the repository.

Any conflicting implementation must be rejected or revised.
