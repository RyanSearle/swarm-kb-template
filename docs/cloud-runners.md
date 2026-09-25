# Cloud runners: the PR lane

Scheduled cloud sessions (claude.ai/code routines) can supplement a local
swarm, but their git proxy is restricted: they can push ONLY their own
session branch and open PRs — no custom refs (so no claims CAS), no
arbitrary branch names (so no task/ready branches), no default-branch
pushes (so no cloud integrator or planner), and none of it is configurable.

Design that fits inside those limits — **cloud = worker-only PR lane**:

- One task per firing. The session clones the repo, reads AGENT.md /
  WORKER.md / EXECUTE.md, and executes exactly one open task on its own
  session branch (task id in every commit message).
- **Read-only coordination awareness** replaces claiming: skip any task id
  present in `git ls-remote origin 'refs/claims/*'` (a local agent holds
  it), and skip tasks with an in-flight cloud PR by inspecting
  `refs/pull/*/head` tips' commit messages for task ids. Residual duplicate
  races are resolved by the integrator's duplicate check (first merge won).
- Skip tasks the cloud environment cannot verify or source (localhost
  services, host-only toolchains) — name these exclusions explicitly in the
  routine prompt. If the instance has a verify gate the sandbox can run,
  bootstrap the toolchain first and never submit code without a green gate.
- **Delivery:** push the session branch, open a PR titled
  `swarm-cloud: T#### <one-line summary>`; the PR body is the session log.
  Do not edit the task's status or logs/ — the local integrator does both
  at merge.
- The LOCAL integrator ingests `swarm-cloud:` PRs as ready-queue
  equivalents (see the "Cloud PR lane" section of procedures/INTEGRATOR.md):
  gate before merge, bounce = comment + close + `bounce_reason:` on main.

Scheduling: one routine per instance, hourly (the platform minimum), model
pinned; stagger minutes across instances. Each firing is one full worker
pass or a clean "nothing cloud-claimable" exit.
