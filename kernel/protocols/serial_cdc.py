from __future__ import annotations

from kernel.protocols._simple import SimpleProtocol


class Serial_cdcProtocol(SimpleProtocol):
    name = "serial_cdc"
    capabilities = ["serial_cdc"]
