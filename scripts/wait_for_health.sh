#!/bin/bash
# Startup verification (audit P-5): block until /health answers 200 with
# status ok, or fail after ~120s so systemd marks the start failed and
# Restart=always retries. Used as ExecStartPost in idx-walkforward.service;
# also runnable by hand after any deploy.
URL="${1:-http://127.0.0.1:5001/health}"
for i in $(seq 1 60); do
    body=$(curl -fsS --max-time 3 "$URL" 2>/dev/null)
    if [ $? -eq 0 ] && echo "$body" | grep -q '"status": *"ok"'; then
        echo "health OK after ${i} attempt(s): $body"
        exit 0
    fi
    sleep 2
done
echo "health check FAILED: $URL not healthy after 120s" >&2
exit 1
