#!/usr/bin/env bash
# Run on the USER's laptop (needs git, gh logged in, python3). Starts the relay agent.
set -euo pipefail
BR="claude/friendly-lamport-y8hz5r"; DIR="${OM_DIR:-$HOME/om-relay}"
for c in git gh python3; do command -v $c >/dev/null || { echo "Missing: $c"; exit 1; }; done
gh auth status >/dev/null 2>&1 || { echo "Run: gh auth login"; exit 1; }
if [ -d "$DIR/.git" ]; then git -C "$DIR" fetch origin "$BR" && git -C "$DIR" checkout "$BR" && git -C "$DIR" pull --ff-only origin "$BR"
else gh repo clone tharkacoding/om "$DIR" -- --branch "$BR"; fi
echo "Relay starting. Every command Claude sends will ask you [y/N]. Ctrl+C stops it."
cd "$DIR" && exec python3 relay/laptop_agent.py --branch "$BR"
