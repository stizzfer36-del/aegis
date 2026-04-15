from __future__ import annotations

from kernel.protocols._simple import SimpleProtocol


class SdrProtocol(SimpleProtocol):
    name = "sdr"
    capabilities = ["sdr"]
