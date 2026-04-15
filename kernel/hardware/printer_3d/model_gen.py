from __future__ import annotations


def generate_scad(description: str) -> str:
    return f"// {description}\ncube([10,10,10]);\n"
