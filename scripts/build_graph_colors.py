#!/usr/bin/env python3
"""Regenerate the Obsidian graph colour-groups spec from kb/ structure.

Integrator-run, like scripts/build_indexes.py. HIERARCHICAL colouring: the hue
wheel is split into one BAND per top-level kb/ area, and each area's subfolders
are assigned hues from within that band only -- so an area reads as one colour
family (all mechanics/* greens, all skills/* cyans, ...) while subfolders vary
by a light->dark ramp inside the family. Files directly under an area sit at the
band centre. The area catch-all query EXCLUDES its subfolders, so colouring is
unambiguous regardless of Obsidian's match-precedence. Output is a TRACKED
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
SAT = 0.70

def rgb_int(h: float, s: float, v: float) -> int:
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return (int(r * 255) << 16) | (int(g * 255) << 8) | int(b * 255)

def main() -> None:
    if not KB.is_dir():
        sys.exit("no kb/ directory")
    areas = sorted(p.name for p in KB.iterdir() if p.is_dir())
    n = len(areas) or 1
    band = 1.0 / n
    groups: list[dict] = []
    for i, area in enumerate(areas):
        subs = sorted(p.name for p in (KB / area).iterdir() if p.is_dir())
        start = i * band
        center = start + band / 2
        margin = 0.12 * band
        usable = band - 2 * margin
        m = len(subs)
        # subfolder groups first (specific); each a shade within the band
        for j, sub in enumerate(subs):
            t = (j + 0.5) / m
            hue = start + margin + t * usable
            val = 0.82 - 0.24 * t          # light -> dark ramp within the family
            groups.append({"query": f'path:"kb/{area}/{sub}/"',
                           "color": {"a": 1, "rgb": rgb_int(hue, SAT, val)}})
        # area catch-all: direct files only (exclude every subfolder), band centre
        q = f'path:"kb/{area}/"' + "".join(f' -path:"kb/{area}/{s}/"' for s in subs)
        groups.append({"query": q, "color": {"a": 1, "rgb": rgb_int(center, SAT, 0.85)}})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(groups, indent=2) + "\n"
    if OUT.exists() and OUT.read_text(encoding="utf-8") == text:
        print(f"{OUT.name}: unchanged ({len(groups)} groups)")
        return
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT} ({len(groups)} groups)")

if __name__ == "__main__":
    main()
