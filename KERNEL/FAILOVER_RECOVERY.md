# Failover and Recovery

## Required failure handling

- malformed events are dropped and logged
- crashed agents are restarted from last mapped state
- unavailable memory triggers fallback mode
- unsafe actions fail closed

## Principle

The map survives even when execution does not.
