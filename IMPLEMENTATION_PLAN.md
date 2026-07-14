# IMPLEMENTATION_PLAN.md

# Athena Implementation Plan

Version: 1.0

## Purpose

This document is the execution contract for Claude Code.

It converts the specification repository into an implementation plan.

Follow this document exactly.

------------------------------------------------------------------------

# Execution Order

Read every specification before writing code.

Required order:

1.  000_ENGINEERING_CONSTITUTION.md
2.  001_PRODUCT.md
3.  002_ARCHITECTURE.md
4.  003_DOMAIN_MODEL.md
5.  004_DECISION_KERNEL.md
6.  005_MARKET_ENGINE.md
7.  006_FACTOR_LIBRARY.md
8.  007_DATABASE.md
9.  008_API.md
10. 009_BACKTEST_ENGINE.md
11. 010_PORTFOLIO_ENGINE.md
12. 011_RISK_ENGINE.md
13. 012_BEHAVIOR_ENGINE.md

Do not skip any document.

------------------------------------------------------------------------

# Global Rules

-   Never invent business rules.
-   Never change architecture without approval.
-   Never move files unless requested.
-   Never implement features outside the current task.
-   Never implement AI decision making.
-   Business logic belongs only to the Domain layer.

If any specification conflicts with another specification:

STOP.

Report the conflict.

Do not guess.

------------------------------------------------------------------------

# Sprint 0

Goal:

Bootstrap the repository.

Deliverables:

-   Folder structure
-   Build configuration
-   FastAPI application
-   Dependency management
-   Docker
-   Alembic
-   Test framework
-   Empty domain modules
-   Placeholder API routes returning HTTP 501

Verification:

-   Project builds
-   Swagger loads
-   Tests pass
-   Ruff passes
-   MyPy passes

Commit:

chore: bootstrap repository

STOP.

------------------------------------------------------------------------

# Sprint 1

Goal:

Implement the Domain Layer only.

Implement:

-   Entities
-   Value Objects
-   Repository Interfaces
-   Domain Events
-   Exceptions

Do NOT implement infrastructure.

Do NOT implement APIs.

Commit:

feat(domain): implement core domain

STOP.

------------------------------------------------------------------------

# Sprint 2

Goal:

Implement Application Layer.

Implement:

-   Use Cases
-   Commands
-   Queries
-   DTOs
-   Validators

Commit:

feat(application): implement use cases

STOP.

------------------------------------------------------------------------

# Sprint 3

Goal:

Implement Infrastructure.

Implement:

-   SQLAlchemy
-   Alembic
-   PostgreSQL
-   DuckDB
-   Redis

Commit:

feat(infrastructure): implement persistence

STOP.

------------------------------------------------------------------------

# Sprint 4

Goal:

Implement REST API.

Implement endpoints defined in 008_API.md.

Generate OpenAPI.

Add integration tests.

Commit:

feat(api): implement REST endpoints

STOP.

------------------------------------------------------------------------

# Sprint 5

Goal:

Implement Decision Kernel according to 004_DECISION_KERNEL.md.

Do not add trading recommendations.

Decision output must include:

-   hypothesis
-   evidence
-   counter_evidence
-   probability
-   confidence
-   expected_utility
-   risk
-   explanation

Commit:

feat(decision): implement decision kernel

STOP.

------------------------------------------------------------------------

# Definition of Done

A sprint is complete only if:

-   Build succeeds
-   Tests pass
-   Lint passes
-   Type checking passes
-   Documentation updated
-   No architecture violations

Never continue automatically to the next sprint.

Always wait for user approval.
