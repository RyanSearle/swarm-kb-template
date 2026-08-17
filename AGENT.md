# AGENT — entry procedure (every agent, every session)

You are one agent of a multi-agent knowledge-base machine. Read this file and
follow it exactly. Do not improvise the procedure — improvise only within the
work a task asks for. You cannot ask anyone anything mid-session: if blocked,
log to protocols/QUESTIONS.md via a planner task and proceed (never block).

## 0. Session setup

1. Note the current UTC time from your environment; use it everywhere a
   timestamp is needed. Generate your agent id: `<yyyymmddHHMM>-<4 random hex>`.
2. `git fetch origin` (refs, claims, ready — see scripts/claim.sh header for
   the refspec). `git checkout main && git pull`.
3. Create your session log `logs/<agent-id>.md` on your work branch later —
   never write logs directly to main.

## 0.5 Vitals & invariants — fast self-check (DESIGN.md Part F)

Before electing a role, run a CHEAP self-check. Detect-only here; heavier
auto-remediation is the planner's job (procedures/PLANNER.md §0).

1. **Derived-state invariants (F4).** From the tasks/ and logs/ listings, sanity-
   check the quantities the scheduler relies on — e.g. completed tasks since the
   last self-audit log must be <= {{SELF_AUDIT_EVERY:25}}+1; the open-task count
   must not be pinned at 0 while DOMAIN coverage is incomplete. If an invariant is
   violated, prefer electing PLANNER (which force-corrects the starved gate and
   logs the anomaly) over any other role. A starved gate must be caught the first
   session that observes it — never allowed to grow unbounded.
2. **Vitals (F3).** If your unit of work needs the network, confirm the source or
   tool actually responds before relying on it. A dead source or an empty-result
   search tool is a FINDING, not a licence to fabricate: record it for the planner
   and choose work that does not depend on it.

Never fabricate to paper over a failed vital — silent degradation is exactly the
failure mode Part F exists to kill.

## 1. Role election (first match wins)

1. **INTEGRATOR** — if `scripts/integrate.sh list` shows ready branches AND
   `scripts/claim.sh try integrator` wins: follow procedures/INTEGRATOR.md.
2. **PLANNER** — ONLY if NO planning pass is already queued for integration
   (`refs/ready/plan-*` must be empty — check `scripts/integrate.sh list` or
   `git for-each-ref refs/ready/plan-*`). A queued planning pass has not reached
   main yet, so its freshly-seeded task IDs are invisible to you and a second
   planner would re-seed the SAME ids and get BOUNCED (add/add collision). If a
   plan branch is queued, elect INTEGRATOR to drain it (or WORKER), not PLANNER.
   If that guard passes AND `scripts/claim.sh try planner` wins AND any of: (a)
   protocols/DIRECTIVES.md has Pending entries; (b) protocols/QUESTIONS.md has
   Answered entries not yet applied (check every blocked/open task that
   references a question id against the Answered section DIRECTLY — do not use
   timestamps; this check must be idempotent); (c) fewer than
   {{MIN_OPEN_TASKS:5}} open tasks in tasks/; (d) a release/event trigger from
   DOMAIN.md has fired since the last planner log. Follow procedures/PLANNER.md.
3. **WORKER** — if any task file in tasks/ has `status: open`: follow
   procedures/WORKER.md.
4. **Nothing to do** — exit without writing anything. (If this happens while
   DOMAIN coverage is incomplete, something is wrong — prefer electing PLANNER.)

## 2. Do exactly one unit of work

One task (worker), one merge-queue pass (integrator), or one planning pass
(planner). Then exit. Small sessions are the design: failure costs one unit.

## 3. Hard rules (all roles)

- **Never commit or push to `main`.** Only the integrator's merge commits land
  there, via procedures/INTEGRATOR.md.
- **Never edit another task's file or another agent's branch.**
- Release your role/task claims before exiting cleanly
  (`scripts/claim.sh release <name>`). If you crash, the TTL reaps them.
- Every commit message: single line, ≤ 200 chars. Detail goes in your session
  log file, which travels with your branch.
- **Sub-agent dispatches (if your harness offers them) are synchronous.** The
  harness ends your session the moment your reply ends — there is no
  background "waiting" state. Block on dispatched work, integrate its
  results, and finish your commit/release steps all within the same reply.
  Ending a reply with work pending is a crash the reaper has to clean up.
- Follow protocols/CONVENTIONS.md in everything you write.
