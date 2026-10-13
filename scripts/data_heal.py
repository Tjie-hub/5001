#!/usr/bin/env python3
"""Nightly data self-heal (2026-10-13).

A failed data job (token expiry, vendor outage, a crashed cron) used to mean a
human had to audit every table and re-run the backfills by hand. This finds gaps
in the last few trading sessions, re-runs the EXISTING idempotent backfill tools
for just those, and says something only when there was something to fix:

  * 1-minute flow bars  -> tools/backfill_flow_bars.py      (per-cell, resumable)
  * broker flow         -> tools/backfill_broker_flow_gap.py (PARTIAL/MISSING dates)

Both tools only fetch missing cells and never overwrite a complete one, so a
re-run is always safe. Rows they add keep their own fetch-time `updated_at`, so
late-filled days stay identifiable to research.

Runs 22:45 Mon-Fri, after the 18:00-22:30 window where bulk vendor calls are
avoided (idx-data-heal.timer). Clean night = silence. Gaps older than the window
are NOT touched here (that is a deliberate, owner-run backfill).
"""
import datetime
import logging
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

logger = logging.getLogger("data_heal")

WINDOW_DAYS = 5
BARS_BUDGET_S = 2400          # flow-bars tool wall clock (its own clamp is 5h)
BROKER_TIMEOUT_S = 1200
MAX_BROKER_DATES = 2          # oldest first; the rest wait for the next night
# The broker feed is chronically PARTIAL: 58 of the last 60 sessions (2026-10)
# return only ~72-95% of the expected tickers (vendor empty replies), which is
# normal, not an outage. Treating that as a gap would alert nightly forever and
# burn a 20-minute vendor backfill every time -- only an outage-sized hole counts.
BROKER_MIN_RATIO = 0.5


def is_broker_gap(row, min_ratio: float = BROKER_MIN_RATIO) -> bool:
    if row["status"] == "COMPLETE":
        return False
    if row["status"] == "MISSING" or not row["expected"]:
        return row["status"] == "MISSING"
    return row["actual"] / row["expected"] < min_ratio


def recent_dates(conn, n: int = WINDOW_DAYS) -> list:
    rows = conn.execute("SELECT DISTINCT date FROM ohlcv WHERE date != '' "
                        "ORDER BY date DESC LIMIT ?", (n,)).fetchall()
    return sorted(r[0] for r in rows)


def _find_gaps(conn, dates):
    """{"bars": {date: n_incomplete_cells}, "broker": {date: PARTIAL|MISSING}}"""
    from stockbit_fetcher import get_tickers
    from tools.flow_bars_gap import missing_bars_cells
    from tools.check_broker_flow_coverage import build_report
    tickers = get_tickers("ALL")
    bars = {d: len(missing_bars_cells(conn, d, tickers)) for d in dates}
    broker = {r["trade_date"]: (r["status"] if r["status"] == "MISSING" else
                                f"PARTIAL {round(100 * r['actual'] / r['expected'])}%")
              for r in build_report(conn)
              if r["trade_date"] in dates and is_broker_gap(r)}
    return {"bars": {d: n for d, n in bars.items() if n}, "broker": broker}


def _run_tool(argv, timeout):
    try:
        return subprocess.run(argv, cwd=ROOT, timeout=timeout,
                              capture_output=True, text=True).returncode
    except subprocess.TimeoutExpired:
        logger.warning("tool timed out after %ss: %s", timeout, argv[1:3])
        return 124


def _ensure_token():
    from stockbit_fetcher import ensure_valid_token
    return ensure_valid_token()


def _day_after(d: str) -> str:
    return (datetime.date.fromisoformat(d) + datetime.timedelta(days=1)).isoformat()


def _fmt(g) -> str:
    parts = []
    if g["bars"]:
        parts.append("1-min flow: " + ", ".join(f"{d} ({n} tickers)" for d, n in sorted(g["bars"].items())))
    if g["broker"]:
        parts.append("broker flow: " + ", ".join(f"{d} ({s})" for d, s in sorted(g["broker"].items())))
    return "; ".join(parts)


def heal(conn, dates=None, gaps_fn=_find_gaps, run_tool=_run_tool, ensure_token=_ensure_token,
         send=None, max_broker_dates=MAX_BROKER_DATES) -> int:
    if send is None:
        from utils.telegram import send_telegram as send
    dates = dates if dates is not None else recent_dates(conn)
    before = gaps_fn(conn, dates)
    if not before["bars"] and not before["broker"]:
        logger.info("no gaps in %s..%s", dates[:1], dates[-1:])
        return 0
    logger.info("gaps found: %s", _fmt(before))

    if not ensure_token():
        send(f"🔴 DATA HEAL: found gaps ({_fmt(before)}) but cannot repair them: no valid "
             f"Stockbit token and the automatic login failed. Refresh the token; the next "
             f"22:45 run repairs them.", event="data.heal_failed", subject="token")
        return 0

    py = sys.executable
    if before["bars"]:
        first, last = min(before["bars"]), max(before["bars"])
        rc = run_tool([py, "tools/backfill_flow_bars.py", "--date-from", first,
                       "--date-to", _day_after(last), "--budget-s", str(BARS_BUDGET_S)],
                      BARS_BUDGET_S + 600)
        logger.info("backfill_flow_bars rc=%s", rc)
    if before["broker"]:
        todo = sorted(before["broker"])[:max_broker_dates]
        rc = run_tool([py, "tools/backfill_broker_flow_gap.py", "--dates", ",".join(todo)],
                      BROKER_TIMEOUT_S)
        logger.info("backfill_broker_flow_gap rc=%s", rc)

    after = gaps_fn(conn, dates)
    if not after["bars"] and not after["broker"]:
        send(f"🟢 DATA HEAL: repaired {_fmt(before)}.", event="data.heal_repaired", subject="ok")
    else:
        send(f"🟠 DATA HEAL: found {_fmt(before)}. Still missing: {_fmt(after)}. It retries "
             f"tomorrow night; if it persists, check the token and the vendor.",
             event="data.heal_failed", subject="remaining")
    return 0


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    from config import DB_PATH
    from data.db import connect
    conn = connect(str(DB_PATH))
    try:
        return heal(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
