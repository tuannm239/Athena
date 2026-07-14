# SPEC-05 — LLM Policy

Status: Accepted principle (Sprint 0)
Owner: Architecture
Last updated: 2026-07-14

## 1. Principle

**LLMs never make investment decisions.** (Constitution, Core Principle 7.)

## 2. Permitted LLM Uses

LLMs may:

1. **Summarize** — condense documents, filings, and news into structured summaries.
2. **Classify** — assign labels (e.g., event type, sentiment category) that enter the pipeline as *features with provenance*, subject to the same quality gates as any other feature.
3. **Explain** — phrase the Explanation stage output from structured facts produced by the Decision Kernel and upstream stages.
4. **Debate** — generate argument/counter-argument analyses for human review.
5. **Generate documentation** — specs, ADR drafts, developer docs.

## 3. Prohibited LLM Uses

LLMs must not:

1. Generate BUY/SELL decisions or anything a user could reasonably interpret as one.
2. Allocate capital or propose position sizes.
3. Embed business logic (no prompts acting as unreviewed decision rules).
4. Bypass the Decision Kernel — no LLM output may flow into the Decision stage.

## 4. Architectural Enforcement

- Single **LLM Gateway** module; it is the only place LLM clients may be imported.
- The `decision_kernel`, `risk`, `portfolio`, and `behavior` modules have **no import path** to the LLM Gateway (enforced by import-linting in CI).
- LLM outputs entering the pipeline (summaries, classifications) are tagged `source: llm` in lineage, with model ID, prompt version, and timestamp.
- Explanation outputs are validated: every factual claim must map to a lineage item; unverifiable claims fail the explanation build.

## 5. Review

Any change to this policy requires an RFC plus an ADR with explicit sign-off.
