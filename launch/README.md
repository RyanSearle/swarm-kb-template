# Launch / compute layer (local)

How the machine is spun up. See `DESIGN.md` Part E for the rationale. The rule:
the launcher is **dumb** — it only wakes agents pointed at `AGENT.md`; all task
coordination is in git (claims-as-refs), so local and cloud compute are
interchangeable behind one entrypoint.

## Prerequisites

1. **A configured domain.** `DOMAIN.md` must be filled (subject, sources, event
   triggers, definition-of-done) before any run does useful work — the planner
   plans against it and bootstrap task `T0001` reads it first.
2. **`claude`, `git`, `gh` on PATH**, and `gh auth status` logged in.
3. **The remote exists** and `origin` points at it (already true for this repo).

## Pieces

- `bin/agent-run.sh` — launches ONE agent for ONE unit of work. Clones the remote
  into a throwaway dir (so parallel agents never share a working tree), reads
  `AGENT.md`, does one unit, pushes its branch (or merges, if integrator), exits.
- `bin/swarm-tick.sh` — the scheduled entry. Backlog-aware fan-out of up to
  `MAX_AGENTS` parallel `agent-run.sh`, floor of 1 so an empty backlog still
  elects a planner. **launchd/cron calls this.**
- `launch/com.swarm-kb.agent.plist.example` — a launchd job firing `swarm-tick.sh`
  every 30 min.

## Bring-up (do these in order)

    # 0. fill DOMAIN.md first.

    # 1. prove ONE agent end-to-end, watching it work (interactive perms):
    REPO=$HOME/projects/swarm-kb-template bin/agent-run.sh

    # 2. prove concurrency with 2-3 agents (integrator election, claim races):
    MAX_AGENTS=3 PERMISSION_MODE=bypassPermissions bin/swarm-tick.sh
    tail -f ~/.local/state/swarm-kb/launch.log

    # 3. enable the schedule (unattended):
    cp launch/com.swarm-kb.agent.plist.example \
       ~/Library/LaunchAgents/com.swarm-kb.agent.plist
    # edit paths/PATH in the plist, then:
    launchctl load ~/Library/LaunchAgents/com.swarm-kb.agent.plist

## Knobs

| Env | Meaning | Default |
|---|---|---|
| `MAX_AGENTS` | max CONCURRENT agents — the pool size each tick tops up to | 2 |
| `PERMISSION_MODE` | `acceptEdits` (attended) or `bypassPermissions` (unattended) | acceptEdits |
| `CLAIM_TTL_MIN` | claim staleness before the reaper reclaims it | 45 |
| `AGENT_MAX_MIN` | kill an agent still running past this many minutes (hung-session backstop) | 30 |
| `MODEL` | optional `--model` override | (account default) |

## Notes

- **Auth canary (fail loud, not silent).** Each tick first proves headless
  GitHub auth with a prompt-disabled `git ls-remote` before launching. On
  failure it logs a distinctive `AUTH=FAIL … Fix: gh auth setup-git` line and
  launches NO agents — a missing git credential helper otherwise makes every
  agent die on `git clone` and shows up only as a silently stuck backlog. The
  tick line carries an `auth=ok|FAIL` field; grep it to spot a broken
  credential instantly. Fix once with `gh auth setup-git` (installs
  `gh` as the credential helper), then verify `git ls-remote <origin>`.
- **Agents are independent (top-up pool).** Each tick reaps finished/over-age
  agents, counts the survivors, and launches only enough NEW agents to refill
  the pool to `MAX_AGENTS` — each fully detached, no `wait`. A slow or hung
  agent never blocks the tick, its peers, or the next tick; a stuck one is
  killed after `AGENT_MAX_MIN`. Needs `AbandonProcessGroup=true` in the plist
  (set in the example) so launchd doesn't kill the detached agents when the
  short-lived tick process exits.
- Unattended runs need a non-prompting permission mode (`bypassPermissions`) —
  safe because each agent works in a throwaway clone with no secrets — or a
  committed `.claude/settings.json` allowlist.
- `MAX_AGENTS` is bounded by your machine and your single quota pool. To scale
  past that, add cloud agents (DESIGN.md E3) firing the SAME `agent-run.sh`
  against the SAME remote — no code change.
- **Source pollers** (upstream change detectors that seed events) are separate
  scheduled jobs, kept distinct from worker fan-out.
