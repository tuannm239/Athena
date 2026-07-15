# ADR-0010 — Interim In-Process Event Bus

- Status: Accepted (interim — supersedable by RFC-0022 when it arrives)
- Date: 2026-07-15
- Deciders: Engineering
- Resolves: RFC-0022 gap (C1) for the application layer

## Context

Aggregates collect immutable domain events (`pull_events()`), and SPEC-03
requires events to be published through the application layer — but RFC-0022
(Event Model) does not exist in the repository.

## Decision

A minimal synchronous in-process bus: application services drain aggregate
events and hand them to an `EventPublisher` port (shared kernel); the
infrastructure implementation dispatches synchronously to registered
subscribers within the monolith (ADR-0001). No delivery guarantees beyond
in-process synchrony are promised until RFC-0022 specifies them.

## Consequences

- (+) Event flow is architecturally correct today; swapping the dispatcher
  later touches one adapter.
- (−) No async/durable delivery until RFC-0022 lands.
