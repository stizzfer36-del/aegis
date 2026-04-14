# Bus Spec

The bus transports structured events across the system.

## Requirements

- append-only event flow
- trace id continuity
- replay support
- low-cost local operation
- recovery-friendly logging

## Ban

No unstructured chatter on the bus.
