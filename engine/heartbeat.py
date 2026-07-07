"""Scheduler dead-man's-switch core (audit item 3.7).

The in-app writer stamps ``logs/scheduler_heartbeat.txt`` every 5 minutes; an
external watchdog (scripts/check_scheduler_heartbeat.py, run from crontab)
reads it and alarms when stale. This module is the pure, side-effect-light
core shared by both — no Telegram, no scheduler imports.
"""
from datetime import datetime
from pathlib import Path


def heartbeat_status(last_iso, now_dt, stale_after_min=15):
    """Classify heartbeat freshness → 'FRESH' | 'STALE' | 'MISSING'.

    MISSING: no/unparseable timestamp. STALE: older than stale_after_min.
    The threshold boundary counts as FRESH (only strictly-older is STALE).
    """
    if not last_iso:
        return "MISSING"
    try:
        last = datetime.fromisoformat(last_iso)
    except (ValueError, TypeError):
        return "MISSING"
    age_min = (now_dt - last).total_seconds() / 60.0
    return "STALE" if age_min > stale_after_min else "FRESH"


def write_heartbeat(path, now_dt):
    """Atomically stamp the heartbeat file with an ISO-8601 timestamp."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(now_dt.isoformat(), encoding="utf-8")
    tmp.replace(p)  # atomic on POSIX


def read_heartbeat(path):
    """Return the stored ISO string, or None if the file is absent/empty."""
    try:
        txt = Path(path).read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    return txt or None
