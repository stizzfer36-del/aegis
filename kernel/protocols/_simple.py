from __future__ import annotations

from typing import Any, Dict, List, Optional

from kernel.protocols.base import BaseProtocol, Command, ProtocolError


class SimpleProtocol(BaseProtocol):
    capabilities: List[str] = []

    def connect(self, device_path: str, fingerprint: Dict[str, Any]) -> bool:
        self.device_path = device_path
        self.fingerprint = dict(fingerprint)
        def _attempt() -> bool:
            return bool(self.device_path)
        self.connected = self.retry(_attempt)
        self.record_outcome("connect", self.connected, {"device_path": device_path, "firmware": str(self.fingerprint.get("firmware_version", "unknown"))})
        return self.connected

    def disconnect(self) -> bool:
        was = self.connected
        self.connected = False
        self.record_outcome("disconnect", was, {"device_path": self.device_path})
        return was

    def send(self, command: Command, expect_response: bool) -> Optional[bytes]:
        if not self.connected:
            raise ProtocolError(self.name, command, b"", "not connected")
        resp = b"ok" if expect_response else None
        if expect_response:
            validated = self.validate_response(command, resp)
            self.record_outcome("send", True, {"firmware": str(self.fingerprint.get("firmware_version", "unknown"))})
            return validated
        self.record_outcome("send", True, {"firmware": str(self.fingerprint.get("firmware_version", "unknown"))})
        return None

    def verify_handshake(self) -> Dict[str, str]:
        if not self.connected:
            raise ProtocolError(self.name, "handshake", b"", "device offline")
        model = str(self.fingerprint.get("model", "unknown"))
        firmware = str(self.fingerprint.get("firmware_version", "unknown"))
        if model == "unknown" or firmware == "unknown":
            raise ProtocolError(self.name, "handshake", b"unknown", "missing handshake fields")
        result = {"status": "ok", "firmware": firmware, "model": model}
        self.record_outcome("handshake", True, result)
        return result

    def list_capabilities(self) -> List[str]:
        return list(self.capabilities)
