# WORKER procedure

One task per session: claim → isolate → execute → publish → exit.

## 1. Pick and claim

1. List `tasks/*.md` with `status: open`; order by `priority:` field
   (event > gap-fill > maintenance), then by id.
2. For your pick: `scripts/claim.sh try task-<ID>`. Lost the race? Take the
   next task. Nothing claimable → exit cleanly.
3. Reap while you're here: `scripts/claim.sh reap` (deletes claims older than
   TTL — a dead agent's abandoned claims; costs you nothing).

## 2. Isolate

`git checkout -b task/<ID>-<agent-id> origin/main`

Everything you do lives on this branch: content, your task-file status flips,
your session log. If you die, the branch dies unmerged — by design.

## 3. Execute (per the task file — it is self-contained)

1. Set the task file's `status: in_progress`, add `claimed_by: <agent-id>`.
2. Do the work per its `dod:` using its `source_hints:`, honouring
   protocols/CONVENTIONS.md (frontmatter schema, citable-layer rules, dataset
   precedence, negative-result pages). For registered `kind: api` sources,
   QUERY them per **Querying API sources** (below) — do not read them.
3. Sub-agents: dispatch freely for parallel fetch/write within your task; you
   are the orchestrator of your own branch.
4. Discoveries out of scope? Do NOT expand your task. Append a proposal file
   `tasks/proposals/<agent-id>-<slug>.md` (planner triages these). Conflicts or
   owner-questions: draft the Q in your log; the planner lifts it to
   protocols/QUESTIONS.md.
5. Set `status: ready`, `completed_at:`, and a 1-3 line `actual_shape:` note in
   the task file. Write your session log to `logs/<agent-id>.md`. Commit
   (single line, ≤200 chars).

## 4. Publish and exit

1. `scripts/ready.sh <ID>` — pushes your branch and `refs/ready/<ID>`.
2. `scripts/claim.sh release task-<ID>`.
3. Exit. Do not merge, do not touch main, do not start another task.

## Querying API sources

Some registered sources are `kind: api` (DOMAIN.md source table +
kb/meta/sources-guide.md; concept in docs/design/queryable-sources.md) — you
QUERY them, you don't read them. Use them for computed / spatial / structured
answers a text source can't give (e.g. passive-tree distances, adjacency,
allocation).

- **Call it per its registry contract** — for transport `http`, curl the
  documented endpoints (you have shell in your clone).
- **A connection failure is a DEAD source, not a retry loop** — note it, fall
  back to the source's stated alternative (usually its backing dataset), never
  fabricate. If the registry marks a source local-only and nothing answers from
  your clone, treat it unavailable and use the backing data; do not block.
- **Cite by SNAPSHOT** — record `source_id` + the exact request + the value
  quoted + the version anchor + the UTC timestamp (same verbatim discipline as a
  web fetch). Never cite "the API" in the abstract.

## Budget

Soft budget {{TASK_TOKEN_BUDGET:~40k tokens}} per task; hard stop at 2×: set
`status: open` again, note `too_large: split needed` in the task file, push
ready anyway (the planner will split it). Keep tasks completable well inside
one session — the discard-on-failure model depends on it.
