#!/usr/bin/env bash
# swarm-tick.sh — the SCHEDULED entry. cron/launchd calls THIS, not agent-run.
#
# Wakes up to MAX_AGENTS agents in parallel; each self-elects a role and claims
# work via git. Backlog-aware: never wake more agents than there is open work,
# with a floor of 1 so an empty backlog still elects a PLANNER to refill it.
set -euo pipefail

REPO="${REPO:-$HOME/projects/swarm-kb-template}"
MAIN_BRANCH="${MAIN_BRANCH:-main}"
MAX_AGENTS="${MAX_AGENTS:-2}"                 # local default: keep it small
STATE_DIR="${STATE_DIR:-$HOME/.local/state/swarm-kb}"
mkdir -p "$STATE_DIR"
LOG="$STATE_DIR/launch.log"

cd "$REPO"
git fetch -q origin 2>/dev/null || true
git checkout -q "$MAIN_BRANCH" 2>/dev/null || true
git pull -q --ff-only 2>/dev/null || true

open="$(grep -rl '^status: open' tasks/ 2>/dev/null | wc -l | tr -d ' ')"
if   [ "${open:-0}" -lt 1 ];           then n=1
elif [ "$open" -lt "$MAX_AGENTS" ];    then n="$open"
else                                        n="$MAX_AGENTS"; fi

echo "$(date -u +%FT%TZ) tick open=$open waking=$n max=$MAX_AGENTS" >> "$LOG"
for _ in $(seq 1 "$n"); do
  AGENT_ID="$(date -u +%Y%m%d%H%M)-$(openssl rand -hex 2)" \
    "$REPO/bin/agent-run.sh" >> "$LOG" 2>&1 &
  sleep 2   # stagger starts so integrator/planner claim races resolve cleanly
done
wait
echo "$(date -u +%FT%TZ) tick done" >> "$LOG"
