# Problem packs — one engine, many problem types

Status: PROPOSED (draft PR) · Date: 2026-08-21 · Owner: Ryan Searle

## Motivation

The engine — git-as-coordination-plane (claims-as-refs, branch-per-task,
serial integrator, discard-on-failure), role election, the F0 autonomy loop,
protocols (DIRECTIVES/QUESTIONS/DECISIONS), the launch layer — is already
problem-agnostic. What is knowledge-base-specific is narrower than it looks:

1. **The completion model** — what "done" means and how it is verified
   (KB: coverage of enumerated atoms, link-integrity, source-health;
   code: named tests green, build clean).
2. **The artifact vocabulary** — what a unit of work produces and its
   conventions (KB: a frontmattered doc under `kb/`; code: a change + the
   test that proves it).
3. **The spec skeleton** — the sections `DOMAIN.md` needs so the planner can
   diff reality against a definition-of-done.

Everything else (WORKER's claim→isolate→execute→publish loop, PLANNER's
ingest/event/coverage passes, INTEGRATOR's gate) survives a problem-type swap
untouched. So: package those three things as a **problem pack** and the same
swarm can attack programming problems, not just KBs.

Naming: **problem pack** (`problems/<name>/`). Alternatives considered:
"problem template" (collides with the repo being a GitHub *template*),
"domain pack" (collides with `DOMAIN.md`, which is the *instance* spec, not
the problem *type*). Rename is cheap if a better word appears.

## The seam

A pack is a directory `problems/<name>/` containing exactly:

| File | Replaces / overlays | Defines |
|---|---|---|
| `DOMAIN.md` | root `DOMAIN.md` skeleton | the spec sections the planner plans against for this problem type |
| `SHAPES.md` | artifact half of `procedures/TASK_SHAPES.md` | task types + artifact schema + proof-of-done convention |
| `EXECUTE.md` | referenced by `procedures/WORKER.md` §3 | how a worker executes + self-verifies one unit; the integrator's merge gate |

The task-file schema itself (frontmatter, one-file-per-task, tasks/done/
archive) is engine, not pack — every pack uses it; packs add task **types**
and the proof-of-done convention for `dod:`.

**Instantiation** becomes: take the template → pick a pack → copy the pack's
three files over the seam (pack `DOMAIN.md` → root `DOMAIN.md`, etc.) → fill
the spec → launch. `docs/INSTANTIATE.md` gains a step 0.

**Engine hooks** (the only engine edits this design needs):
- `WORKER.md` §3 executes "per the pack's EXECUTE.md" instead of inlining
  KB doc conventions.
- `INTEGRATOR.md` runs "the pack's merge gate" (kb: link-check + index
  regen; code: build + test suite on the merge candidate; red = bounce).
- `PLANNER.md` §3's coverage diff reads "diff the definition-of-done against
  the artifact space the pack defines" (kb/ tree vs. backlog-with-proofs).

## Completion models compared

| | kb pack | code pack |
|---|---|---|
| done (task) | doc(s) exist, frontmatter valid, cited | named test(s) green + build clean |
| done (instance) | DoD coverage targets met, self-audit passes | DoD backlog empty, full suite green, self-audit passes |
| verify gate (integrator) | `sync_links --check`, index regen | ONE canonical verify command (build + full suite) |
| artifact | `kb/**.md` node + `related:` edges | code change + its test + session log |
| negative result | absence page | regression test pinning the bug |
| granularity review | split/merge docs by size/cohesion | split tasks; refactor proposals via F0 |
| fabrication guard | never assert unverified magnitudes | never mark done on an unrun test |

## The code pack (problems/code/)

Principles, from the owner's framing (2026-08-21):

1. **Self-testable by construction.** Every task's `dod:` names the command(s)
   and expected result that PROVE completion — "proof: `<verify-cmd>` green
   AND new test <path> passes". A task whose done-ness can't be mechanically
   checked is not seedable; the planner reshapes it until it is.
2. **The verification harness is itself agent-built.** The instance's
   `DOMAIN.md` names ONE canonical verify command (e.g. `scripts/verify.sh`).
   If it doesn't exist yet, the bootstrap task (T0001, type `harness`) builds
   it: test runner + smoke tests, runnable in a fresh throwaway clone with no
   attended setup. Harness gaps discovered later are `harness` tasks, seeded
   like any other gap.
3. **Every fix ships its test.** The failing repro becomes a committed
   regression test before (or with) the fix — the code pack's analogue of the
   KB's negative-result page. First merge wins; a duplicate fix without a
   better test is discarded.
4. **The integrator is the wall.** The merge gate runs the canonical verify
   command on the merge candidate; any red = bounce with the failure pasted
   into the bounce note. Workers self-verify first, but only the gate's run
   counts.
5. **No drive-by scope.** Out-of-scope discoveries (design smells, missing
   features) go to `tasks/proposals/` exactly as in the kb pack — the planner
   triages; workers never expand their diff.

External runtime dependencies (a live server the tests drive, a device, a
network service) are declared in `DOMAIN.md` as `kind: api` sources with
reachability stated — the existing queryable-sources machinery (health
vitals, dead-source demotion, snapshot citation) applies unchanged.

## Rollout (pilot → sweep, per our own convention)

- **Phase 1 (this PR, additive):** `problems/` with the code pack drafted +
  a `problems/kb/` marker noting the template root IS the kb pack today.
  No engine files change yet — nothing breaks the live poe2 instance's
  mechanism cherry-pick flow.
- **Phase 2 (pilot):** instantiate the code pack INSIDE `PathOfBuilding-AI`
  (the artifact is the repo, so the swarm files live in the target repo):
  DOMAIN.md = the `docs/TOOL_FRICTION.md` backlog (10 open, pilot-derived,
  each self-testable against the headless server on :52178), T0001 = harness.
  Friction found in the seam feeds back here.
- **Phase 3 (extraction):** once the pilot proves the seam, extract the root
  kb-isms into `problems/kb/` properly and add the three engine hooks, so the
  root holds only engine. Until then the kb pack stays where it is.

## Open questions

- Does the code pack need a `priority:` vocabulary beyond
  event/gap-fill/maintenance? (Suspect no: regression=event, backlog=gap-fill,
  refactor/debt=maintenance.)
- Cross-cutting instances (a KB *and* code in one repo — e.g. a KB whose
  tooling the swarm also maintains): out of scope; run two instances.
