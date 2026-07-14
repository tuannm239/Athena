# SPEC-07 — Database

> Status: Accepted Version: 1.0

# Database Specification

## Purpose

Define the persistence architecture for Athena.

Business rules belong to the Domain Layer. The database stores state
only.

------------------------------------------------------------------------

# Storage Architecture

## PostgreSQL

Primary transactional database.

Stores:

-   Users
-   Portfolios
-   Positions
-   Decisions
-   Audit logs
-   Configuration

## DuckDB

Analytical database.

Stores:

-   Historical prices
-   Financial statements
-   Factor snapshots
-   Backtesting datasets

## Redis

Caching and distributed locks.

Stores:

-   Sessions
-   API cache
-   Short-lived market context

------------------------------------------------------------------------

# Design Principles

-   UUID primary keys
-   UTC timestamps
-   Soft delete where applicable
-   Audit trail for mutable entities
-   Idempotent migrations

------------------------------------------------------------------------

# Core Tables

## users

-   id
-   email
-   status
-   created_at

## portfolios

-   id
-   user_id
-   base_currency
-   created_at

## positions

-   id
-   portfolio_id
-   ticker
-   quantity
-   average_cost

## decisions

-   id
-   hypothesis
-   probability
-   confidence
-   status
-   created_at

## evidence

-   id
-   decision_id
-   source
-   category
-   confidence

## factors

-   factor_id
-   version
-   category
-   value
-   calculated_at

------------------------------------------------------------------------

# Migration

Use Alembic.

Rules:

-   Forward-only migrations
-   Reviewed before merge
-   No destructive changes without ADR

------------------------------------------------------------------------

# Indexing

Required indexes:

-   ticker
-   portfolio_id
-   decision_id
-   created_at
-   factor_id

------------------------------------------------------------------------

# Audit

Every update to Decision, Portfolio and Position must create an
immutable audit record.

------------------------------------------------------------------------

# Backup

-   Daily full backup
-   Hourly WAL/archive
-   Restore procedure tested quarterly

------------------------------------------------------------------------

# Acceptance Criteria

-   Zero business logic in persistence layer
-   Schema versioned
-   Reproducible migrations
-   Documented indexes
