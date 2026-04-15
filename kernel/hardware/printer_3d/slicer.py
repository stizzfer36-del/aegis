from __future__ import annotations

from pathlib import Path


def render_gcode(scad_path: Path, out_path: Path) -> Path:
    out_path.write_text(f"; generated from {scad_path.name}\nG28\n", encoding="utf-8")
    return out_path
