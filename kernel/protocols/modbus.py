from __future__ import annotations

from kernel.protocols._simple import SimpleProtocol


class ModbusProtocol(SimpleProtocol):
    name = "modbus"
    capabilities = ["modbus"]
