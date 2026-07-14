# CLAUDE.md

# ATHENA Engineering Constitution

## Mission

ATHENA is a Financial Decision Intelligence Platform.

It is **not**:
- a trading bot
- a chatbot
- a stock screener
- a signal generator

Its purpose is to improve investment decision quality through
explainable, probabilistic, and risk-aware analysis.

## Core Principles

1.  Architecture before implementation.
2.  Domain-Driven Design.
3.  Clean Architecture.
4.  Explainability over black-box outputs.
5.  Risk before return.
6.  Portfolio before individual stock.
7.  LLMs never make investment decisions.

## Repository Structure

``` text
/spec
/rfc
/adr
/backend
/frontend
/infrastructure
/tests
/scripts
```

## Development Workflow

1.  Read all specification files.
2.  Review architecture.
3.  Identify missing specifications.
4.  Create ADRs when needed.
5.  Build domain models.
6.  Build application services.
7.  Build APIs.
8.  Build UI.
9.  Add tests.
10. Wait for review before major architectural changes.

## Decision Pipeline

``` text
Data
→ Normalization
→ Feature Engineering
→ Knowledge Graph
→ Market Regime
→ Sector Analysis
→ Company Analysis
→ Probability Update
→ Risk Assessment
→ Portfolio Optimization
→ Behavioral Override
→ Decision
→ Explanation
→ Learning
```

## LLM Policy

LLMs may:
- summarize
- classify
- explain
- debate
- generate documentation

LLMs must not:
- generate BUY/SELL decisions
- allocate capital
- embed business logic
- bypass Decision Kernel

## Technology

Backend:
- Python 3.13
- FastAPI
- SQLAlchemy 2.x
- Pydantic v2

Data:
- PostgreSQL
- DuckDB
- Redis

Analytics:
- Polars

ML:
- LightGBM
- XGBoost
- PyMC
- Optuna

## Coding Standards

-   100% type hints
-   Unit tests required
-   Integration tests required
-   No business logic in controllers
-   No SQL in services
-   API-first
-   Modular architecture

## Deliverables for Sprint 0

Create only:
- Repository structure
- Specifications
- Architecture documents
- Engineering constitution

Do not implement business logic.
