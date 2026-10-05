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
    # Global outbound blackout (owner-ordered 2026-10-05): while
    # logs/TELEGRAM_OFF exists, cron failure alerts are skipped too — the
    # python senders check the same file (utils.telegram.is_off). The failure
    # itself still lands in the job log and the rc below.
    if [ -f "$DIR/logs/TELEGRAM_OFF" ]; then
        echo "[$(date '+%F %T')] ALERT SKIPPED (telegram globally OFF) for $JOB" >> "$LOG"
        exit "$rc"
    fi
    ENV_FILE="${CRON_WRAP_ENV:-$DIR/.env}"
    TOKEN=$(grep -E '^TELEGRAM_TOKEN=' "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2-)
    CHAT=$(grep -E '^TELEGRAM_CHAT_ID=' "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2-)
    API_BASE="${CRON_WRAP_API_BASE:-https://api.telegram.org}"
    TAIL=$(tail -n 5 "$LOG")
    MSG="🚨 CRON FAIL [$JOB] rc=$rc on $(hostname)
$TAIL"
    # Redact configured secrets (utils.logging_config.redact_secrets) before
    # this ever reaches Telegram -- the last 5 log lines can contain
    # anything the wrapped job printed, including a leaked secret value
    # (P1-7: this was the one outbound alert path the Python redaction
    # mechanism never covered). Reuses the venv's real implementation
    # instead of a second, drift-prone bash reimplementation. Fails open to
    # unredacted-but-sent (not silently dropped) if the venv/import isn't
    # available -- e.g. local test environments -- since a missed alert
    # reintroduces the exact silent-cron-failure risk this wrapper exists
    # to close (see header comment).
    PYBIN="$DIR/venv/bin/python3"
    if [ -x "$PYBIN" ]; then
        REDACTED=$(cd "$DIR" && "$PYBIN" -c "
import sys
from utils.logging_config import redact_secrets
sys.stdout.write(redact_secrets(sys.stdin.read()))
" <<<"$MSG" 2>>"$LOG")
        if [ -n "$REDACTED" ]; then
            MSG="$REDACTED"
        else
            echo "[$(date '+%F %T')] REDACTION FAILED for $JOB -- sending unredacted" >> "$LOG"
        fi
    else
        echo "[$(date '+%F %T')] REDACTION SKIPPED for $JOB (no venv at $PYBIN)" >> "$LOG"
    fi
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
