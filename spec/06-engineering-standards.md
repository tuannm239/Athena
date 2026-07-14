# SPEC-06 — Engineering Standards

Status: Draft (Sprint 0)
Owner: Engineering
Last updated: 2026-07-14

## 1. Language & Frameworks

- Python 3.13; FastAPI; SQLAlchemy 2.x; Pydantic v2; Polars.
- ML: LightGBM, XGBoost, PyMC, Optuna.

## 2. Code Quality

- **100% type hints**; mypy in strict mode is a CI gate.
- Formatter + linter (ruff) enforced in CI.
- Import-boundary checks enforce Clean Architecture rules (SPEC-02 §2) and the LLM boundary (SPEC-05 §4).

## 3. Testing

- **Unit tests required** for all domain and application code.
- **Integration tests required** for repositories, APIs, and pipeline stage contracts.
- Pipeline stages get contract tests: given a fixed snapshot, outputs are reproducible.
- No merge without green tests.

## 4. Architectural Rules (hard gates)

1. No business logic in controllers.
2. No SQL in services (application layer) — repositories only.
3. API-first: OpenAPI contract merged before UI work starts.
4. Modular architecture: cross-context imports only through published contracts.

## 5. Change Management

- New capability or contract change → RFC in `/rfc`.
- Architectural decision → ADR in `/adr` (template: `adr/0000-template.md`).
- Major architectural changes wait for review before implementation (Constitution, Workflow step 10).

## 6. Definition of Done

A change is done when: typed, tested (unit + integration), documented (spec/ADR updated if contracts changed), and reviewed.
