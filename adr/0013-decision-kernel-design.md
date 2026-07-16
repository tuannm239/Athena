# ADR-0013 — Decision Kernel Design

- Status: Accepted (Engineering Authorization)
- Date: 2026-07-16
- Deciders: Engineering (authorized design authority)

## Problem

SPEC-04 defines the kernel's pipeline, business rules and output but not its
composition; its §Extension Points reference a Plugin SDK (RFC-0021) that
does not exist yet. RFC-0020 fixes the compiled Decision Object shape.

## Alternatives considered

1. Wait for RFC-0021 — rejected: authorization directs implementation now.
2. A plugin loader invented ahead of RFC-0021 — rejected: would prejudge the
   SDK's semantics.
3. **Constructor-injected engine functions behind kernel-owned Protocols**
   (hexagonal ports), platform engines as defaults — chosen: the seam where
   RFC-0021 plugins will later plug in, with zero core modification.

## Chosen solution

- The kernel lives in `decision_kernel.application.kernel` (orchestration is
  application-layer work; the aggregate's invariants stay in the domain).
- Ports: probability evaluation, DSL graph execution, risk assessment and
  position sizing are injected callables typed by kernel Protocols; defaults
  bind the platform engines (RFC-0026 probability, RFC-0027 risk/sizing,
  RFC-0020 evaluator).
- Execution semantics: DSL adjustments apply on top of the Bayesian
  posterior/confidence (base values), per RFC-0020's pipeline order
  (Probability Engine before graph-adjusted Decision Object); total expected
  utility = RFC-0026 EU at the final probability + DSL UTILITY adjustments.
- The kernel is deterministic and pure — its only inputs are the aggregate,
  the compiled ruleset, the fact context, an `as_of` instant and explicit
  sizing/risk parameters. No I/O, no LLM import path (ADR-0003; enforced by
  test).
- Explanation is structured per SPEC-04 §Explainability: why, why not,
  assumptions, missing information, key risks, alternative scenarios — every
  claim traceable to evidence items, rules or engine outputs.

## Consequences

- (+) Sprint 12 ships without prejudging RFC-0021; plugins later implement
  the same Protocols.
- (+) Every stage independently replaceable and testable.
- (−) Plugin discovery/packaging remains open until RFC-0021.
