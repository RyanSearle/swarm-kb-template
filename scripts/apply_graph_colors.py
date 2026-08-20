#!/usr/bin/env python3
"""Apply the swarm-maintained graph view settings to the LOCAL Obsidian graph.

.obsidian/graph.json is gitignored (Obsidian rewrites its camera/zoom state --
and, on any graph-settings edit, the WHOLE file, clobbering colorGroups and the
search filter). So the swarm can't commit it. The integrator instead commits
.obsidian/graph-colors.generated.json; this script -- run locally by
bin/swarm-tick.sh after each pull -- enforces the swarm-owned view settings into
the live graph.json, preserving every OTHER (user-owned) setting:
  * colorGroups  <- the generated spec (colour nodes by kb/ area)
  * search       <- DESIRED_SEARCH (hide the index.generated.md hub nodes)
so an accidental deletion or an Obsidian rewrite self-heals on the next tick.
Idempotent; no-ops if either file is absent (e.g. cloud runners / template).

NOTE: because `search` is enforced, an ad-hoc graph search typed into the view
is reverted on the next tick. Change DESIRED_SEARCH (or set it to "") to opt out.
"""
from __future__ import annotations
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SPEC = REPO / ".obsidian" / "graph-colors.generated.json"
GRAPH = REPO / ".obsidian" / "graph.json"
DESIRED_SEARCH = "-path:index.generated"   # hide section index.generated.md hubs

def main() -> None:
    if not SPEC.exists() or not GRAPH.exists():
        return  # no spec or no vault -> nothing to do
    groups = json.loads(SPEC.read_text(encoding="utf-8"))
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    changed = False
    if graph.get("colorGroups") != groups:
        graph["colorGroups"] = groups
        changed = True
    if graph.get("search") != DESIRED_SEARCH:
        graph["search"] = DESIRED_SEARCH
        changed = True
    if not changed:
        return  # already in sync
    GRAPH.write_text(json.dumps(graph, indent=2) + "\n", encoding="utf-8")
    print(f"synced graph view settings ({len(groups)} colour groups, search={DESIRED_SEARCH!r})")

if __name__ == "__main__":
    main()
