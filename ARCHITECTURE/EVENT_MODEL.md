# Event Model

## Canonical event family

The core event family is built around `agent.action` and related system events.

## Required event types

- `human.intent`
- `agent.thinking`
- `agent.design`
- `agent.execute`
- `agent.map_consequence`
- `remember.candidate`
- `wealth.generated`
- `policy.decision`
- `system.recover`

## Required fields

Every event must include:

- `trace_id`
- `event_type`
- `ts`
- `agent`
- `intent_ref`
- `cost`
- `consequence_summary`
- `wealth_impact`
- `policy_state`

## Rules

- Events are append-only.
- Events must be structured JSON.
- Events may not contain raw secrets.
- Unmapped execution events are invalid.
- Failed events are preserved for recovery and audit.

## Minimal example

```json
{
  "trace_id": "tr_01",
  "event_type": "agent.execute",
  "ts": "2026-04-14T18:00:00Z",
  "agent": "forge",
  "intent_ref": "build landing page and deploy",
  "cost": {"tokens": 14123, "dollars": 0.00},
  "consequence_summary": "writes app files and deploy config",
  "wealth_impact": {"type": "projected", "value": 250},
  "policy_state": "approved"
}
```

## Validation behavior

Malformed events are dropped, logged, and escalated to Warden for structural review.
