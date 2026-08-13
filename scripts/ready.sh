#!/bin/bash
# ready.sh <TASK_ID> — publish the current work branch for integration.
# Pushes the branch itself (so the integrator can fetch it) and marks it
# ready via refs/ready/<TASK_ID> pointing at your HEAD.
set -euo pipefail
REMOTE="${REMOTE:-origin}"
ID="$1"
BRANCH=$(git rev-parse --abbrev-ref HEAD)
[ "$BRANCH" != "main" ] || { echo "refusing: you are on main"; exit 1; }
git push -q "$REMOTE" "$BRANCH"
git push -q "$REMOTE" "HEAD:refs/ready/$ID"
echo "published $BRANCH as ready/$ID"
