from __future__ import annotations

from pathlib import Path


class PCBDesigner:
    def generate_schematic(self, description: str, out_dir: Path) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "design.kicad_sch"
        path.write_text(f"# schematic\n# {description}\n", encoding="utf-8")
        return path

    def generate_pcb_layout(self, out_dir: Path) -> Path:
        path = out_dir / "design.kicad_pcb"
        path.write_text("(kicad_pcb (version 202311))\n", encoding="utf-8")
        return path

    def run_drc(self) -> dict[str, str]:
        return {"status": "ok"}

    def export_gerber(self, out_dir: Path) -> Path:
        path = out_dir / "gerber.zip"
        path.write_bytes(b"GERBER")
        return path

    def export_bom(self, out_dir: Path) -> Path:
        path = out_dir / "bom.csv"
        path.write_text("ref,part\nR1,10k\n", encoding="utf-8")
        return path
