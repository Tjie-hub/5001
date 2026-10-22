#!/bin/bash
# Sunday 2026-10-25 full {FQ} financials pull — OS-job wrapper (U3, ZCODE_BRIEF_UPDATE_2026-10-22).
# Armed as two one-off systemd user timers (09:05 session 1, 13:00 resume; the fetch is resumable
# and no-ops if the morning finished). Everything data-pulling runs HERE, never inside a model turn
# (the 10-21 lesson: a model-turn pilot died on a Z.ai 429 before its first GET).
# Pre-flights: only run on 2026-10-25; refuse while a jurnal26 tape backfill process is running
# (its nightly job owns the token 21:05-06:30); token must pass the read-only pre-open check;
# >= 5G free where the data lands. fetch itself: no --force, default --max-minutes 170 cap.
# The FQ_PULL_* env vars exist ONLY so tests/test_fq_full_pull_script.py can stub each guard;
# production runs use the defaults. Logs: logs/fin_full_pull_20261025_<tag>.log
set -u
cd "/home/tjiesar/10 Projects/idx-walkforward-5001" || exit 1
EXPECT_DATE="${FQ_PULL_EXPECT_DATE:-2026-10-25}"
PGREP_CMD="${FQ_PULL_PGREP_CMD:-pgrep -f tape_backfill}"
PRECHECK_CMD="${FQ_PULL_PRECHECK_CMD:-venv/bin/python3 auto_token.py --preopen-check}"
FETCH_CMD="${FQ_PULL_FETCH_CMD:-venv/bin/python3 scripts/stockbit_fin_backfill.py fetch}"
LOG="${FQ_PULL_LOG:-logs/fin_full_pull_20261025_${1:-manual}.log}"
log() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }

log "START full-pull session ${1:-manual}"
if [ "$(date +%F)" != "$EXPECT_DATE" ]; then
  log "REFUSED: today is $(date +%F), expected ${EXPECT_DATE} (never catch up outside the approved Sunday window)"
  exit 1
fi
if $PGREP_CMD > /dev/null 2>&1; then
  log "REFUSED: a jurnal26 tape backfill process is running (token shared 21:05-06:30)"
  exit 1
fi
if ! $PRECHECK_CMD >> "$LOG" 2>&1; then
  log "REFUSED: token pre-open check failed (output above); never log in from a scheduled run"
  exit 1
fi
FREE_GB=$(df -BG --output=avail /home/tjiesar/idx_external 2>/dev/null | tail -1 | tr -dc '0-9')
if [ -z "$FREE_GB" ]; then
  FREE_GB=$(df -BG --output=avail /home/tjiesar 2>/dev/null | tail -1 | tr -dc '0-9')
fi
df -h /home/tjiesar/idx_external >> "$LOG" 2>&1 || df -h /home/tjiesar >> "$LOG" 2>&1
log "free space: ${FREE_GB:-unknown}G"
if [ -n "$FREE_GB" ] && [ "$FREE_GB" -lt 5 ]; then
  log "REFUSED: less than 5G free where the raw store lands"
  exit 1
fi

$FETCH_CMD >> "$LOG" 2>&1
rc=$?
log "fetch rc=${rc}"
log "END full-pull session ${1:-manual}"
exit $rc
