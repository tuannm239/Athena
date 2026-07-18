# FE-ADR-0004 — Dark-mode-first HSL design system

- Status: Accepted · Date: 2026-07-18

## Decision
A Bloomberg/FactSet/Morningstar-inspired, dense, minimal financial UI.
Colors are HSL CSS variables (`--background`, `--gain`, `--loss`, …) so
light/dark swap without re-declaring palettes; dark is the `:root` default,
`.light` opts in. shadcn-style primitives via `class-variance-authority`.

## Consequences
- Semantic financial tokens (`gain`/`loss`/`warn`) keep P&L coloring
  consistent and theme-aware.
- WCAG-AA contrast maintained in both themes; visible focus rings for
  keyboard users.
