from __future__ import annotations

from kernel.protocols._simple import SimpleProtocol


class Can_busProtocol(SimpleProtocol):
    name = "can_bus"
    capabilities = ["can_bus"]
