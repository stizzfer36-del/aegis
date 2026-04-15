from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SatelliteBootstrap:
    deployed: bool = False

    def deploy(self) -> bool:
        self.deployed = True
        return True
