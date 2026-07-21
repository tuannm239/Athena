# RFC-0019 --- Knowledge Graph

**Status:** Draft  
**Version:** 1.1

------------------------------------------------------------------------

# 1. Purpose

The Knowledge Graph represents relationships across companies,
industries, macroeconomics, investment decisions and versioned features.

It is the canonical relationship model used by Athena.

The Knowledge Graph provides explainable relationship reasoning across
the entire investment platform while remaining independent from any
graph database implementation.

------------------------------------------------------------------------

# 2. Goals

- Represent financial relationships explicitly.
- Support explainable reasoning.
- Enable impact analysis.
- Integrate with the Feature Store.
- Remain independent from storage technology.

------------------------------------------------------------------------

# 3. Node Types

## Company

- ticker
- name
- exchange

## Industry

## Sector

## Country

## Currency

## Commodity

## Macro Indicator

Examples:

- Interest Rate
- Inflation
- GDP
- PMI

## Event

Examples:

- Central bank decision
- Earnings release
- Regulatory change
- Merger
- Supply disruption

## Decision

Represents an evaluated investment hypothesis.

## Evidence

Represents structured evidence consumed by the Probability Engine.

## Feature

Represents a versioned feature published by the Feature Store.

Examples:

- ROE
- ROIC
- RSI(14)
- Market Regime
- Liquidity Score

------------------------------------------------------------------------

# 4. Relationship Types

Company -> BELONGS_TO -> Industry

Industry -> BELONGS_TO -> Sector

Company -> SUPPLIES -> Company

Company -> COMPETES_WITH -> Company

Commodity -> IMPACTS -> Industry

Macro Indicator -> INFLUENCES -> Sector

Event -> AFFECTS -> Company

Decision -> REFERENCES -> Company

Decision -> SUPPORTED_BY -> Evidence

Decision -> CONTRADICTED_BY -> Evidence

Decision -> USES -> Feature

Feature -> DERIVED_FROM -> Company

Feature -> DERIVED_FROM -> Market

------------------------------------------------------------------------

# 5. Graph Rules

- Relationships are directed.
- Every edge has a semantic type.
- Nodes have globally unique identifiers.
- Cycles are allowed only when explicitly defined.
- Every Decision must reference versioned Features.
- Graph traversal must be deterministic.

------------------------------------------------------------------------

# 6. Reasoning

The graph supports:

- dependency traversal
- upstream impact
- downstream impact
- neighborhood search
- shortest path
- influence propagation
- relationship explanation

------------------------------------------------------------------------

# 7. Example

```text
Interest Rate Increase
        ↓
Banking Sector
        ↓
Real Estate Sector
        ↓
Steel Industry
        ↓
Company ABC
        ↓
Feature: Earnings Growth Score
        ↓
Decision #12345
```

------------------------------------------------------------------------

# 8. Update Rules

Graph updates must be:

- versioned
- auditable
- reproducible

Historical relationships must remain queryable.

## Graph Version

Every graph snapshot must include:

- graph_version
- feature_snapshot
- created_at

This guarantees reproducible graph traversal across releases.

------------------------------------------------------------------------

# 9. Public Services

- FindNeighbors()
- FindImpacts()
- FindDependencies()
- ExplainRelationship()
- Traverse()

------------------------------------------------------------------------

# 10. Acceptance Criteria

- Deterministic traversal.
- Explainable relationship paths.
- Versioned graph changes.
- Independent from graph database implementation.
- Every Decision references versioned Features.
- Every graph snapshot includes graph_version.
- Historical graph states remain reproducible.
- Identical graph snapshot produces identical traversal results.
