from __future__ import annotations

import time
from typing import Dict, List


def hid_list() -> Dict[str, List[Dict[str, str]]]:
    try:
        import hid
    except ImportError as exc:
        raise ImportError("hidapi not installed — pip install hidapi") from exc
    devices = []
    for d in hid.enumerate():
        devices.append(
            {
                "vendor_id": str(d.get("vendor_id")),
                "product_id": str(d.get("product_id")),
                "manufacturer": str(d.get("manufacturer_string") or ""),
                "product": str(d.get("product_string") or ""),
                "serial_number": str(d.get("serial_number") or ""),
            }
        )
    return {"devices": devices}


def serial_list() -> Dict[str, List[Dict[str, str]]]:
    try:
        from serial.tools import list_ports
    except ImportError as exc:
        raise ImportError("pyserial not installed — pip install pyserial") from exc
    ports = []
    for p in list_ports.comports():
        ports.append({"port": p.device, "description": p.description, "hwid": p.hwid})
    return {"ports": ports}


def serial_send(port: str, baud: int, message: str, timeout: float = 2.0) -> Dict[str, str]:
    try:
        import serial
    except ImportError as exc:
        raise ImportError("pyserial not installed — pip install pyserial") from exc
    with serial.Serial(port=port, baudrate=baud, timeout=timeout) as ser:
        ser.write(message.encode("utf-8"))
        data = ser.read(4096)
    return {"response": data.decode("utf-8", errors="replace")}


def serial_listen(port: str, baud: int, duration: float = 5.0) -> Dict[str, str]:
    try:
        import serial
    except ImportError as exc:
        raise ImportError("pyserial not installed — pip install pyserial") from exc
    chunks: List[bytes] = []
    deadline = time.time() + duration
    with serial.Serial(port=port, baudrate=baud, timeout=0.25) as ser:
        while time.time() < deadline:
            part = ser.read(4096)
            if part:
                chunks.append(part)
    return {"output": b"".join(chunks).decode("utf-8", errors="replace")}
