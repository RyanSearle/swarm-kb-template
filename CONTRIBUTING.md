# Contributing

Thanks for your interest! This project is a small, opinionated engine — the
best contributions respect its design constraints (all coordination through
git; agents are short-lived and disposable; every rule earns its place by a
documented failure). Read `DESIGN.md` before proposing mechanism changes.

## What to contribute

- **Mechanism fixes** — anything under `bin/`, `scripts/`, `procedures/`,
  `protocols/`, `AGENT.md`. If you run an instance and fix the mechanism
  there, please PR the fix back here (see
  `docs/design/template-and-instance.md` for the two-way flow).
- **Problem packs** — new packs under `problems/` (see
  `docs/design/problem-packs.md` for the three-file seam: `DOMAIN.md`
  skeleton + `SHAPES.md` + `EXECUTE.md`). A pack PR should name at least one
  real instance where you ran it.
- **Design lessons** — if your instance hit a failure mode the rules don't
  cover, an issue describing it (symptom, root cause, what would have caught
  it) is a first-class contribution even without code.

## Ground rules

- **Keep the launcher dumb.** No coordination logic outside git. If a change
  needs shared state, it belongs in refs/files-on-main, not in the runner.
- **Domain-agnostic only.** Nothing outside `problems/` and the docs may
  reference a specific subject domain. (`DOMAIN.md` at the root is a
  skeleton.)
- **One concern per PR**, single-line commit messages ≤ 200 chars (matching
  `protocols/CONVENTIONS.md` — detail goes in the PR description).
- Run the checks locally before pushing:
  `bash -n bin/*.sh scripts/*.sh && python3 -m py_compile scripts/*.py`
  (CI runs the same).

## Testing changes

There is no unit-test suite for the mechanism — its test is an instance.
For non-trivial changes, run at least one agent end-to-end against a scratch
instance (`docs/INSTANTIATE.md`, then `bin/agent-run.sh`) and say in the PR
what you observed.
