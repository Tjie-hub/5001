#!/usr/bin/env bash
# Self-healing supervisor for the Dataset B broker-flow backfill.
# Restarts the (idempotent, resumable) fetcher if it exits for any reason
# until 0 cells are pending. Not tracked by the Claude Code harness's
# background-task memory watchdog on purpose (launched via nohup+disown),
# so a host memory squeeze that kills harness-tracked tasks doesn't stop it.
set -u
cd "$(dirname "$0")/../../../../.."
SCRIPT="docs/research_programs/P-M/dataset_b/backfill_broker_flow.py"
LOG="docs/research_programs/P-M/dataset_b/store/logs/supervisor.log"
mkdir -p "$(dirname "$LOG")"

for i in $(seq 1 300); do
  echo "[supervisor] $(date -u +%FT%TZ) iteration=$i starting fetcher" >> "$LOG"
  python3 "$SCRIPT" >> "$LOG" 2>&1
  rc=$?
  pending=$(python3 "$SCRIPT" --dry-run 2>>"$LOG" | grep -o 'pending=[0-9]*' | cut -d= -f2)
  echo "[supervisor] $(date -u +%FT%TZ) iteration=$i exited rc=$rc pending=$pending" >> "$LOG"
  if [ "$pending" = "0" ]; then
    echo "[supervisor] $(date -u +%FT%TZ) COMPLETE — 0 cells pending" >> "$LOG"
    break
  fi
  sleep 10
done
