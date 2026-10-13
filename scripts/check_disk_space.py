#!/usr/bin/env python3
"""Hourly disk-space guard (2026-10-13).

On 2026-10-10..12 the SSD was at 99% and three nightly backups failed with
"database or disk is full" before anyone noticed. This warns early instead:
85% used -> warning, 90% -> critical, each at most once per day per mount
(the dedup subject carries the level, so a warning never mutes the critical).
system.disk_low is exempt from the TELEGRAM_OFF blackout.

Run hourly via deploy/systemd/idx-disk-guard.timer through cron_wrap.sh.
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.telegram import send_telegram  # noqa: E402

WARN_PCT = 85
CRIT_PCT = 90
GB = 1024 ** 3


def check(paths=("/",), warn=WARN_PCT, crit=CRIT_PCT,
          usage_fn=shutil.disk_usage, send=send_telegram):
    """Return 0 normally, 1 if a path could not be read (that is reported too)."""
    rc = 0
    for path in paths:
        try:
            u = usage_fn(path)
        except OSError as e:
            rc = 1
            send(f"🔴 DISK GUARD: cannot read usage of {path}: {e}",
                 event="system.disk_low", subject=f"{path}:unreadable")
            continue
        pct = round(100 * u.used / u.total)
        if pct < warn:
            continue
        level = "critical" if pct >= crit else "warn"
        icon = "🔴 CRITICAL" if level == "critical" else "🟠 WARNING"
        send(f"{icon} DISK {path} is {pct}% used, {u.free / GB:.1f} GB free "
             f"(nightly backup needs ~19 GB free).",
             event="system.disk_low", subject=f"{path}:{level}")
    return rc


if __name__ == "__main__":
    sys.exit(check())
