from __future__ import annotations

from pathlib import Path


class FirmwareDesigner:
    def generate_sketch(self, target_chip: str, source: str, out_dir: Path) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{target_chip}.ino"
        path.write_text(source, encoding="utf-8")
        return path

    def compile_firmware(self, source_path: Path) -> Path:
        out = source_path.with_suffix(".bin")
        out.write_bytes(b"FW")
        return out

    def flash_firmware(self, binary_path: Path, device_path: str) -> bool:
        return binary_path.exists() and bool(device_path)
