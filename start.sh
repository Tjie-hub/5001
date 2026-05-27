#!/bin/bash
# Start IDX Strategy Suite on port 5001
cd "$(dirname "$0")"

# sectors.app overlay — observability only (logs disagreements, does not block trades).
# Flip to "enforce" after reviewing logs/scheduler.log for ≥1 week of [sectors.app SHADOW] entries.
export SECTORS_APP_MODE="${SECTORS_APP_MODE:-shadow}"

exec ./venv/bin/python app.py "$@"
