from __future__ import annotations

from kernel.protocols._simple import SimpleProtocol


class AdbProtocol(SimpleProtocol):
    name = "adb"
    capabilities = ["adb"]
