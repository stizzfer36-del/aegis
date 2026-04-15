from __future__ import annotations

from kernel.protocols._simple import SimpleProtocol


class Ble_gattProtocol(SimpleProtocol):
    name = "ble_gatt"
    capabilities = ["ble_gatt"]
