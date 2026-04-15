from __future__ import annotations

from kernel.protocols._simple import SimpleProtocol


class Usb_hidProtocol(SimpleProtocol):
    name = "usb_hid"
    capabilities = ["usb_hid"]
