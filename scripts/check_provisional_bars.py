#!/usr/bin/env python3
"""Dead-man's-switch for OHLCV finalisation (2026-09-16).

`screener/idx_scraper.save_ohlcv_to_db` writes PROVISIONAL bars (is_final=0)
on intraday runs and FINAL bars (is_final=1) on the 16:15 EOD run. When that
EOD run does not complete, the intraday bars stay provisional forever —
nothing re-finalises a past session, and `data/fetcher.py` cannot heal them
(its upsert carries `WHERE ohlcv.close IS NULL` so yfinance never clobbers an
authoritative scraper bar).

Every research query filters `is_final=1`, so a stranded session is INVISIBLE
to research rather than obviously broken. On 2026-09-16 five such sessions
were found — 2026-07-08, 07-09, 07-24, 08-20, 09-07 — the worst showing 137 of
915 tickers, and 63% of the stranded bars carried a materially wrong close
(they were mid-session snapshots). None had ever raised an alert, because
cron_wrap.sh only alerts on a job that fired and FAILED, and the EOD run
exited successfully after finalising ~135 of ~915 tickers.

This checks two distinct failures the repair left no guard against:
  STRANDED — a past session still holding is_final=0 bars.
  THIN     — a past session whose finalised-row count is far below the norm,
             which is how 2026-07-09 (137 rows total) presents: not stranded,
             simply never fetched.

Fix a STRANDED session with:  scripts/repair_provisional_bars.py --apply

Run daily from crontab (the EOD scraper runs every weekday, so a daily check
catches a gap within one session):
    0 9 * * * cd "<repo>" && venv/bin/python3 scripts/check_provisional_bars.py
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.db import connect as db_connect  # noqa: E402
from utils.telegram import send_telegram  # noqa: E402

WIB = ZoneInfo("Asia/Jakarta")
# Today's bars are legitimately provisional; yesterday's may still be mid-EOD
# if this runs before the 16:15 scraper. Two days is unambiguous.
GRACE_DAYS = 2
# A finalised-row count below this share of the trailing norm is a thin session.
THIN_FRAC = 0.80
# Sessions to establish the norm from.
NORM_WINDOW = 20
LOOKBACK_DAYS = 120


def main() -> int:
    conn = db_connect(read_only=True)
    today = datetime.now(WIB).date()
    cutoff = (today - timedelta(days=GRACE_DAYS)).strftime("%Y-%m-%d")
    since = (today - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")

    rows = conn.execute(
        "SELECT date, "
        "  SUM(CASE WHEN is_final=1 THEN 1 ELSE 0 END), "
        "  SUM(CASE WHEN COALESCE(is_final,1)<>1 THEN 1 ELSE 0 END) "
        "FROM ohlcv WHERE date >= ? GROUP BY date ORDER BY date", (since,)).fetchall()
    if not rows:
        print("no sessions in lookback window — nothing to check")
        return 0

    finals = [f for _, f, _ in rows]
    finals_sorted = sorted(finals[-NORM_WINDOW:])
    norm = finals_sorted[len(finals_sorted) // 2] or 0

    stranded = [(d, f, p) for d, f, p in rows if d <= cutoff and p > 0]
    thin = [(d, f, p) for d, f, p in rows
            if d <= cutoff and p == 0 and norm and f < THIN_FRAC * norm]

    print(f"checked {len(rows)} sessions since {since} "
          f"(norm = {norm} finalised rows/session, grace = {GRACE_DAYS} days)")

    if not stranded and not thin:
        print("OK — every settled session is fully finalised")
        return 0

    lines = ["⚠️ OHLCV finalisation gap"]
    if stranded:
        lines.append(f"\n{len(stranded)} session(s) STRANDED with provisional bars "
                     f"(invisible to every is_final=1 query):")
        for d, f, p in stranded[-10:]:
            lines.append(f"  {d}: {f} final, {p} provisional")
        lines.append("Fix: scripts/repair_provisional_bars.py --apply")
    if thin:
        lines.append(f"\n{len(thin)} session(s) THIN — finalised rows far below "
                     f"the {norm}-row norm (bars never fetched at all):")
        for d, f, p in thin[-10:]:
            lines.append(f"  {d}: {f} final ({100*f/max(norm,1):.0f}% of norm)")

    msg = "\n".join(lines)
    print(msg)
    try:
        send_telegram(msg)
    except Exception as e:  # alerting must not mask the finding
        print(f"[warn] telegram alert failed: {e}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
