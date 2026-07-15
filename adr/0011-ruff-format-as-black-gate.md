# ADR-0011 — `ruff format` Fulfills the Black Requirement

- Status: Accepted
- Date: 2026-07-15
- Deciders: Engineering
- Resolves: ARCHITECTURE_REVIEW.md C8

## Context

The operating prompt requires both Ruff and Black. Running two formatters
invites conflicting rewrites; `ruff format` is a Black-compatible formatter
already present in the toolchain.

## Decision

`ruff format --check` is the formatting gate in CI and pre-commit usage.
Black itself is not added as a dependency. `ruff check` remains the lint gate.

## Consequences

- (+) One tool, one configuration, Black-compatible output.
- (−) Rare divergences from Black's style are accepted as-is.
