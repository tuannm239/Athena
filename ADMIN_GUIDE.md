# Athena — Administrator Guide (Web v1.0)

For operators who deploy and run the Athena web application. Infrastructure and
backend operations are covered in `DEPLOYMENT.md`, `OBSERVABILITY.md`,
`INCIDENT_RESPONSE.md` and `docs/product/ADMINISTRATOR_GUIDE.md`.

## Roles (RBAC)

| Role | Can |
|---|---|
| `VIEWER` | read dashboards, decisions, portfolios, reports |
| `ANALYST` | + create/update decisions, add evidence, run reviews |
| `ADMIN` | + Administration screen, API keys, user/role management |

Roles are enforced **server-side**; the UI only hides controls a role cannot
use. The **Administration** page (`/admin`, admins only) manages API keys and
shows component health.

## First run

1. Deploy the stack (`DEPLOYMENT.md`) and apply migrations.
2. Register the first user (`/login` → Register), then elevate to `ADMIN`
   server-side (`UPDATE users SET role='ADMIN' WHERE email=…`).
3. Confirm the **Administration** and role badge appear.

## Building & deploying the web app

- Production image: `web/Dockerfile` (multi-stage Next.js standalone,
  non-root), wired into `docker-compose.prod.yml` behind the Nginx TLS edge.
- Environment: `ATHENA_API_URL` points the frontend at the API; the app proxies
  `/api/*` to it. See `DEPLOYMENT.md`.
- CI: `.github/workflows/web-ci.yml` runs lint, typecheck, unit tests + coverage,
  production build, Storybook, and Playwright E2E.

## Quality gates (must stay green)

```bash
cd web
pnpm typecheck   # 0 TypeScript errors
pnpm lint        # 0 ESLint warnings
pnpm test        # unit/integration (90 passing)
pnpm build       # production build (26 routes)
pnpm exec playwright test   # auth, workflow, and screenshot specs
```

## Screenshots

`pnpm exec playwright test screenshots` regenerates the full page catalog into
`web/tests/e2e/screenshots/` (see `SCREENSHOT_CATALOG.md`).

## Client-side data

UX preferences, favorites, pinned companies, saved filters, notes/attachments,
notification read-state and feedback are stored in the browser's localStorage
(keys `athena-ux`, `athena-notes`, `athena-notifications`, `athena-feedback`).
Clearing site data resets them harmlessly. The backend remains the system of
record for decisions and evidence.

## Guardrails to preserve

Athena must never execute trades or connect to a broker; there is no execution
path in the app. Human approval is mandatory for every decision. LLMs may
summarize/explain/extract but never produce BUY/SELL decisions. Keep it so.

## Support surfaces

`/notifications`, `/help`, `/feedback`, `/about`, `/release-notes` are all
in-app. Users' feedback is stored locally in this pilot; collect it from the
Feedback page during UAT.
