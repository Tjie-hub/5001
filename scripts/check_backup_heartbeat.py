#!/usr/bin/env python3
"""External dead-man's-switch for the nightly DB backup crons (walkforward.db
+ research.db) and the weekly restore drill (P1-2, follow-up to the
scheduler heartbeat pattern in audit item 3.7 /
scripts/check_scheduler_heartbeat.py).

Every cron job already alerts on nonzero exit via cron_wrap.sh, but that only
catches a job that *fired and failed* -- it says nothing about a job that
silently stopped firing at all (crontab entry removed by accident, systemd
user session not started at boot, etc.). A ~36h backup gap already occurred
once (2026-07-25/26) and went undetected until manually noticed -- this
closes that gap the same way the scheduler heartbeat closes the equivalent
gap for the scheduler process itself.

Reuses cron_wrap.sh's own per-job log files as the freshness signal (their
mtime advances only when cron_wrap.sh actually runs that job to completion,
success or failure) rather than inventing a new heartbeat file db_backup.py/
db_restore.py would need to be taught to write.

Run from crontab once daily (coarser cadence than the 15-min scheduler
heartbeat is appropriate -- these jobs run daily/weekly, not every few
minutes):
    0 7 * * * cd "<repo>" && venv/bin/python3 scripts/check_backup_heartbeat.py >> logs/heartbeat_check.log 2>&1
"""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.heartbeat import heartbeat_status  # noqa: E402
from utils.telegram import send_telegram  # noqa: E402

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (display name, cron_wrap.sh log path, staleness threshold in minutes).
# Thresholds are the job's own cadence plus slack for a late-but-not-dead run:
# both backups are daily 21:30/21:35 -> 26h; restore drill is weekly Sunday
# 09:00 -> 8d.
DEFAULT_CHECKS = (
    ("nightly DB backup",
     os.path.join(_REPO_ROOT, "logs", "cron_db_backup.log"),
     26 * 60),
    ("nightly research.db backup (R-5)",
     os.path.join(_REPO_ROOT, "logs", "cron_db_backup_research.log"),
     26 * 60),
    ("weekly restore drill",
     os.path.join(_REPO_ROOT, "logs", "cron_db_restore_drill.log"),
     8 * 24 * 60),
)


def _mtime_iso(path):
    """The log file's own last-modified time as an ISO string, or None if it
    doesn't exist yet -- reused as heartbeat_status()'s "last beat" input."""
    try:
        ts = os.path.getmtime(path)
    except OSError:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def check(checks=DEFAULT_CHECKS, now=None):
    """Return 0 if every job's log is FRESH, 1 if any is STALE/MISSING
    (alarming once per stale/missing job, not just once overall)."""
    now_dt = now or datetime.now(timezone.utc)
    rc = 0
    for name, path, stale_after_min in checks:
        last = _mtime_iso(path)
        status = heartbeat_status(last, now_dt, stale_after_min)
        if status == "FRESH":
            continue
        rc = 1
        msg = (f"🔴 CRON DEAD-MAN'S SWITCH: {name} {status} "
               f"(log: {os.path.basename(path)}, last activity: {last or 'never'}). "
               f"cron_wrap.sh alerts on failure, but not on never firing at "
               f"all -- check `crontab -l` and whether the systemd user "
               f"session/cron daemon is up.")
        try:
            send_telegram(msg, event="system.backup_dead")
        except Exception:
            pass  # cron log still captures the print below
        print(msg)
    return rc


if __name__ == "__main__":
    sys.exit(check())
