#!/usr/bin/env python3
"""External dead-man's-switch for the APScheduler (audit item 3.7).

Run from crontab every ~10 min:
    */10 * * * * cd "<repo>" && venv/bin/python3 scripts/check_scheduler_heartbeat.py >> logs/heartbeat_check.log 2>&1

Reads logs/scheduler_heartbeat.txt (stamped every 5 min by the in-app writer)
and Telegram-alarms when the beat is STALE or MISSING. Independent of the app
process on purpose — if the scheduler dies, this still runs.
"""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.heartbeat import heartbeat_status, read_heartbeat  # noqa: E402
from utils.telegram import send_telegram  # noqa: E402

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "logs", "scheduler_heartbeat.txt")


def check(path=DEFAULT_PATH, stale_after_min=15):
    """Return 0 if FRESH, 1 (and alarm) if STALE/MISSING."""
    last = read_heartbeat(path)
    status = heartbeat_status(last, datetime.now(timezone.utc), stale_after_min)
    if status == "FRESH":
        return 0
    msg = (f"🔴 SCHEDULER HEARTBEAT {status} — last beat: {last or 'never'}. "
           f"APScheduler/app may be dead; trades/reports NOT running. "
           f"Restart via ./start.sh.")
    try:
        send_telegram(msg)
    except Exception:
        pass  # cron log still captures the print below
    print(msg)
    return 1


if __name__ == "__main__":
    sys.exit(check())
