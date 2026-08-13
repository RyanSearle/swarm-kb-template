# PLANNER procedure — seeding, protocols, phases

Singleton (claim `planner`). One planning pass on a branch
(`plan/<agent-id>`), published through the integrator like any work.

## 0. Vitals, invariants & source health — before ingest (DESIGN.md Part F)

The planner is where autonomous remediation happens (it seeds tasks and writes
protocols/DECISIONS.md). Run this FIRST.

1. **Invariant guards (F4).** Recompute the scheduler's derived quantities from
   tasks/ + logs/ and assert their bounds. If a gate has been starved — e.g. more
   than {{SELF_AUDIT_EVERY:25}}+1 completed tasks since the last self-audit log, or
   the open-task count stuck at 0 across several planner logs while coverage is
   incomplete — FORCE the affected gate this pass (seed the overdue audit / gap
   batch) and append a one-line anomaly entry to protocols/DECISIONS.md. Self-
   correct on the first pass that observes the violation.
2. **Source health / vitals (F3).** For each source in DOMAIN.md §Primary sources,
   check reachability and that the fetch/search tool returns non-empty results. A
   source failing across {{SOURCE_DEAD_AFTER:3}} consecutive observations is auto-
   demoted (Tier B): record the demotion + the working fallback you adopted in
   protocols/DECISIONS.md and prefer work that does not depend on it. Do NOT block
   or wait — act on the safe default and log it. Escalate a Q only if NO usable
   source/tool remains for a required capability.

## 1. Ingest (idempotently — no timestamp watermarks)

1. **Directives**: for each Pending entry in protocols/DIRECTIVES.md — apply
   (seed/adjust tasks; DOMAIN.md-affecting ones: apply only if the owner wrote
   the change or explicitly authorized; else raise a Q), move to Acknowledged
   with `action_taken`. `priority: high` directives outrank everything below.
2. **Answers**: for EVERY task in tasks/ that is blocked-on or references a
   question id, check protocols/QUESTIONS.md `## Answered` DIRECTLY. If
   answered: unblock, append the answer into the task's `notes:`. This check
   is a set-comparison, not a "newer than last time" filter — it cannot
   permanently miss (lesson: the watermark bug).
3. **Proposals**: triage tasks/proposals/* into real tasks or a rejection note.
4. **Bounced**: re-open `refs/bounced` tasks with concrete merge instructions.

## 2. Event check (DOMAIN.md §Release/event triggers)

New release/patch/dataset since the last planner log? Derive tasks FROM ITS
CONTENT: named entities → one targeted update task each; family-wide changes
→ one task per affected kb/ subtree. Mark them `priority: event`. NEVER seed
re-validation for content the release doesn't touch.

## 3. Coverage diff (phase logic)

Diff DOMAIN.md §Definition-of-done against kb/ (+ index data):

- Gaps exist → **BUILD-OUT**: seed gap-fill batches (8-15 items per task,
  build/consumer-relevance ordered — valuable tail first; pilot an unproven
  doc shape with ~3-15 items before sweeping; keep open tasks ≤
  {{MAX_OPEN_TASKS:40}}).
- No gaps, no events → **MAINTENANCE**: seed ONE slow-rotation verification
  batch (≤10 docs, oldest `last_verified` first, `confidence: low` first).
  Never exit planning with an empty queue — that idles the machine.
- Either way: ensure the **capability self-audit** task recurs (one per
  {{SELF_AUDIT_EVERY:~25}} completed tasks, rotating variants per DOMAIN.md).
- **Granularity review (F2 — Tier A curator work).** Ensure a `granularity-review`
  task recurs, rotating by oldest `last_granularity_reviewed` (absent = never =
  first). It re-derives the right granularity for a topic from computable signals
  — a doc over the size cap ({{DOC_SIZE_CAP_BYTES:8000}} bytes), low internal
  cohesion, or inbound-link clustering implying a different cut — and may **split,
  merge, OR re-split differently**. It IGNORES whether the topic was split before:
  no prior structural decision is frozen (DESIGN.md F2). Anti-thrash: do not reverse
  a granularity change younger than {{GRANULARITY_COOLDOWN_RUNS:20}} runs unless the
  cohesion gain clears {{GRANULARITY_MIN_GAIN:0.2}}. Structure changes run through
  the F0 loop (propose -> integrator verify -> monitor MISSING stays 0 -> revert on
  regression).

## 4. Archive & bookkeep

Move `status: done` task files to tasks/done/ (append-only archive dir; keeps
the live queue listing small). Write `logs/<agent-id>.md` with: phase, tasks
seeded/archived/unblocked, directives processed, event determinations. State
is DERIVED (counts of files, log greps) — the template stores no counters.

## 5. Publish

Commit (single line), `scripts/ready.sh plan-<agent-id>`, release claim, exit.
