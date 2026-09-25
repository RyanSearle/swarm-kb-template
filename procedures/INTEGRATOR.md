# INTEGRATOR procedure — the only writer to main

Singleton (claim `integrator`). One merge-queue pass, then exit.

## 1. The pass

For each `refs/ready/<ID>` (oldest first), on an up-to-date local main:

1. **Duplicate check** — task file on main already `done`? A reissued claim
   raced its original; FIRST merge won. Delete this ready ref + branch. Next.
2. `git merge --no-ff <ready-branch>`:
   - **Clean** → verify the branch's task file says ready/done and flip to
     `status: done` in the merge if the worker didn't; verify every new/changed
     kb/ doc has complete frontmatter (reject = bounce, don't fix silently
     unless trivial). Push main. Delete `refs/ready/<ID>`, `refs/claims/task-<ID>`,
     and the task branch.
   - **Conflict** → resolve yourself ONLY if it is semantically trivial
     (non-overlapping list/table additions, both-sides-appends). Anything
     judgement-shaped: `git merge --abort`, move the ref to
     `refs/bounced/<ID>`, append a note to the task file on main
     (`bounce_reason:`) in a tiny direct commit. The planner re-opens bounced
     tasks with instructions.
3. After all merges: if any kb/ docs changed, run
   `python3 scripts/build_indexes.py && python3 scripts/build_graph_colors.py`
   and include the regenerated indexes AND
   `.obsidian/graph-colors.generated.json` in a final commit. **Both are
   build artifacts — never hand-edited, never a merge conflict.** (The live
   `.obsidian/graph.json` is gitignored/user-owned; the tick applies its
   colorGroups locally.)

## 2. Exit

`scripts/claim.sh release integrator`. Push everything. Exit.

## Notes

- Serial, boring, fast — that is the point. All parallelism lives in workers.
- You may do a worker task afterwards ONLY if the queue was empty — never
  interleave integrating and working.
- Main must always be consistent: every commit on main leaves tasks/, kb/ and
  indexes agreeing with each other.

## Cloud PR lane (after the ready-queue pass)

Cloud-runner sessions (e.g. claude.ai/code routines) cannot push
coordination refs or task branches — their git proxy allows only the
session's own branch plus PR creation. They deliver completed tasks as PRs
titled `swarm-cloud: T#### <summary>` (see docs/cloud-runners.md). After
draining `refs/ready/*`:

1. List open PRs whose title starts with `swarm-cloud:` (`gh pr list
   --state open --json number,title,headRefName`; if `gh` is unavailable,
   skip this section and note that in your log).
2. For each, oldest first, treat the PR head EXACTLY like a ready branch:
   - Duplicate check: task already done on main → close the PR with a
     comment. Next.
   - Merge gate: identical to any ready branch (this instance's EXECUTE.md
     gate — run it; never merge red).
   - Clean + green → merge, flip the task to done if the worker couldn't,
     push main, close the PR as merged.
   - Gate red or judgement-shaped conflict → do NOT merge: comment
     `bounce: <reason>`, close the PR, and append `bounce_reason:` to the
     task file on main (tiny direct commit) so the planner re-opens it —
     the cloud session branch is dead once its session ends, so bounces
     live on main, not the PR.
3. Cloud workers cannot flip task status or write logs to main — do both at
   merge (the PR body carries the session log; copy it into
   logs/<agent-id>.md if present).
