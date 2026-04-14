# Scheduler Spec

The scheduler decides when standing agents wake, sleep, retry, compress memory, and resume interrupted work.

## Core behaviors

- wake on event class
- queue by priority
- prevent duplicate execution
- defer low-value work
- preserve resume points
