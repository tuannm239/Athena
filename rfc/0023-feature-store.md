# RFC-0023 --- Feature Store

**Status:** Draft\
**Version:** 1.0

# 1. Purpose

The Feature Store provides a single, versioned source of truth for all
features used by Decision, Probability, Risk and Portfolio engines.

Features must be reproducible, immutable and discoverable.

------------------------------------------------------------------------

# 2. Goals

-   Single source of truth
-   Versioned features
-   Offline and online consistency
-   Reproducible calculations
-   Independent of ML framework

------------------------------------------------------------------------

# 3. Feature Categories

## Market Features

-   Market regime
-   Liquidity score
-   Breadth score
-   Volatility score

## Company Features

-   ROE
-   ROIC
-   Revenue Growth
-   EPS Growth
-   Debt to Equity
-   Free Cash Flow Yield

## Portfolio Features

-   Sector exposure
-   Concentration index
-   Cash ratio
-   Diversification score

## Behavioral Features

-   Bias score
-   Confidence calibration
-   Review completion rate

------------------------------------------------------------------------

# 4. Feature Metadata

Each feature must define:

-   feature_id
-   name
-   version
-   owner
-   description
-   data_type
-   unit
-   calculation_method
-   dependencies
-   freshness_policy

------------------------------------------------------------------------

# 5. Feature Lifecycle

Draft → Validated → Published → Deprecated → Archived

Published features are immutable.

------------------------------------------------------------------------

# 6. Read APIs

GetFeature(id)

GetFeatureVersion(id, version)

ListFeatures()

SearchFeatures()

------------------------------------------------------------------------

# 7. Validation Rules

Every published feature must have:

-   documentation
-   unit tests
-   benchmark dataset
-   owner
-   version
-   deterministic calculation

------------------------------------------------------------------------

# 8. Versioning

MAJOR: breaking calculation

MINOR: backward compatible enhancement

PATCH: documentation or bug fix

------------------------------------------------------------------------

# 9. Acceptance Criteria

-   Identical input produces identical feature values.
-   Historical feature versions remain queryable.
-   Decision Engine always references explicit feature versions.
-   No feature is overwritten after publication.
