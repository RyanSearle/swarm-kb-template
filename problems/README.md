# problems/ — problem packs

A **problem pack** adapts the engine to a KIND of problem (knowledge base,
programming problem, …) the way `DOMAIN.md` adapts an instance to a subject.
Design + seam definition: `docs/design/problem-packs.md`.

Each pack supplies exactly three files:

- `DOMAIN.md` — the spec skeleton the planner plans against for this
  problem type (copied over the root `DOMAIN.md` at instantiation).
- `SHAPES.md` — task types, artifact schema, and the proof-of-done
  convention for `dod:` fields.
- `EXECUTE.md` — how a worker executes and self-verifies one unit of work,
  and the merge gate the integrator runs.

Instantiate: take the template → pick a pack → copy its files over the seam
(`problems/<pack>/DOMAIN.md` → `DOMAIN.md`, keep `SHAPES.md`/`EXECUTE.md`
beside `procedures/`) → fill the spec → launch (`docs/INSTANTIATE.md`).

Packs:

- `kb/` — knowledge-base problems. Currently the template ROOT is the kb
  pack (its files predate this layout); see `kb/README.md`. Extraction into
  this directory is Phase 3 of the design.
- `code/` — programming problems with self-testable completion: done =
  named tests green behind ONE canonical verify command; the verification
  harness is itself agent-built (bootstrap task T0001).
