# EXECUTE — code pack worker procedure & merge gate

Replaces the KB half of `procedures/WORKER.md` §3 for code instances. The
claim → isolate → publish loop is the engine's; this is what "execute" means.

## Worker: execute one task

1. **Read the dod + proof.** If the proof references the canonical verify
   command and it doesn't exist/run in your clone, STOP: this is a harness
   gap. Note it, set the task back to open with `blocked_on:` a proposal for
   the harness task, and exit — never hand-verify around a missing harness.
2. **Red first.** For `fix`/`verify`: write/port the failing test and RUN it
   — confirm it fails for the stated reason before touching code. For
   `feature`: write the specifying tests first where practical.
3. **Make it green.** Implement minimally, matching surrounding code. Live
   services (`kind: api` sources) are driven per WORKER.md "Querying API
   sources": a connection failure is a DEAD source finding, not a retry loop
   and never a mock-it-and-claim-done.
4. **Run the full proof**: the canonical verify command PLUS the task's named
   tests, in your clone, from a clean state. Paste the tail of the output
   into your session log. All green → `status: ready`. Anything red or
   skipped → not ready; fix, split, or bounce yourself back to open.
5. Out-of-scope discoveries → tasks/proposals/, as ever.

## Integrator: merge gate (per candidate, after conflict checks)

1. On the merge candidate (main + branch), run the **canonical verify
   command** from `DOMAIN.md` §Verification. Exit 0 = pass.
2. Any red = **BOUNCE**: push `refs/bounced/<id>` with the failing test names
   + output tail in the bounce note. Do not attempt repair — discard-on-
   failure applies to code exactly as to docs.
3. If the verify command itself fails to START (toolchain/bootstrap broken),
   that is a red MAIN event: merge nothing, and ensure the planner sees it
   (it must seed a priority-event harness task; F4 invariant — a machine that
   can't run its own gate must never keep merging).
4. Gate cost note: the suite runs once per candidate, serialised at the
   integrator — the cheapest stage. If the suite outgrows the tick budget,
   that's a `harness` task (split into smoke-at-gate + full-on-schedule), a
   decision logged via F0, never silently skipped.
