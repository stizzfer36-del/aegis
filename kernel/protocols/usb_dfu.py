from __future__ import annotations

from kernel.protocols._simple import SimpleProtocol


class Usb_dfuProtocol(SimpleProtocol):
    name = "usb_dfu"
    capabilities = ["usb_dfu"]
