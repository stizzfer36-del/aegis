from __future__ import annotations

from kernel.protocols._simple import SimpleProtocol


class Http_deviceProtocol(SimpleProtocol):
    name = "http_device"
    capabilities = ["http_device"]
