# GitHub Release Draft — Athena v1.0

Ready-to-publish draft. Publishing a GitHub release requires a maintainer
action (tag + release); this file is the prepared content.

- **Tag:** `v1.0`
- **Target:** `claude/git-bundle-clone-athena-e85fxc` (or `main` after merge)
- **Title:** `Athena v1.0 — Productization`
- **Type:** Draft (do not mark "latest" until product-owner sign-off)

## To publish

```bash
# From a maintainer machine with the repo checked out at the release commit:
git tag -a v1.0 -m "Athena v1.0 — Productization"
git push origin v1.0
# then create the release from the tag (GitHub UI, or `gh release create v1.0 \
#   --draft --title "Athena v1.0 — Productization" --notes-file docs/release/GITHUB_RELEASE_DRAFT.md`)
```

---

## Release body

**Athena v1.0 — Productization**

Athena is a Financial Decision Intelligence Platform. It generates explainable,
probabilistic, risk-aware **Decision Objects** for a human to approve. It
executes no trades and connects to no broker.

### Highlights
- ⌘K **command palette & global search** — instant navigation and lookup.
- **Redesigned dashboard** — 10 widgets (market, decisions, reviews, portfolio,
  health, evidence, regime, risk, probability, activity).
- **In-app notifications** — review reminders and pipeline/provider/system
  alerts (no email/SMS).
- **Export everywhere** — CSV, Excel, PDF, JSON — and a **Reports** page
  (Decision, Portfolio, Risk, Daily/Weekly/Monthly, Backtest, Scenario).
- **Personalization** — favorites, recent items, pinned companies, saved
  filters, and preferences (theme, density, reduce-motion, landing page).
- **Accessibility & polish** — keyboard help (`?`), skip-link, focus rings,
  reduced-motion and density support, mobile navigation.
- **Product documentation** — Quick Start, User, Admin, Troubleshooting,
  Architecture and API guides.

### Compatibility
No breaking API changes; no new investment algorithms; no architecture or
backend redesign. All Phase-6 work is additive and frontend-side.

### Safety posture (unchanged)
No trade execution · no broker integration · Decision Objects only · human
approval mandatory · full audit trail · LLMs never produce decisions.

### Quality
Web: typecheck, ESLint, 76 unit tests, production build — all green.
Backend (unchanged since Phase 5): 365 tests, 95.57% coverage, mypy strict,
ruff clean.

See `ATHENA_v1.0_RELEASE.md`, `docs/release/RELEASE_NOTES.md`,
`docs/release/KNOWN_ISSUES.md`, and `docs/release/UPGRADE_GUIDE.md`.

**Known limitations:** some views use clearly-labelled sample data until live
feeds connect; one production provider (Alpha Vantage) wired; Backtest/Scenario
reports await their data source; reports/search are client-side; no OTel
tracing. None blocks the human-in-the-loop internal pilot.
