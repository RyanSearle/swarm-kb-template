# DOMAIN — <your-instance-name>  (code pack)

> The single file that adapts the machine to a codebase and its goal. The
> PLANNER treats this as the specification it plans against. Keep it under
> ~10 KB — it is read every planning session. Fill every section, then delete
> these blockquote instructions. Pack docs: `problems/code/` in the template;
> design: `docs/design/problem-packs.md`.

## Mission

<One paragraph. What software, what capability it must gain or defect class
it must lose, and for whom. State what "solved" looks like as an observable —
"all backlog items closed and `<verify-cmd>` green" is the default.>

## Owner

<Name>. The DIRECTIVES / QUESTIONS / DECISIONS protocols address them.

## Target

- **Repo layout:** <where the code under work lives relative to this file —
  usually this repo; name the top-level dirs that matter and any submodules
  with pinned versions agents must NOT bump.>
- **Build:** <the command(s) that compile/typecheck from a fresh clone,
  incl. toolchain versions. If unattended bootstrap needs steps, list them —
  agents run in throwaway clones with no interactive setup.>
- **Run:** <how to start the thing under test, if the tests need it live —
  or state that the harness starts/stops it itself (preferred).>

## Verification (the completion model)

- **Canonical verify command:** `<e.g. scripts/verify.sh>` — build + full
  test suite, exit 0 = green. This is THE definition of working; the
  integrator's merge gate runs exactly this on every merge candidate.
- **Harness status:** <exists | to-be-built>. If to-be-built, the bootstrap
  task (type `harness`) creates it FIRST: runner + smoke tests, deterministic,
  runnable in a fresh clone. Requirements/constraints for it: <e.g. must
  drive the live server on :PORT, must not need network beyond X>.
- **Determinism rules:** <flaky-test policy, timeouts, what external state
  tests may touch. A test that needs an undeclared resource is a harness bug.>

## Sources (by confidence tier)

> Same three KINDS as any instance (`docs/design/queryable-sources.md`):
> **file** (specs/docs in-repo), **web**, **api** (live services the tests
> drive — declare reachability; a dead service is a FINDING, not a retry loop).

| Tier | Source | Notes |
|---|---|---|
| official | <upstream docs / protocol spec> | |
| dataset | <in-repo docs, e.g. a friction/bug backlog file> | usually the DoD's source of truth |
| api | <live service under test, host:port, health endpoint> | snapshot-cite behaviours observed |

## Release/event triggers

- <What re-opens work: upstream/dependency releases (which? how classified?),
  a red canonical verify on main (always priority `event`), regressions
  reported by the owner via DIRECTIVES.>
- Nothing is re-verified merely for being old; a green suite is the freshness.

## Definition of done (enumerable backlog, each item with its proof)

> One line per item: what, and the PROOF that closes it (test file/name that
> must pass under the canonical verify command). The planner diffs this list
> against tasks/ + the test suite. Items without a stateable proof get a
> harness/reshape task first, not a fix task.

- [ ] <item — proof: `tests/<file>` green under `<verify-cmd>`>
- **Capability self-audit:** periodically, can a consumer do <the mission
  task> against the built artifact ALONE? Each gap it hits → a backlog item
  with a proof.
