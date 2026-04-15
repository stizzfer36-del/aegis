from __future__ import annotations

import pytest

from kernel.protocols.base import ProtocolError
from kernel.protocols.serial_cdc import Serial_cdcProtocol


def test_serial_cdc_mock(tmp_path) -> None:
    proto = Serial_cdcProtocol()
    assert proto.connect("/dev/ttyACM0", {"model": "flipper", "firmware_version": "1.0.0"})
    assert proto.send("info", expect_response=True) == b"ok"


def test_serial_response_validation() -> None:
    proto = Serial_cdcProtocol()
    proto.connect("/dev/x", {"model": "m", "firmware_version": "1"})
    with pytest.raises(ProtocolError):
        proto.validate_response("x", b"")


def test_retry_logic() -> None:
    proto = Serial_cdcProtocol()
    state = {"n": 0}
    def fail_then_ok() -> bool:
        state["n"] += 1
        return state["n"] == 3
    assert proto.retry(fail_then_ok)


def test_firmware_version_check() -> None:
    proto = Serial_cdcProtocol()
    proto.connect("/dev/x", {"model": "m", "firmware_version": "2.0.0"})
    hs = proto.verify_handshake()
    assert hs["firmware"] == "2.0.0"
