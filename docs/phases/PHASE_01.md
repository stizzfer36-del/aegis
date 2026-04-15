# Phase 01 — Kernel Core

## Mission

Build the smallest enforceable kernel that every future agent can trust.

## Ships in this phase

- Event bus.
- Canonical event schema.
- Action-consequence mapper.
- Policy gate.
- Model router.
- Scheduler.
- Introspection commands.
- Recovery and failover rules.

## Banned in this phase

- Fancy UI.
- Non-core agents.
- Revenue expansion before trace quality.
- Broad interface work beyond basic terminal viability.

## Acceptance criteria

- Every event has a trace id and required fields.
- Every execution-capable action passes through policy and mapping.
- The kernel can recover from malformed events and agent crashes.
- `aegis map`, `aegis trace`, and `aegis wealth` are defined and usable.

## Proof demo

One terminal intent enters the kernel and produces a visible trace with routing, policy result, consequence mapping, memory candidates, and a recoverable outcome.
