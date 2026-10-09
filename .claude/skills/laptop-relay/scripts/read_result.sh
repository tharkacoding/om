#!/usr/bin/env bash
# Usage: read_result.sh <id>   - waits up to ~3 minutes for relay/results/<id>.json
set -euo pipefail
BR="claude/friendly-lamport-y8hz5r"; id="$1"
for i in $(seq 1 18); do
  git pull -q --rebase origin "$BR" 2>/dev/null || true
  [ -f "relay/results/$id.json" ] && { cat "relay/results/$id.json"; exit 0; }
  sleep 10
done
echo '{"ok":false,"error":"no result yet - is the agent running and has the user approved the command?"}'; exit 2
