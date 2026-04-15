from __future__ import annotations

from kernel.protocols._simple import SimpleProtocol


class MqttProtocol(SimpleProtocol):
    name = "mqtt"
    capabilities = ["mqtt"]
