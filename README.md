# swarm-kb — an autonomous, git-coordinated knowledge-base swarm

Fire many short-lived AI agents at a git repo; they self-organize **through git
itself** — no shared database, no central orchestrator — to build and maintain a
dense, cited knowledge base for ONE domain you specify. Coordination is git refs:
claims-as-refs, branch-per-task, a single serial integrator, a merge queue. The
machine is self-correcting: every structural change goes
propose → adversarial self-verify → apply → monitor → auto-rollback.

**This repo is the TEMPLATE** — domain-agnostic mechanism. To run it on your own
subject you fill exactly ONE file (`DOMAIN.md`) and register your sources.
Everything else *is* the machine and works unchanged across domains.

## What's in the box

- **`AGENT.md`** — the single entrypoint every agent reads; it elects a role
  (worker / planner / integrator) by winning a git claim, does one unit of work,
  and exits.
- **`procedures/`** — the role playbooks. **`protocols/`** — the coordination
  format: `CONVENTIONS` (load-bearing rules), `DECISIONS` (append-only autonomy
  log), `DIRECTIVES` / `QUESTIONS` (owner ↔ machine channels).
- **`scripts/`** — git-as-substrate coordination (`claim.sh` / `ready.sh` /
  `integrate.sh`), the index builder, and a read-only `dashboard.py`.
- **`bin/` + `launch/`** — launch one agent (`agent-run.sh`, a throwaway clone)
  or install a scheduled swarm.
- **`docs/design/`** — `DESIGN.md` (the full concept + the hard-won lesson behind
  every rule) and `queryable-sources.md` (treating APIs/web as first-class
  knowledge sources).

## Quick start

1. **Use this template** (GitHub *Use this template*, or fork).
2. **Fill `DOMAIN.md`** for your subject — the only domain-specific file.
3. **Register sources** — files in `data/`, web pages, or query APIs
   (`docs/design/queryable-sources.md`).
4. **Launch** — `bin/agent-run.sh` for one agent; `launch/` for a scheduled swarm.
5. **Watch** — `python3 scripts/dashboard.py` (read-only board + timeline).

Full walkthrough: **`docs/INSTANTIATE.md`**.

## Reference instance

The **poe2-build-kb** run — a Path of Exile 2 build knowledge base, 40+ production
waves — is the reference instance these rules were distilled from; `DESIGN.md`
cites its evidence inline. How an instance relates to this template, and how
improvements flow **both** ways, is in **`docs/design/template-and-instance.md`**.
