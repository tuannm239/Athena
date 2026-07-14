# SPEC-08 — API

> Status: Accepted Version: 1.0

# API Specification

## Purpose

Define the external API contract for Athena.

API-first development is mandatory. Every endpoint must be documented
before implementation.

------------------------------------------------------------------------

# Principles

-   RESTful APIs
-   OpenAPI 3.1
-   JSON only
-   Versioned endpoints (/api/v1)
-   Idempotent where appropriate
-   UTC timestamps
-   UUID identifiers

------------------------------------------------------------------------

# Authentication

-   OAuth2 / JWT
-   Role-based authorization
-   Refresh tokens
-   API keys for service integrations

------------------------------------------------------------------------

# Resource Groups

## Decisions

GET /api/v1/decisions

GET /api/v1/decisions/{id}

POST /api/v1/decisions

PATCH /api/v1/decisions/{id}

------------------------------------------------------------------------

## Portfolios

GET /api/v1/portfolios

POST /api/v1/portfolios

GET /api/v1/portfolios/{id}

GET /api/v1/portfolios/{id}/positions

------------------------------------------------------------------------

## Companies

GET /api/v1/companies/{ticker}

GET /api/v1/companies/{ticker}/factors

GET /api/v1/companies/{ticker}/research

------------------------------------------------------------------------

## Market

GET /api/v1/market/context

GET /api/v1/market/regime

GET /api/v1/market/sectors

------------------------------------------------------------------------

## Backtesting

POST /api/v1/backtests

GET /api/v1/backtests/{id}

------------------------------------------------------------------------

# Standard Response

Every response includes:

-   request_id
-   timestamp
-   status
-   data
-   errors (optional)

------------------------------------------------------------------------

# Error Codes

400 ValidationError

401 Unauthorized

403 Forbidden

404 NotFound

409 Conflict

422 BusinessRuleViolation

500 InternalError

------------------------------------------------------------------------

# API Rules

-   No business logic in controllers
-   Validation before application layer
-   Domain errors mapped to HTTP responses
-   Pagination for collections
-   Filtering and sorting supported
-   OpenAPI documentation generated automatically

------------------------------------------------------------------------

# Acceptance Criteria

-   OpenAPI specification complete
-   Backward compatible versioning
-   Integration tests for public endpoints
