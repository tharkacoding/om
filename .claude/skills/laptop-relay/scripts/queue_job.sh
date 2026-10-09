#!/usr/bin/env bash
# Usage: queue_job.sh "<command>"   (run from the repo root, on the relay branch)
set -euo pipefail
BR="claude/friendly-lamport-y8hz5r"
[ $# -eq 1 ] || { echo 'usage: queue_job.sh "<command>"'; exit 1; }
git pull -q --rebase origin "$BR" || true
mkdir -p relay/jobs
n=$(ls relay/jobs 2>/dev/null | grep -c '\.json$' || true); id=$(printf '%03d' $((n+1)))
python3 -I -c 'import json,sys;print(json.dumps({"cmd":sys.argv[1]}))' "$1" > "relay/jobs/$id.json"
git add "relay/jobs/$id.json"; git commit -qm "relay job $id"; git push -q origin "$BR"
echo "$id"
