#!/bin/bash
# integrate.sh — integrator helpers (the merging itself is done by the agent
# following procedures/INTEGRATOR.md with ordinary git commands).
#
#   integrate.sh list           ready branches, oldest first
#   integrate.sh done <ID>      cleanup after a successful merge
#   integrate.sh bounce <ID>    move ready -> bounced (after merge --abort)
set -euo pipefail
REMOTE="${REMOTE:-origin}"
git fetch -q --prune "$REMOTE" \
  '+refs/claims/*:refs/claims/*' '+refs/ready/*:refs/ready/*' \
  '+refs/bounced/*:refs/bounced/*' '+refs/heads/*:refs/remotes/'"$REMOTE"'/*'

case "${1:-list}" in
  list)
    git for-each-ref 'refs/ready/*' --sort=creatordate \
      --format='%(refname:short)  ->  %(objectname:short)  %(creatordate:relative)' ;;
  done)
    ID="$2"
    git push -q "$REMOTE" ":refs/ready/$ID" 2>/dev/null || true
    git push -q "$REMOTE" ":refs/claims/task-$ID" 2>/dev/null || true
    # delete merged task branches matching this id
    for B in $(git branch -r --list "$REMOTE/task/$ID-*" | sed "s| *$REMOTE/||"); do
      git push -q "$REMOTE" ":refs/heads/$B" 2>/dev/null || true
    done
    git update-ref -d "refs/ready/$ID" 2>/dev/null || true
    echo "cleaned up $ID" ;;
  bounce)
    ID="$2"
    SHA=$(git show-ref -s "refs/ready/$ID")
    git push -q "$REMOTE" "$SHA:refs/bounced/$ID" ":refs/ready/$ID"
    git update-ref -d "refs/ready/$ID" 2>/dev/null || true
    echo "bounced $ID (planner will re-open with instructions)" ;;
  *) echo "usage: integrate.sh list|done|bounce [id]"; exit 2 ;;
esac
