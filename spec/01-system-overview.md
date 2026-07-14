# SPEC-01 — System Overview

Status: Draft (Sprint 0)
Owner: Architecture
Last updated: 2026-07-14

## 1. Purpose

ATHENA is a Financial Decision Intelligence Platform. Its purpose is to improve the *quality* of investment decisions through explainable, probabilistic, and risk-aware analysis. It supports human decision-makers; it does not replace them and it does not execute trades.

## 2. Explicit Non-Goals

ATHENA is **not**:

1. A trading bot — it never places orders or connects to execution venues.
2. A chatbot — conversational LLM features exist only to explain and document, never to decide.
3. A stock screener — it does not rank tickers by simplistic filters as a product surface.
4. A signal generator — it does not emit standalone BUY/SELL signals detached from portfolio and risk context.

## 3. Primary Users

- Individual investors seeking structured, risk-aware decision support.
- Analysts who need explainable probabilistic reasoning over markets, sectors, and companies.

## 4. Core Capabilities (target state)

1. Ingest and normalize market, fundamental, and alternative data.
2. Maintain a knowledge graph linking companies, sectors, factors, and events.
3. Detect market regimes and condition all downstream analysis on them.
4. Produce probabilistic company and sector assessments with explicit uncertainty.
5. Assess risk before return, at portfolio level before instrument level.
6. Optimize portfolios under constraints, with a behavioral-override layer that guards against known investor biases.
7. Explain every decision output in human-readable, auditable form.
8. Learn from realized outcomes to recalibrate probabilities.

## 5. Decision Pipeline (canonical)

```text
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

Each stage is specified in SPEC-03. No stage may be bypassed. The Decision stage is owned exclusively by the **Decision Kernel** (deterministic, testable, non-LLM).

## 6. Architectural Constraints

- Domain-Driven Design: bounded contexts follow the pipeline stages and business subdomains.
- Clean Architecture: dependencies point inward; domain has zero framework dependencies.
- API-first: every capability is exposed through a versioned API before any UI is built.
- Explainability over black-box outputs: any model whose output feeds a decision must produce attributions or an interpretable surrogate.

## 7. Quality Attributes (prioritized)

1. Correctness and auditability of decisions.
2. Explainability.
3. Reproducibility (same inputs → same outputs, pinned data snapshots).
4. Modularity / replaceability of pipeline stages.
5. Performance (analysis latency is secondary to correctness).

## 8. Out of Scope for Sprint 0

Everything except: repository structure, specifications, architecture documents, and the engineering constitution.
