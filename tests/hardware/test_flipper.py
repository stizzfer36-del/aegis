from __future__ import annotations

import pytest

from kernel.hardware.flipper.driver import FlipperDriver
from kernel.hardware.flipper.rpc import decode_message, encode_message
from kernel.protocols.serial_cdc import Serial_cdcProtocol


class MockSerial(Serial_cdcProtocol):
    def send(self, command, expect_response: bool):
        if isinstance(command, bytes):
            decoded = decode_message(command)
            return encode_message(decoded["method"], {"ok": True})
        return b"ok"


def test_flipper_connect_mock() -> None:
    proto = MockSerial()
    assert proto.connect("/dev/ttyACM0", {"model": "flipper", "firmware_version": "1.1.0"})


def test_flipper_nfc_read_mock() -> None:
    proto = MockSerial()
    proto.connect("/dev/ttyACM0", {"model": "flipper", "firmware_version": "1.1.0"})
    driver = FlipperDriver(proto)
    out = driver.execute("nfc_read", {"target": "card"})
    assert out.ok


def test_flipper_firmware_mismatch() -> None:
    proto = MockSerial()
    proto.connect("/dev/ttyACM0", {"model": "flipper", "firmware_version": "0.1.0"})
    driver = FlipperDriver(proto)
    with pytest.raises(ValueError):
        driver.execute("nfc_read", {"target": "card"})


def test_flipper_rpc_encode_decode() -> None:
    msg = encode_message("nfc_read", {"slot": 1})
    parsed = decode_message(msg)
    assert parsed["method"] == "nfc_read"
    assert parsed["params"]["slot"] == 1
