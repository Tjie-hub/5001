#!/usr/bin/env python3
"""Telegram recovery alert for the internet watcher (~/watch.sh).

    net_alert.py <internet|dns> <down_epoch> <up_epoch> "<verdict>"

Called by watch.sh once a link/DNS outage has ended. It is a recovery summary
on purpose: while the link is down Telegram is unreachable, so a "went down"
message could not be delivered anyway. Outages shorter than NET_ALERT_MIN_S are
dropped (a 6-second blip is not worth a message).

The watcher guarantees one call per outage, so the event is RULE_NONE and is in
notify_policy.BLACKOUT_EXEMPT — TELEGRAM_OFF must not hide an outage report.
"""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# config.py is the single .env reader (it load_dotenv()s on import). cron jobs get
# TELEGRAM_* from scripts/cron_wrap.sh, but ~/watch.sh calls this script directly.
import config  # noqa: E402,F401
from utils.telegram import send_telegram  # noqa: E402

WIB = timezone(timedelta(hours=7))
MIN_S = 60


def fmt_duration(s: int) -> str:
    s = int(s)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h}h{m:02d}m{sec:02d}s"
    if m:
        return f"{m}m{sec:02d}s"
    return f"{sec}s"


def _hms(epoch: int) -> str:
    return datetime.fromtimestamp(int(epoch), WIB).strftime("%H:%M:%S")


def alert(kind, down, up, verdict, min_s=MIN_S, send=send_telegram) -> int:
    """Return 0 if sent or intentionally skipped, 1 if the send raised."""
    dur = int(up) - int(down)
    if dur < min_s:
        return 0
    label = "DNS" if kind == "dns" else "INTERNET"
    msg = (f"🟠 {label} outage ended — down {_hms(down)} → {_hms(up)} WIB "
           f"({fmt_duration(dur)}).\nCause: {verdict or 'not diagnosed'}")
    try:
        delivered = send(msg, event="system.net_outage", subject=kind)
    except Exception as e:  # the watcher log already holds the full record
        print(f"net_alert: send failed: {e}", file=sys.stderr)
        return 1
    # send_telegram() returns False (not raises) when suppressed or unconfigured;
    # don't let the log claim a delivery that never happened.
    if delivered is False:
        print(f"net_alert: NOT delivered (suppressed/unconfigured/failed): {msg!r}", file=sys.stderr)
        return 1
    print(f"net_alert: sent: {msg!r}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit("usage: net_alert.py <internet|dns> <down_epoch> <up_epoch> [verdict]")
    sys.exit(alert(sys.argv[1], sys.argv[2], sys.argv[3],
                   sys.argv[4] if len(sys.argv) > 4 else "",
                   min_s=int(os.environ.get("NET_ALERT_MIN_S", MIN_S))))
