#!/bin/bash
# Cron failure alerting wrapper (hardening Phase 4 / audit P-4).
#
# Two cron jobs failed EVERY run for weeks because their scripts didn't
# exist and cron output went to log files nobody read. Every cron entry now
# runs through this wrapper: output is logged per-job, and any nonzero exit
# (including "script not found") sends a Telegram alert with the last log
# lines.
#
# Usage: cron_wrap.sh <job-name> <command> [args...]
set -u
JOB="$1"; shift
DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="${CRON_WRAP_LOG_DIR:-$DIR/logs}"
LOG="$LOG_DIR/cron_${JOB}.log"
mkdir -p "$LOG_DIR"

echo "[$(date '+%F %T')] START $JOB: $*" >> "$LOG"
"$@" >> "$LOG" 2>&1
rc=$?
echo "[$(date '+%F %T')] EXIT $JOB rc=$rc" >> "$LOG"

if [ "$rc" -ne 0 ]; then
    ENV_FILE="${CRON_WRAP_ENV:-$DIR/.env}"
    TOKEN=$(grep -E '^TELEGRAM_TOKEN=' "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2-)
    CHAT=$(grep -E '^TELEGRAM_CHAT_ID=' "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2-)
    API_BASE="${CRON_WRAP_API_BASE:-https://api.telegram.org}"
    TAIL=$(tail -n 5 "$LOG")
    MSG="🚨 CRON FAIL [$JOB] rc=$rc on $(hostname)
$TAIL"
    if [ -n "$TOKEN" ] && [ -n "$CHAT" ]; then
        curl -fsS --max-time 10 "$API_BASE/bot$TOKEN/sendMessage" \
            --data-urlencode "chat_id=$CHAT" \
            --data-urlencode "text=$MSG" >/dev/null 2>&1 \
            || echo "[$(date '+%F %T')] ALERT SEND FAILED for $JOB" >> "$LOG"
    else
        echo "[$(date '+%F %T')] ALERT SKIPPED (no telegram creds) for $JOB" >> "$LOG"
    fi
fi
exit $rc
