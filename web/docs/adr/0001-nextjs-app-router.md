# FE-ADR-0001 — Next.js 15 App Router + TypeScript

- Status: Accepted · Date: 2026-07-18

## Decision
Use Next.js 15 (App Router, React 19) with strict TypeScript. Server
Components by default; client components only where interactivity/state is
needed (`"use client"`). Rationale: code-splitting per route, streaming,
first-class TS, and the documented stack for this project.

## Consequences
- File-system routing under `app/`; each nav destination is a folder.
- `tsc` type-checks app code strictly; tests are validated by running
  (Vitest/esbuild), so `tsconfig` excludes `tests/` and `stories/`.
- TypeScript pinned to 5.6 (Next 15's supported line; 7.x pre-release
  broke webpack tsconfig-paths resolution).
