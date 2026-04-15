from __future__ import annotations

from kernel.protocols._simple import SimpleProtocol


class GpioProtocol(SimpleProtocol):
    name = "gpio"
    capabilities = ["gpio"]
