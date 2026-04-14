# Kernel

## Purpose

The kernel is the smallest enforceable runtime AEGIS depends on.

## Owns

- event bus
- memory client
- policy gate
- model router
- scheduler
- introspection
- consequence mapping hooks
- recovery primitives

## Does not own

- agent personalities
- interface branding
- prestige features
- business logic that belongs to specific agents

## Success criteria

- can normalize intent,
- route work,
- gate actions,
- emit valid events,
- recover from interruption,
- and expose the full trace cleanly.

## Required docs

- `BUS_SPEC.md`
- `ROUTER_SPEC.md`
- `SCHEDULER_SPEC.md`
- `POLICY_GATE_SPEC.md`
- `MEMORY_CLIENT_SPEC.md`
- `INTROSPECTION_SPEC.md`
- `FAILOVER_RECOVERY.md`
