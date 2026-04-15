from __future__ import annotations

from pathlib import Path
from typing import Dict


class CADDesigner:
    def generate_enclosure(self, dimensions: Dict[str, float], out_dir: Path) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "enclosure.scad"
        path.write_text(f"cube([{dimensions.get('x',10)},{dimensions.get('y',10)},{dimensions.get('z',10)}]);\n", encoding="utf-8")
        return path

    def export_stl(self, out_dir: Path) -> Path:
        path = out_dir / "enclosure.stl"
        path.write_text("solid enclosure\nendsolid enclosure\n", encoding="utf-8")
        return path
