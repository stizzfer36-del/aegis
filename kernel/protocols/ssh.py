from __future__ import annotations

from kernel.protocols._simple import SimpleProtocol


class SshProtocol(SimpleProtocol):
    name = "ssh"
    capabilities = ["ssh"]
