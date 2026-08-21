# swarm-kb — a git-native engine for autonomous agent swarms

[![checks](https://github.com/RyanSearle/swarm-kb-template/actions/workflows/ci.yml/badge.svg)](https://github.com/RyanSearle/swarm-kb-template/actions/workflows/ci.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![template](https://img.shields.io/badge/GitHub-use%20this%20template-2ea44f)](https://github.com/RyanSearle/swarm-kb-template/generate)

Fire many short-lived AI agents at a git repo; they self-organize **through
git itself** — no shared database, no message bus, no central orchestrator.
Born as a knowledge-base builder, now generalizing to **any problem with a
mechanically checkable definition of done** via [problem packs](#problem-packs).

The whole coordination plane is a git remote. Any machine that can clone can
join the swarm — a laptop on cron, a cloud runner, both at once. The launcher
is deliberately **dumb**: all intelligence lives in the repo's procedure
files, all state in git refs.

## How it works

```
        ┌───────────── one git remote = the entire coordination plane ─────────────┐
        │   refs/claims/*   role & task locks (atomic compare-and-swap, TTL-reaped)│
        │   refs/ready/*    finished branches queued for integration               │
        │   refs/bounced/*  rejected branches, with the reason attached            │
        └──────────────────────────────────────────────────────────────────────────┘
                                          ▲
  scheduler tick ─► bin/agent-run.sh ─► fresh throwaway clone ─► AGENT.md
                                          │  role election: first claim wins
              ┌───────────────────────────┼──────────────────────────────┐
          PLANNER (singleton)         WORKER (many)               INTEGRATOR (singleton)
          ingest owner directives     claim ONE task              the only writer to main:
          + answers, diff the         → branch → do the work      drain the ready queue
          definition-of-done          → self-verify → push        serially, run the merge
          against reality,            refs/ready/<id> → exit      gate, bounce anything red
          seed task files
```

Every agent lives for exactly **one unit of work**, then exits. Failure is
cheap by construction: a crashed agent's branch dies unmerged, its claims
expire, and someone else picks the task up. There are no counters or status
files to corrupt — all state is *derived* from listing tasks, refs, and logs.

The machine is **self-correcting**: structural changes go through
propose → adversarial self-verify → apply → monitor a named metric →
auto-rollback (`git revert`), logged in an append-only decision journal the
owner can audit and veto. The design goal is fire-and-forget: the owner
touches mission, secrets, and taste — everything else the system detects, it
fixes.

## Problem packs

A **problem pack** adapts the engine to a *kind* of problem — what "done"
means, what an artifact is, and how the integrator verifies a merge candidate
([design](docs/design/problem-packs.md)):

| | `problems/kb` — knowledge bases | `problems/code` — programming problems |
|---|---|---|
| done | enumerated coverage targets met, every claim cited | named tests green behind ONE canonical verify command |
| artifact | small, cross-linked, frontmattered docs | code change + the regression test that proves it |
| merge gate | link-integrity check + index regen | build + full test suite on the merge candidate |
| negative result | an "absence page" | a regression test pinning the bug |

The verification harness for a code instance is **itself agent-built** — the
bootstrap task creates the runner and smoke tests before any fix task runs.

## Quick start

1. **Use this template** → your new repo (this is the coordination plane
   every agent clones and pushes to).
2. **Pick a problem pack** (`problems/`; the repo root ships as the kb pack).
3. **Fill `DOMAIN.md`** — mission, scope, sources, events, definition of
   done. The one domain-specific file; the planner plans against it.
4. **Launch one agent**: `bin/agent-run.sh` (throwaway clone, one unit of
   work, exits). Prove N=1, then N=2 in parallel, then install the scheduler
   (`launch/`, macOS launchd example; anything that can run a shell script
   on an interval works).
5. **Watch**: `python3 scripts/dashboard.py` — a read-only live board.

Full walkthrough: [`docs/INSTANTIATE.md`](docs/INSTANTIATE.md). Requirements:
`git`, `bash`, `python3`, and an agent CLI (built against
[Claude Code](https://claude.com/claude-code); any runtime that can follow
`AGENT.md` in a checkout works).

## Battle-tested, not whiteboarded

These rules were distilled from **months of unattended production operation**
of the reference instance (a Path of Exile 2 build knowledge base: 100+
autonomous waves, thousands of documents, a concurrent multi-agent swarm on a
10-minute scheduler) plus a code-pack pilot (fixing a JSON-RPC toolset
against its own agent-built test harness). Every load-bearing rule in
[`protocols/CONVENTIONS.md`](protocols/CONVENTIONS.md) exists because its
absence cost something once — the evidence is cited inline in
[`DESIGN.md`](DESIGN.md). A sample of scars:

- **Silent degradation is the enemy.** A dead credential once idled the whole
  swarm for days while every tick logged success — hence the pre-launch auth
  canary, per-source health vitals, and derived-state invariant guards.
- **Watermarks lose data; sets don't.** Timestamp-filtered protocol
  processing permanently missed entries — all ingest is now idempotent
  set-comparison.
- **Planners must serialize on the merge queue**, or two of them re-seed the
  same task ids and one side's work is always bounced.
- **Every queue needs a full lifecycle** — bounced refs with no delete path
  haunted the dashboard as immortal "needs rework" items.

## Repository tour

| Path | What it is |
|---|---|
| `AGENT.md` | the single entrypoint every agent reads; role election |
| `DOMAIN.md` | skeleton of the one file you fill per instance |
| `procedures/` | role playbooks: worker, planner, integrator, task shapes |
| `protocols/` | conventions, owner↔machine channels, autonomy decision log |
| `problems/` | problem packs (kb, code) |
| `scripts/` | git-substrate coordination: `claim.sh`, `ready.sh`, `integrate.sh`, dashboard |
| `bin/` | `agent-run.sh` (one agent) and `swarm-tick.sh` (scheduled top-up pool) |
| `launch/` | scheduler examples (macOS launchd) + bring-up guide |
| `DESIGN.md`, `docs/design/` | the full design with evidence, problem packs, queryable sources, template⇄instance flow |

## Status & roadmap

Working today: kb instances (reference instance in production), code-pack
pilot (first instance live). Next: extracting the kb pack out of the repo
root (`problems/kb`, design Phase 3), more packs (research, migration),
first-class cloud compute plane. See
[`docs/design/problem-packs.md`](docs/design/problem-packs.md).

## Contributing

Mechanism fixes, new problem packs, and **failure reports from real
instances** are all welcome — see [`CONTRIBUTING.md`](CONTRIBUTING.md) and
the [Code of Conduct](CODE_OF_CONDUCT.md). If you run an instance, lessons
learned there are the project's lifeblood
([template⇄instance flow](docs/design/template-and-instance.md)).

## License

[MIT](LICENSE) © 2026 Ryan Searle
