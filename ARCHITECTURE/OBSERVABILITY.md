# Observability

## Goal

AEGIS must be inspectable in motion.

## Primary views

- `aegis trace` — event timeline.
- `aegis map` — action-consequence map.
- `aegis wealth` — value output and attribution.
- `aegis memory` — memory writes, compression, and skill promotion.

## Required telemetry

- trace id
- actor
- route chosen
- tool usage
- policy decisions
- retries
- failures
- resume points
- memory writes
- artifact outputs

## Rule

If a failure cannot be reconstructed from the trace, observability is insufficient.
