#!/usr/bin/env python3
"""Apply the swarm-maintained colour spec to the LOCAL Obsidian graph.

.obsidian/graph.json is gitignored (Obsidian rewrites its camera/zoom state
constantly), so the swarm can't commit it. The integrator instead commits
.obsidian/graph-colors.generated.json; this script -- run locally by
bin/swarm-tick.sh after each pull -- copies ONLY the colorGroups key into the
live graph.json, preserving every other (user-owned) setting. Idempotent;
no-ops if either file is absent (e.g. cloud runners / template with no vault).
"""
from __future__ import annotations
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SPEC = REPO / ".obsidian" / "graph-colors.generated.json"
GRAPH = REPO / ".obsidian" / "graph.json"

def main() -> None:
    if not SPEC.exists() or not GRAPH.exists():
        return  # no spec or no vault -> nothing to do
    groups = json.loads(SPEC.read_text(encoding="utf-8"))
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    if graph.get("colorGroups") == groups:
        return  # already applied
    graph["colorGroups"] = groups
    GRAPH.write_text(json.dumps(graph, indent=2) + "\n", encoding="utf-8")
    print(f"applied {len(groups)} colour groups to {GRAPH}")

if __name__ == "__main__":
    main()
