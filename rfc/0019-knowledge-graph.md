# RFC-0019 --- Knowledge Graph

**Status:** Draft  
**Version:** 1.1

------------------------------------------------------------------------

# 1. Purpose

The Knowledge Graph represents relationships across companies,
industries, macroeconomics and investment decisions.

It is the canonical relationship model used by Athena.

------------------------------------------------------------------------

# 2. Goals

- Represent financial relationships explicitly.
- Support explainable reasoning.
- Enable impact analysis.
- Be independent from storage technology.

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

## Feature

Represents a versioned feature from the Feature Store.

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

Feature -> DERIVED_FROM -> Company

Feature -> DERIVED_FROM -> Market

Decision -> USES -> Feature

------------------------------------------------------------------------

# 5. Graph Rules

- Relationships are directed.
- Every edge has a semantic type.
- Cycles are allowed only when explicitly defined.
- Nodes have globally unique identifiers.

------------------------------------------------------------------------

# 6. Reasoning

The graph supports:

- dependency traversal
- upstream impact
- downstream impact
- neighborhood search
- shortest path
- influence propagation

------------------------------------------------------------------------

# 7. Example

```text
Interest Rate Increase
        ↓
Banking Sector
        ↓
Real Estate Sector
        ↓
Steel Companies
        ↓
Company ABC
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

This guarantees reproducible graph traversal.

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
