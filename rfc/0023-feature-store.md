# RFC-0023 --- Feature Store

**Status:** Draft\
**Version:** 1.1

------------------------------------------------------------------------

# 1. Purpose

The Feature Store provides a single, versioned source of truth for all
features used by Decision, Probability, Risk and Portfolio engines.

Features must be reproducible, immutable and discoverable.

------------------------------------------------------------------------

# 2. Goals

- Single source of truth
- Versioned features
- Offline and online consistency
- Reproducible calculations
- Independent of ML framework

------------------------------------------------------------------------

# 3. Feature Categories

## Market Features

- Market regime
- Liquidity score
- Breadth score
- Volatility score

## Company Features

- ROE
- ROIC
- Revenue Growth
- EPS Growth
- Debt to Equity
- Free Cash Flow Yield

## Technical Features

### Trend

- SMA (5, 10, 20, 50, 100, 200)
- EMA (12, 26, 50)
- Golden Cross
- Death Cross
- ADX (14)

### Momentum

- RSI (14)
- MACD
- MACD Signal
- MACD Histogram
- Stochastic Oscillator
- Williams %R
- Rate of Change (ROC)

### Volatility

- ATR (14)
- Bollinger Bands
- Historical Volatility (20D)
- True Range

### Volume

- Average Volume (20D)
- Volume Ratio
- On-Balance Volume (OBV)
- Money Flow Index (MFI)
- Accumulation / Distribution Line (A/D)

### Relative Strength

- Relative Strength vs VNINDEX
- Relative Strength vs Sector
- Momentum (1M)
- Momentum (3M)
- Momentum (6M)
- Momentum (12M)

## Portfolio Features

- Sector exposure
- Concentration index
- Cash ratio
- Diversification score

## Behavioral Features

- Bias score
- Confidence calibration
- Review completion rate

------------------------------------------------------------------------

# 4. Feature Metadata

Each feature must define:

- feature_id
- name
- version
- owner
- description
- data_type
- unit
- calculation_method
- dependencies
- freshness_policy
- frequency

------------------------------------------------------------------------

# 4.1 Feature Classification

Every feature belongs to exactly one category.

| Category | Description |
|----------|-------------|
| Market | Derived from market-wide data |
| Company | Derived from company fundamentals |
| Technical | Derived from historical price and volume |
| Portfolio | Derived from portfolio composition |
| Behavioral | Derived from user decision behavior |

A feature may depend on multiple raw datasets but must belong to a single category.

------------------------------------------------------------------------

# 4.2 Feature Naming Convention

Feature identifiers are globally unique.

Feature identifiers should follow a consistent namespace.

Examples

```text
TECH.RSI.14
TECH.SMA.20
TECH.EMA.50
TECH.MACD
TECH.ADX.14

FUND.ROE
FUND.ROIC
FUND.PE
FUND.PB
FUND.FCF_YIELD

MARKET.LIQUIDITY_SCORE
MARKET.BREADTH_SCORE
MARKET.VOLATILITY_SCORE

PORT.SECTOR_EXPOSURE
PORT.CONCENTRATION
PORT.CASH_RATIO
PORT.DIVERSIFICATION

BEHAVIOR.BIAS_SCORE
BEHAVIOR.CONFIDENCE_CALIBRATION
BEHAVIOR.REVIEW_COMPLETION
```

------------------------------------------------------------------------

# 4.3 Technical Feature Rules

Technical features are deterministic transformations of persisted market data.

Technical features must never depend on:

- Model predictions
- AI inference
- Decision outputs
- Probability scores

Every rolling technical feature must define:

- lookback window
- warm-up period
- missing-data policy

Given identical historical market data, identical technical features must always produce identical values.

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

- documentation
- unit tests
- benchmark dataset
- owner
- version
- deterministic calculation

------------------------------------------------------------------------

# 8. Versioning

MAJOR: breaking calculation

MINOR: backward compatible enhancement

PATCH: documentation or bug fix

------------------------------------------------------------------------

# 9. Acceptance Criteria

- Identical input produces identical feature values.
- Historical feature versions remain queryable.
- Decision Engine always references explicit feature versions.
- No feature is overwritten after publication.
- Every feature belongs to exactly one category.
- Every feature has a unique feature_id.
- Every published feature is reproducible.
- Every feature declares its dependencies.
- Technical features are computed only from persisted market data.
