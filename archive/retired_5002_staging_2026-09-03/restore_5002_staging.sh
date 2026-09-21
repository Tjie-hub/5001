#!/bin/bash
# Restore the retired 5002 staging instance (scheduler-stubbed dev server).
# Archived 2026-09-03 — see README.md in this directory.
#
# Safe to run while production (idx-walkforward.service, port 5001) is up:
# the scheduler stub below guarantees no second scheduler instance.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"   # archive/<dir>/ -> repo root
PORT=5002

if ss -tln | grep -q ":$PORT "; then
    echo "port $PORT is already in use — nothing to do" >&2
    exit 1
fi

cd "$REPO"
echo "launching staging on http://127.0.0.1:$PORT (repo: $REPO, scheduler: stubbed)"
nohup venv/bin/python -c "
import scheduler
scheduler.start_scheduler = lambda: None
import app
app.app.run(host='127.0.0.1', port=$PORT, threaded=True)
" > /tmp/staging_$PORT.log 2>&1 &

sleep 10
curl -fsS "http://127.0.0.1:$PORT/api/v1/health" >/dev/null \
    && echo "staging is up: http://127.0.0.1:$PORT  (log: /tmp/staging_$PORT.log)" \
    || { echo "staging failed to become healthy — check /tmp/staging_$PORT.log" >&2; exit 1; }
