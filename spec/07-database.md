# SPEC-07 — Database

> Status: Accepted
> Version: 1.1

# Database Specification

## Purpose

Define the persistence architecture for Athena.

Business rules belong to the Domain Layer. The database stores state only.

------------------------------------------------------------------------

# Storage Architecture

## PostgreSQL

Primary transactional database.

Stores:

- Users
- Portfolios
- Positions
- Decisions
- Audit logs
- Configuration
- Feature metadata
- Feature lifecycle
- Feature governance

## DuckDB

Analytical database.

Stores:

- Historical prices
- Financial statements
- Factor snapshots
- Feature values
- Backtesting datasets

## Redis

Caching and distributed locks.

Stores:

- Sessions
- API cache
- Short-lived market context

------------------------------------------------------------------------

# Design Principles

- UUID primary keys
- UTC timestamps
- Soft delete where applicable
- Audit trail for mutable entities
- Idempotent migrations

------------------------------------------------------------------------

# Core Tables

## users

- id
- email
- status
- created_at

## portfolios

- id
- user_id
- base_currency
- created_at

## positions

- id
- portfolio_id
- ticker
- quantity
- average_cost

## decisions

- id
- hypothesis
- probability
- confidence
- status
- created_at

## evidence

- id
- decision_id
- source
- category
- confidence

## factors

Analytical factor values stored in DuckDB.

Fields:

- factor_id
- version
- category
- value
- calculated_at

------------------------------------------------------------------------

# Feature Store Tables (RFC-0023)

## feature_registry

Stores versioned feature metadata.

Fields:

- feature_id
- feature_key
- version
- name
- owner
- description
- category
- data_type
- unit
- calculation_method
- freshness_policy
- benchmark_dataset
- test_suite
- status
- registered_at
- updated_at

Constraints:

- (feature_key, version) must be unique.
- Published feature versions are immutable.
- Lifecycle follows RFC-0023.

Indexes:

- feature_key
- version
- category
- status

------------------------------------------------------------------------

## feature_dependencies

Stores feature dependency relationships.

Fields:

- id
- feature_id
- depends_on_feature_id

Indexes:

- feature_id
- depends_on_feature_id

------------------------------------------------------------------------

# Persistence Rules

PostgreSQL stores only:

- Feature metadata
- Lifecycle state
- Governance information

DuckDB stores:

- Calculated feature values
- Factor snapshots
- Analytical datasets

Business logic SHALL NOT exist in the persistence layer.

------------------------------------------------------------------------

# Migration

Use Alembic.

Rules:

- Forward-only migrations
- Reviewed before merge
- No destructive changes without ADR

------------------------------------------------------------------------

# Indexing

Required indexes:

- ticker
- portfolio_id
- decision_id
- created_at
- factor_id
- feature_key
- version
- status

------------------------------------------------------------------------

# Audit

Every update to:

- Decision
- Portfolio
- Position
- Feature metadata

must create an immutable audit record.

------------------------------------------------------------------------

# Backup

- Daily full backup
- Hourly WAL/archive
- Restore procedure tested quarterly

------------------------------------------------------------------------

# Acceptance Criteria

- Zero business logic in persistence layer
- Schema versioned
- Reproducible migrations
- Documented indexes
- Feature Store persistence compliant with RFC-0023
