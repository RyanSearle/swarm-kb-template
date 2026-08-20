#!/usr/bin/env python3
"""Regenerate the Obsidian graph colour-groups spec from kb/ structure.

Integrator-run, like scripts/build_indexes.py. One colour group per top-level
kb/ subtree so the graph view is readable (nodes coloured by area). Hues are
evenly spaced by sorted position for maximum separation. Output is a TRACKED
artifact, .obsidian/graph-colors.generated.json; scripts/apply_graph_colors.py
writes it into the (gitignored, user-owned) .obsidian/graph.json colorGroups on
the local vault. No dependencies.
"""
from __future__ import annotations
import colorsys, json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
KB = REPO / "kb"
OUT = REPO / ".obsidian" / "graph-colors.generated.json"

def rgb_int(h: float) -> int:
    r, g, b = colorsys.hsv_to_rgb(h, 0.70, 0.85)
    return (int(r * 255) << 16) | (int(g * 255) << 8) | int(b * 255)

def main() -> None:
    if not KB.is_dir():
        sys.exit("no kb/ directory")
    areas = sorted(p.name for p in KB.iterdir() if p.is_dir())
    n = len(areas) or 1
    groups = [
        {"query": f'path:"kb/{a}/"', "color": {"a": 1, "rgb": rgb_int(i / n)}}
        for i, a in enumerate(areas)
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(groups, indent=2) + "\n"
    if OUT.exists() and OUT.read_text(encoding="utf-8") == text:
        print(f"{OUT.name}: unchanged ({len(groups)} groups)")
        return
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT} ({len(groups)} groups)")

if __name__ == "__main__":
    main()
