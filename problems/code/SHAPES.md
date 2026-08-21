# SHAPES — code pack task types & artifact conventions

Engine task-file schema (frontmatter, one file per task, tasks/done/ archive,
proposals dir) is unchanged from `procedures/TASK_SHAPES.md`. This file
replaces its KB artifact half for code instances.

## Task types

| type | unit of work |
|---|---|
| `harness` | build/extend the verification harness itself (runner, smoke tests, fixtures, determinism fixes). T0001 is always a harness task if the canonical verify command doesn't exist yet. |
| `fix` | close one defect. Ships the regression test WITH the fix. |
| `feature` | add one capability. Ships the tests that specify it. |
| `refactor` | behaviour-preserving restructure. Proof = suite green before AND after; goes through the F0 loop (propose → verify → apply → monitor → revert). |
| `verify` | reproduce/characterise a reported behaviour; output = a committed (possibly failing-and-skipped) test + a task note, not a fix. |
| `granularity-review` | re-cut the backlog: split too-large items, merge trivial ones, re-derive proofs. Same F2 rules as the kb pack. |
| `self-audit` / `bootstrap` | as in the engine. |

`priority:` vocabulary is the engine's: `event` (regression, red main,
upstream break) > `gap-fill` (backlog) > `maintenance` (refactor/debt).

## Proof-of-done convention (the load-bearing rule)

Every `dod:` MUST end with a `proof:` line naming the mechanical check:

    proof: `<canonical-verify-cmd>` exits 0 AND tests/<new-or-named-test> passes

A worker may not set `status: ready` without having RUN the proof in their
clone. A dod whose proof can't be stated is a planner bug — reshape (usually
via a `verify` or `harness` task) before seeding the fix.

## Artifact conventions

- **Every fix ships its test** — the failing repro committed as a regression
  test (the code analogue of the KB's negative-result page). A `fix` diff
  with no test does not merge.
- **Match the codebase** — style, naming, comment density of surrounding
  code. No drive-by refactors inside `fix`/`feature` tasks; propose instead
  (tasks/proposals/).
- **Small diffs win** — same discard-on-failure economics as docs: a task's
  diff should be cheap to bounce. Over the token budget → `too_large: split
  needed`, back to open.
- **Session log** (`logs/<agent-id>.md`) records: proof command output
  (tail), behaviours OBSERVED vs assumed (snapshot-cite live-service
  observations), anything skipped.
- **Never weaken the gate to pass it** — deleting/skipping a failing test,
  loosening an assertion, or marking done on an unrun proof is fabrication
  (CONVENTIONS: never fabricate to hide a failed vital). A legitimately wrong
  test is its own `fix` task with the reasoning logged.
