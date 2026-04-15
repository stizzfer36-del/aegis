from __future__ import annotations

from kernel.hardware.base import BaseDriver
from kernel.protocols.ssh import SshProtocol


class RaspberryPiDriver(BaseDriver):
    name = "raspberry_pi"
    capabilities = ["shell_exec", "gpio_control", "i2c_scan", "spi_scan", "service_install", "docker_deploy", "sensor_read"]

    def __init__(self, protocol: SshProtocol) -> None:
        super().__init__(protocol)
