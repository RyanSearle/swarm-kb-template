# TASK_SHAPES — schemas and conventions

## Task file (tasks/T<NNNN>-<slug>.md)

```markdown
---
id: T0042
title: <one line>
status: open | in_progress | ready | done | blocked
priority: event | gap-fill | maintenance
type: create | update | verify | split | granularity-review | self-audit | bootstrap
claimed_by: <agent-id, when claimed>
blocked_on: <Q-id, if blocked>
created_by: <agent-id>
created_at: <ISO>
completed_at: <ISO>
---

## dod
<definition of done — explicit, self-contained; a worker with NO other
context must be able to execute from this file alone>

## source_hints
<urls / data/ paths / kb docs to read; fetch quirks from DOMAIN.md>

## notes
<answers appended by planner; actual_shape / bounce_reason appended later>
```

Rules: one file per task; only the claiming worker (or planner/integrator per
their procedures) edits it; never delete — done tasks move to tasks/done/.
Batch tasks (8-15 items) over per-item tasks. ids sequential; planner assigns.

## KB doc frontmatter (kb/**/*.md — all fields mandatory)

```yaml
---
topic: <path/under/kb>
title: <human readable>
volatility: stable | volatile | ephemeral   # descriptive only — not a scheduler
last_verified: <date>                        # provenance, not a scheduler
sources:
  - url: <url or data/ path>
    tier: <tier per DOMAIN.md>
    confidence: high | medium | low
    accessed: <date>
confidence: high | medium | low
related: [<topic>, ...]
last_granularity_reviewed: <date>            # optional; structure cursor (F2), NOT freshness
---
```

## Doc conventions

- One topic per file; self-contained body; plain facts; inline-cite the
  non-obvious. No index editing — indexes are generated (scripts/build_indexes.py).
- **Size cap = granularity trigger, not an error.** A doc exceeding
  {{DOC_SIZE_CAP_BYTES:8000}} bytes is a signal to run a `granularity-review`
  (split into per-subconcept nodes; the original becomes a generated index) — see
  procedures/PLANNER.md §3 and DESIGN.md F2. "One topic per file" is maintained by
  re-derivation, never frozen once.
- **Negative-result pages**: a verify task confirming ABSENCE writes the
  absence as a doc (what was checked, sources, naming traps) — protects LLM
  readers from re-deriving it.
- **Pilot → sweep**: never mass-produce an unproven doc shape.
- Heuristics-layer docs: heuristic statement → mechanical basis (cross-ref,
  don't duplicate) → applicability limits → confidence. Community tier may be
  PRIMARY here only.
