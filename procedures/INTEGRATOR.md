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
