#!/usr/bin/env bash
# agent-run.sh — launch exactly ONE swarm-KB agent for ONE unit of work.
#
# The compute-layer entrypoint, DUMB by design: all task coordination lives in
# git (claims-as-refs), so this only has to spin up an agent pointed at AGENT.md.
# It runs identically locally or in a cloud environment — only the caller differs.
#
# Isolation: each agent works in a FRESH throwaway clone (exactly like a cloud
# agent), so N local agents never collide on a shared working tree. Branches and
# claims are pushed to origin — the single shared coordination plane.
#
# Env:
#   REPO            canonical local clone, used only to discover the remote url
#                   (default: $HOME/projects/swarm-kb-template)
#   REMOTE_URL      git url every agent clones/pushes (default: REPO's origin)
#   MAIN_BRANCH     default: main
#   AGENT_ID        default: <yyyymmddHHMM>-<hex>
#   CLAIM_TTL_MIN   claim staleness for the reaper (default 45)
#   MODEL           optional --model override
#   PERMISSION_MODE claude permission mode (default acceptEdits). For UNATTENDED
#                   operation use bypassPermissions — safe here because each agent
#                   runs in a throwaway clone holding no secrets — or commit a
#                   scoped .claude/settings.json allowlist.
set -euo pipefail

REPO="${REPO:-$HOME/projects/swarm-kb-template}"
REMOTE_URL="${REMOTE_URL:-$(git -C "$REPO" remote get-url origin)}"
MAIN_BRANCH="${MAIN_BRANCH:-main}"
export CLAIM_TTL_MIN="${CLAIM_TTL_MIN:-45}"
export AGENT_ID="${AGENT_ID:-$(date -u +%Y%m%d%H%M)-$(openssl rand -hex 2)}"
PERMISSION_MODE="${PERMISSION_MODE:-acceptEdits}"
MODEL="${MODEL:-}"

RUN_DIR="${RUN_DIR:-${STATE_DIR:-$HOME/.local/state/swarm-kb}/agents}"
mkdir -p "$RUN_DIR"
PIDFILE="$RUN_DIR/$AGENT_ID.pid"
echo "$$" > "$PIDFILE"   # swarm-tick.sh counts/reaps the pool by these
WORK="$(mktemp -d "${TMPDIR:-/tmp}/swarm-${AGENT_ID}.XXXXXX")"
cleanup() { cd /; rm -rf "$WORK"; rm -f "$PIDFILE"; }
trap cleanup EXIT

git clone -q "$REMOTE_URL" "$WORK"
cd "$WORK"
# Pull the coordination refs a plain clone doesn't fetch by default.
git fetch -q origin \
  '+refs/claims/*:refs/claims/*' \
  '+refs/ready/*:refs/ready/*' \
  '+refs/bounced/*:refs/bounced/*' 2>/dev/null || true
git checkout -q "$MAIN_BRANCH"

read -r -d '' PROMPT <<PROMPT_EOF || true
You are swarm agent ${AGENT_ID}, working in an isolated clone at ${WORK}.
Read AGENT.md and follow it EXACTLY. Do exactly ONE unit of work: fetch refs,
elect a role (integrator / planner / worker) by winning a git claim, complete
one task, one merge-queue pass, or one planning pass, push your work branch (or
merge, if you are the integrator, per procedures/INTEGRATOR.md), release your
claim, then exit. Never commit to ${MAIN_BRANCH} except as the integrator.
PROMPT_EOF

args=(-p "$PROMPT" --permission-mode "$PERMISSION_MODE")
[ -n "$MODEL" ] && args+=(--model "$MODEL")
claude "${args[@]}"
