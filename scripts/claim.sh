#!/bin/bash
# claim.sh — atomic task/role claims via git refs (CAS at the remote).
#
#   claim.sh try <name>      exit 0 = claim won; exit 1 = already claimed
#   claim.sh release <name>  delete the claim ref (yours, normally)
#   claim.sh reap            delete all claims older than CLAIM_TTL_MIN
#   claim.sh list            show live claims with age
#
# How it works: each attempt creates a UNIQUE empty commit (agent id +
# timestamp in the message => unique sha) and pushes it to refs/claims/<name>.
# Creating a new ref succeeds for exactly one pusher; everyone else is
# rejected (non-fast-forward). No lock server needed.
#
# Env: AGENT_ID (recommended), CLAIM_TTL_MIN (default 45), REMOTE (origin)
set -euo pipefail
REMOTE="${REMOTE:-origin}"
TTL_MIN="${CLAIM_TTL_MIN:-45}"
AGENT="${AGENT_ID:-$(date -u +%Y%m%d%H%M)-$$}"

fetch_claims() {
  git fetch -q --prune "$REMOTE" \
    '+refs/claims/*:refs/claims/*' \
    '+refs/ready/*:refs/ready/*' \
    '+refs/bounced/*:refs/bounced/*' 2>/dev/null || true
}

case "${1:-}" in
  try)
    NAME="$2"; fetch_claims
    if git show-ref --verify -q "refs/claims/$NAME"; then exit 1; fi
    EMPTY_TREE=$(git hash-object -t tree /dev/null)
    SHA=$(git commit-tree "$EMPTY_TREE" -m "claim $NAME by $AGENT at $(date -u +%FT%TZ)")
    if git push -q "$REMOTE" "$SHA:refs/claims/$NAME" 2>/dev/null; then
      git update-ref "refs/claims/$NAME" "$SHA"
      echo "claimed $NAME as $AGENT"; exit 0
    else
      exit 1   # lost the race
    fi ;;
  release)
    NAME="$2"
    git push -q "$REMOTE" ":refs/claims/$NAME" 2>/dev/null || true
    git update-ref -d "refs/claims/$NAME" 2>/dev/null || true
    echo "released $NAME" ;;
  reap)
    fetch_claims
    NOW=$(date -u +%s)
    git for-each-ref 'refs/claims/*' --format='%(refname) %(objectname)' | \
    while read -r REF SHA; do
      TS=$(git show -s --format=%ct "$SHA")
      AGE_MIN=$(( (NOW - TS) / 60 ))
      if [ "$AGE_MIN" -gt "$TTL_MIN" ]; then
        echo "reaping ${REF#refs/claims/} (age ${AGE_MIN}m > ${TTL_MIN}m)"
        git push -q "$REMOTE" ":$REF" 2>/dev/null || true
        git update-ref -d "$REF" 2>/dev/null || true
      fi
    done ;;
  list)
    fetch_claims
    NOW=$(date -u +%s)
    git for-each-ref 'refs/claims/*' --format='%(refname:short) %(objectname)' | \
    while read -r REF SHA; do
      TS=$(git show -s --format=%ct "$SHA")
      echo "$REF  age $(( (NOW - TS) / 60 ))m  ($(git show -s --format=%s "$SHA"))"
    done ;;
  *) echo "usage: claim.sh try|release|reap|list [name]"; exit 2 ;;
esac
