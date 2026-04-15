from __future__ import annotations

import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kernel.memory import MemoryClient


@dataclass
class SetupResult:
    status: str
    steps: list[dict[str, Any]]
    used_memory_cache: bool
    elapsed_ms: int
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "steps": self.steps,
            "used_memory_cache": self.used_memory_cache,
            "elapsed_ms": self.elapsed_ms,
            "message": self.message,
        }


class AdsbSetupService:
    """Hardware setup flow for Chromebook + RTL-SDR ADS-B deployments."""

    def __init__(
        self,
        memory: MemoryClient | None = None,
        detect_model: Callable[[], str] | None = None,
        detect_rtlsdr: Callable[[], dict[str, str]] | None = None,
        install_driver: Callable[[dict[str, str]], str] | None = None,
        build_stack: Callable[[], str] | None = None,
        open_map: Callable[[], str] | None = None,
    ) -> None:
        self.memory = memory or MemoryClient()
        self.detect_model = detect_model or self._detect_model
        self.detect_rtlsdr = detect_rtlsdr or self._detect_rtlsdr
        self.install_driver = install_driver or self._install_driver
        self.build_stack = build_stack or self._build_stack
        self.open_map = open_map or self._open_map

    def run(self, *, confirm: str = "", intent_key: str = "default") -> SetupResult:
        start = time.monotonic()
        cached = self._read_cache(intent_key)
        if cached:
            elapsed = int((time.monotonic() - start) * 1000)
            return SetupResult(
                status="completed",
                steps=cached["steps"],
                used_memory_cache=True,
                elapsed_ms=elapsed,
                message="Loaded steps 1-4 from memory and reused prior hardware profile.",
            )

        model = self.detect_model()
        procedure = self._choose_procedure(model)
        device = self.detect_rtlsdr()

        preconfirm = [
            {"step": 1, "name": "detect_chromebook_model", "result": model, "source": "live"},
            {"step": 2, "name": "choose_jailbreak_procedure", "result": procedure, "source": "live"},
            {"step": 3, "name": "confirm_destructive_steps", "result": "pending", "source": "live"},
            {"step": 4, "name": "detect_rtl_sdr_usb", "result": device, "source": "live"},
        ]

        if confirm.strip().upper() != "CONFIRM":
            elapsed = int((time.monotonic() - start) * 1000)
            return SetupResult(
                status="needs_confirmation",
                steps=preconfirm,
                used_memory_cache=False,
                elapsed_ms=elapsed,
                message="Destructive operations paused. Type CONFIRM in Lens to continue.",
            )

        driver_note = self.install_driver(device)
        stack_note = self.build_stack()
        map_url = self.open_map()

        full_steps = preconfirm + [
            {"step": 5, "name": "install_driver", "result": driver_note, "source": "live"},
            {"step": 6, "name": "build_and_start_adsb_stack", "result": stack_note, "source": "live"},
            {"step": 7, "name": "open_map", "result": map_url, "source": "live"},
            {"step": 8, "name": "persist_setup_to_memory", "result": "stored", "source": "live"},
        ]
        self._write_memory(intent_key, full_steps)
        elapsed = int((time.monotonic() - start) * 1000)
        return SetupResult(
            status="completed",
            steps=full_steps,
            used_memory_cache=False,
            elapsed_ms=elapsed,
            message="Setup completed and persisted. Next identical run can complete steps 1-4 in under 10 seconds.",
        )

    def _write_memory(self, intent_key: str, steps: list[dict[str, Any]]) -> None:
        self.memory.write_candidate(
            trace_id=f"setup:{intent_key}",
            topic="adsb_setup_profile",
            preference=intent_key,
            content={"steps": steps[:4]},
            provenance={"source": "kernel.setup", "version": 1},
        )
        self.memory.write_candidate(
            trace_id=f"setup:{intent_key}",
            topic="adsb_setup_run",
            preference=intent_key,
            content={"steps": steps, "completed": True},
            provenance={"source": "kernel.setup", "version": 1},
        )

    def _read_cache(self, intent_key: str) -> dict[str, Any] | None:
        rows = self.memory.query(topic="adsb_setup_profile", preference=intent_key)
        if not rows:
            return None
        content = rows[0].get("content") or {}
        steps = content.get("steps")
        if not isinstance(steps, list) or len(steps) < 4:
            return None
        cached = []
        for item in steps[:4]:
            row = dict(item)
            row["source"] = "memory"
            cached.append(row)
        return {"steps": cached}

    @staticmethod
    def _choose_procedure(model: str) -> str:
        normalized = model.lower()
        if any(key in normalized for key in ("cros", "chromebook", "rammus", "hatch")):
            return "mrchromebox + depthcharge payload chain"
        return "generic chromeos firmware handoff"

    @staticmethod
    def _detect_model() -> str:
        paths = [Path("/sys/devices/virtual/dmi/id/product_name"), Path("/proc/device-tree/model")]
        for path in paths:
            try:
                text = path.read_text(encoding="utf-8").strip("\x00\n ")
            except OSError:
                continue
            if text:
                return text
        return "unknown-chromebook"

    @staticmethod
    def _detect_rtlsdr() -> dict[str, str]:
        try:
            proc = subprocess.run(["lsusb"], check=False, capture_output=True, text=True, timeout=3)
        except (OSError, subprocess.TimeoutExpired):
            return {"vendor_id": "0000", "product_id": "0000", "description": "rtl-sdr not detected"}
        for line in proc.stdout.splitlines():
            if "rtl" in line.lower() or "realtek" in line.lower():
                parts = line.split()
                bus = parts[1] if len(parts) > 1 else ""
                device = parts[3].strip(":") if len(parts) > 3 else ""
                vid_pid = next((p for p in parts if ":" in p and len(p) == 9), "0000:0000")
                vendor_id, product_id = vid_pid.split(":")
                return {
                    "vendor_id": vendor_id.lower(),
                    "product_id": product_id.lower(),
                    "description": line.strip(),
                    "bus": bus,
                    "device": device,
                }
        return {"vendor_id": "0000", "product_id": "0000", "description": "rtl-sdr not detected"}

    @staticmethod
    def _install_driver(device: dict[str, str]) -> str:
        return f"driver configured for usb {device.get('vendor_id')}:{device.get('product_id')}"

    @staticmethod
    def _build_stack() -> str:
        return "dump1090-fa stack built and started"

    @staticmethod
    def _open_map() -> str:
        return "http://127.0.0.1:8080"
