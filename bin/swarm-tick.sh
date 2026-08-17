#!/usr/bin/env bash
# swarm-tick.sh — the SCHEDULED entry. cron/launchd calls THIS, not agent-run.
#
# TOP-UP POOL of INDEPENDENT agents. Each tick:
#   1. prunes finished agents and reaps any that have run past AGENT_MAX_MIN
#      (a hung-session backstop), via per-agent pidfiles under STATE_DIR/agents,
#   2. counts how many agents are still alive, and
#   3. launches only enough NEW agents to refill the pool to MAX_AGENTS — each
#      fully DETACHED (nohup + disown; NO `wait`).
# Agents share nothing but git refs, so a slow/hung one never blocks the tick,
# its peers, or the next tick; concurrency is capped by the top-up count, so
# ticks neither pile up nor stall.
# REQUIRES the plist to set AbandonProcessGroup=true — otherwise launchd kills
# the detached agents when this short-lived tick process exits.
set -euo pipefail

REPO="${REPO:-$HOME/projects/swarm-kb-poe2}"
MAIN_BRANCH="${MAIN_BRANCH:-main}"
MAX_AGENTS="${MAX_AGENTS:-2}"
AGENT_MAX_MIN="${AGENT_MAX_MIN:-30}"   # kill an agent still running past this (keep < CLAIM_TTL_MIN so its claim later reaps)
STATE_DIR="${STATE_DIR:-$HOME/.local/state/swarm-kb}"
RUN_DIR="$STATE_DIR/agents"
mkdir -p "$RUN_DIR"
LOG="$STATE_DIR/launch.log"
export STATE_DIR RUN_DIR               # so agent-run.sh writes its pidfile where we read it

cd "$REPO"
git fetch -q origin 2>/dev/null || true
git checkout -q "$MAIN_BRANCH" 2>/dev/null || true
git pull -q --ff-only 2>/dev/null || true

# portable elapsed-seconds for a pid (parses ps etime [[dd-]hh:]mm:ss)
agent_age_s() {
  local et; et="$(ps -o etime= -p "$1" 2>/dev/null | tr -d ' ')"; [ -z "$et" ] && return 1
  local d=0 hms="$et" h=0 m s
  case "$et" in *-*) d="${et%%-*}"; hms="${et#*-}";; esac
  case "$hms" in
    *:*:*) h="${hms%%:*}"; hms="${hms#*:}"; m="${hms%%:*}"; s="${hms#*:}";;
    *:*)   m="${hms%%:*}"; s="${hms#*:}";;
    *)     m=0; s="$hms";;
  esac
  echo $(( (10#${d}*86400) + (10#${h}*3600) + (10#${m}*60) + 10#${s} ))
}

# 1+2. prune finished agents, reap over-age ones, count the survivors.
running=0
for pf in "$RUN_DIR"/*.pid; do
  [ -e "$pf" ] || continue
  pid="$(cat "$pf" 2>/dev/null || true)"
  if [ -z "$pid" ] || ! kill -0 "$pid" 2>/dev/null; then
    rm -f "$pf"; continue                        # already exited → free the slot
  fi
  age="$(agent_age_s "$pid" 2>/dev/null || echo 0)"
  if [ "${age:-0}" -gt "$(( AGENT_MAX_MIN * 60 ))" ]; then
    echo "$(date -u +%FT%TZ) reap agent pid=$pid age=${age}s > ${AGENT_MAX_MIN}m" >> "$LOG"
    pkill -P "$pid" 2>/dev/null || true          # its claude child, best-effort
    kill "$pid" 2>/dev/null || true
    rm -f "$pf"; continue
  fi
  running=$(( running + 1 ))
done

# 3. top the pool up to MAX_AGENTS, bounded by the open backlog (floor 1 when
#    there is headroom, so an empty backlog still wakes a PLANNER to refill it).
open="$(grep -rl '^status: open' tasks/ 2>/dev/null | wc -l | tr -d ' ')"
headroom=$(( MAX_AGENTS - running ))
if [ "$headroom" -lt 0 ]; then headroom=0; fi
if   [ "$headroom" -lt 1 ];       then n=0
elif [ "${open:-0}" -lt 1 ];      then n=1
elif [ "$open" -lt "$headroom" ]; then n="$open"
else                                   n="$headroom"; fi

echo "$(date -u +%FT%TZ) tick open=$open running=$running waking=$n max=$MAX_AGENTS" >> "$LOG"

# launch each new agent FULLY DETACHED — no wait; a hung one can't block anything.
for ((i=0; i<n; i++)); do
  AGENT_ID="$(date -u +%Y%m%d%H%M)-$(openssl rand -hex 2)" \
    nohup "$REPO/bin/agent-run.sh" >> "$LOG" 2>&1 &
  disown
  sleep 2   # stagger starts so integrator/planner claim races resolve cleanly
done
# return immediately; the pool self-tops-up next tick.
