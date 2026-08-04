#!/usr/bin/env python3
"""
Gap audit for the broker_flow dataset.

Investigation (docs/audit/BROKER_FLOW_BACKFILL_REPORT.md, 2026-08-04) proved
the marketdetectors endpoint serves genuine historical broker data when both
`from` and `to` are supplied, verified back to at least 2020-01-02. This tool
audits broker_flow against the real IDX trading calendar (ohlcv) to find
exactly which trading dates are missing or only partially populated — per
this same repo's own precedent (STOCKBIT_FLOW_BACKFILL_FEASIBILITY.md /
REPORT.md for the sibling stockbit_flow dataset).

Read-only: never writes to any table.

Status per trade_date (expected is the EFFECTIVE expected count — the day's
ohlcv ticker universe minus confirmed-permanently-unsupported tickers, see
unsupported_tickers() below; not the raw ohlcv count):
    COMPLETE  actual ticker count >= effective expected count that day
    PARTIAL   actual > 0 but < effective expected
    MISSING   actual == 0 (and effective expected > 0)

Only real trading dates (present in ohlcv) are reported — weekends and
exchange holidays are never flagged as gaps. As of the 2026-08-04 freeze,
broker_flow backfill is COMPLETE at the maximum fidelity the Stockbit API
supports (see BROKER_FLOW_BACKFILL_REPORT.md) — this tool remains useful for
future drift detection, not because further backfill is expected.

Usage:
    venv/bin/python3 tools/check_broker_flow_coverage.py [--db PATH] [--json]
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
DEFAULT_DB = HERE / "data" / "walkforward.db"

# broker_flow was introduced in commit 6ac9aa1 (2026-04-23) — verified via
# git log -S"def fetch_broker_flow" plus a parent-commit diff check (the
# function is absent in 6ac9aa1^, present in 6ac9aa1). Dates before this were
# never expected to have coverage; the original audit wrongly used ohlcv's
# 2021-07-05 start as the baseline and inflated 1153 of 1220 dates as false
# gaps as a result (see docs/audit/BROKER_FLOW_BACKFILL_REPORT.md).
EXPECTED_COVERAGE_START = "2026-04-23"

# Minimum number of ohlcv-days a ticker must be observed on, with zero
# broker_flow rows every time, before it's classified as a permanent API
# limitation rather than coincidence/insufficient evidence. The real dataset's
# confirmed-unsupported tickers (92 of them, audited 2026-08-04 after the
# full backfill completed) all had >= 42 samples — this default sits well
# below that observed floor while staying far above small/incidental gaps.
UNSUPPORTED_MIN_SAMPLES = 20


def _connect(db_path):
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=30)
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def _expected_ticker_sets(conn):
    rows = conn.execute(
        "SELECT date, ticker FROM ohlcv WHERE date != '' AND date >= ?",
        (EXPECTED_COVERAGE_START,),
    ).fetchall()
    sets: dict[str, set] = {}
    for d, t in rows:
        sets.setdefault(d, set()).add(t)
    return sets


def _actual_counts(conn):
    rows = conn.execute(
        "SELECT trade_date, COUNT(DISTINCT ticker) FROM broker_flow "
        "WHERE trade_date != '' GROUP BY trade_date"
    ).fetchall()
    return {d: c for d, c in rows}


def unsupported_tickers(conn, since=EXPECTED_COVERAGE_START, min_samples=UNSUPPORTED_MIN_SAMPLES):
    """Tickers with ohlcv presence on at least `min_samples` distinct dates
    since `since`, with ZERO broker_flow rows across every one of them.

    This is a confirmed, evidence-based permanent API limitation, not a
    backfill gap: verified live (2026-08-04) against 7 such tickers on dates
    never previously queried — every one returned HTTP 200 with genuinely
    empty broker_summary arrays (suspended stocks, near-zero-liquidity
    small-caps, and the IHSG index symbol itself, which isn't a stock).
    `min_samples` guards against misclassifying a ticker from a handful of
    coincidentally-illiquid days or a new listing with little history yet —
    the real confirmed-unsupported set (92 tickers, audited 2026-08-04) all
    had >= 42 samples, well above the default threshold.
    """
    rows = conn.execute(
        """SELECT o.ticker, COUNT(DISTINCT o.date) ohlcv_days,
                  COUNT(DISTINCT bf.trade_date) broker_days
           FROM ohlcv o
           LEFT JOIN broker_flow bf
             ON bf.ticker = o.ticker AND bf.trade_date = o.date
           WHERE o.date >= ?
           GROUP BY o.ticker""",
        (since,),
    ).fetchall()
    return {t for t, ohlcv_days, broker_days in rows
            if broker_days == 0 and ohlcv_days >= min_samples}


def build_report(conn) -> list[dict]:
    """One row per real trading date (ohlcv-scoped): trade_date, expected,
    actual, status. Sorted ascending by trade_date.

    `expected` is the effective expected count: the day's ohlcv ticker
    universe minus any confirmed-unsupported tickers (see
    unsupported_tickers()) — a date is never reported PARTIAL/MISSING solely
    because of a ticker this API can never return data for.
    """
    expected_sets = _expected_ticker_sets(conn)
    actual = _actual_counts(conn)
    unsupported = unsupported_tickers(conn)

    report = []
    for trade_date in sorted(expected_sets):
        exp = len(expected_sets[trade_date] - unsupported)
        act = actual.get(trade_date, 0)
        if exp == 0:
            status = "COMPLETE"  # nothing achievable was ever missing
        elif act == 0:
            status = "MISSING"
        elif act < exp:
            status = "PARTIAL"
        else:
            status = "COMPLETE"
        report.append({
            "trade_date": trade_date,
            "expected": exp,
            "actual": act,
            "status": status,
        })
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    conn = _connect(args.db)
    try:
        report = build_report(conn)
    finally:
        conn.close()

    if args.json:
        print(json.dumps(report, indent=2))
        return

    n_complete = sum(1 for r in report if r["status"] == "COMPLETE")
    n_partial = sum(1 for r in report if r["status"] == "PARTIAL")
    n_missing = sum(1 for r in report if r["status"] == "MISSING")

    print(f"{'trade_date':<12} {'expected':>8} {'actual':>8}  status")
    for r in report:
        if r["status"] != "COMPLETE":
            print(f"{r['trade_date']:<12} {r['expected']:>8} {r['actual']:>8}  {r['status']}")
    print()
    print(f"Total trading dates: {len(report)}")
    print(f"  COMPLETE: {n_complete}")
    print(f"  PARTIAL:  {n_partial}")
    print(f"  MISSING:  {n_missing}")


if __name__ == "__main__":
    sys.exit(main())
