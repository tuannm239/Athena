# Athena Web Application

The frontend for the **Athena Financial Decision Intelligence Platform** —
a Bloomberg/FactSet/Morningstar-inspired, dark-mode-first web app that helps
humans make **explainable, probabilistic, risk-aware** investment decisions.

> Athena is **not** a trading app or a broker. It assists decisions; **human
> approval is mandatory**. No order-execution path exists (enforced by the
> backend, mirrored by the UI).

## Stack

| Concern | Choice |
|---|---|
| Framework | Next.js 15 (App Router) · React 19 · TypeScript 5.6 |
| Styling | TailwindCSS 3 (dark-mode-first HSL design system) |
| Data | TanStack Query · typed SPEC-08 API client |
| State | Zustand (auth + RBAC) |
| Charts | SVG gauges (built-in); Recharts available |
| Markdown | react-markdown |
| Auth | JWT + refresh-token rotation |
| Testing | Vitest + Testing Library · Playwright (e2e) · Storybook |
| Package manager | pnpm |

## Getting started

```bash
pnpm install
ATHENA_API_URL=http://localhost:8000 pnpm dev   # proxies /api/* to the backend
```

The app expects the Athena backend (SPEC-08) at `ATHENA_API_URL`
(default `http://localhost:8000`). `/api/*` requests are proxied there by
`next.config.mjs`.

## Scripts

| Script | Purpose |
|---|---|
| `pnpm dev` | dev server |
| `pnpm build` / `pnpm start` | production build / serve |
| `pnpm typecheck` | `tsc --noEmit` (app code) |
| `pnpm lint` | ESLint (next/core-web-vitals) |
| `pnpm test` / `pnpm test:cov` | Vitest unit tests / coverage |
| `pnpm e2e` | Playwright end-to-end |
| `pnpm storybook` / `pnpm build-storybook` | component workshop |

## Architecture

```
app/          Next.js App Router routes (one folder per feature area)
components/    ui/ primitives (shadcn-style) + layout/ shell
features/      feature-specific composite components (e.g. decision review)
providers/     React context: Theme (dark-first), Query, Auth guard
services/      typed API service modules (one per domain) + MockProvider
stores/        Zustand stores (auth + RBAC)
hooks/         TanStack Query hooks
lib/           api-client (JWT/refresh/retry), tokens, utils, navigation
types/         SPEC-08 wire types (mirror backend Pydantic schemas)
tests/         Vitest unit tests + e2e/ Playwright specs
stories/       Storybook stories
public/        manifest, service worker, PWA icons
```

See `docs/adr/` for frontend architecture decisions and
`FRONTEND_STATUS.md` (repo root) for the acceptance-criteria status.

## Backend integration & MockProvider

The app consumes the existing backend REST API only — it never changes
domain models. Endpoints that are not yet exposed (they return
`501 NotImplemented`, e.g. `/market`, company factors, `/backtests`) are
handled by the **MockProvider** (`services/mock-provider.ts`): a service
tries the real endpoint first and, only on a 501, falls back to clearly
labelled sample data (a "sample data" badge appears in the UI). When the
endpoint ships, the real path succeeds and the mock **stops firing
automatically — no code change required**.

## Security

- JWT access token in memory; refresh token in localStorage; transparent
  single-flight refresh rotation on 401.
- RBAC mirrored client-side (VIEWER/ANALYST/ADMIN); the backend remains the
  enforcement authority on every request.
- No secrets in the bundle; API base is same-origin via the proxy.

## Accessibility

Keyboard-navigable, ARIA-labelled, visible focus rings, skip-to-content
link, WCAG-AA contrast in both themes. Storybook runs the a11y addon.
