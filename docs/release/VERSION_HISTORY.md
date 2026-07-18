# Athena — Version History

| Version | Date | Summary |
|---|---|---|
| **v1.0** | 2026-07-18 | **Productization (Phase 6).** Command palette + global search, redesigned 10-widget dashboard, in-app notifications, export (CSV/Excel/PDF/JSON), Reports, personalization (favorites/recent/pinned/saved filters/preferences), UX polish + accessibility, product documentation. No API/architecture changes. |
| v0.9 (pilot) | 2026-07-18 | **Production deployment & pilot (Phase 5).** Production images, Nginx TLS edge, CI/CD with CVE + image scanning, Prometheus/Grafana/Alertmanager observability, security hardening, backup/restore + DR, pilot mode, first production data provider (Alpha Vantage), production validation → GO WITH CONDITIONS. |
| v0.4 (platform) | 2026 | **Platform complete (Phases 1–4).** Decision Kernel, Probability/Risk/Portfolio/Market-Regime/Behavior engines, Knowledge Graph, Feature Store, Data Pipeline, Decision DSL + Compiler, Backtest, Scenario Simulator; REST API (SPEC-08); Next.js frontend; quant research program. |

## Backend API version

The backend app version is `0.4.0` (SPEC-08 contract). Phase 5–6 did not change
the REST contract; the product `v1.0` denotes the overall release milestone.

## Conventions

- Backend migrations are forward-only (SPEC-07).
- Web UX state is versioned in `localStorage` (currently v1).
- Architectural decisions are recorded as ADRs under `/adr`.

Full detail per release is in `RELEASE_NOTES.md`; see the git history and
`CHANGELOG.md` for commit-level changes.
