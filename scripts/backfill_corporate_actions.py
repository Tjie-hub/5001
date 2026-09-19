"""Reconcile `corporate_actions` against the full per-ticker action history.

`data/fetcher.py::_save_actions` can only capture actions that land on a row of
the fetched OHLCV frame, so any dividend or split whose ex-date has no saved bar
is invisible to it. This script queries each ticker's complete action history
directly and inserts anything absent.

Measured 2026-09-19: 52 events absent within the table's coverage window, all
dated 2026 and consistent with fetch lag; 4 of them had no OHLCV bar on the
ex-date and were therefore structurally uncapturable by the normal path.

Idempotent (INSERT OR IGNORE on the natural key). Reference data only.

    venv/bin/python scripts/backfill_corporate_actions.py [--dry-run] [--limit N]
"""
import argparse
import logging
import sys
import time

sys.path.insert(0, ".")

from config import DB_PATH
from data.db import connect as db_connect
from data.market_schema import ensure_market_data_schema


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--sleep", type=float, default=0.2)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    import pandas as pd
    import yfinance as yf

    ensure_market_data_schema(DB_PATH)
    conn = db_connect(DB_PATH, timeout=30)
    try:
        tickers = [r[0] for r in conn.execute(
            "SELECT DISTINCT ticker FROM ohlcv WHERE ticker != 'IHSG' ORDER BY ticker"
        )][: a.limit]
        have = {(t, d, act) for t, d, act in conn.execute(
            "SELECT ticker, date, action FROM corporate_actions")}
        lo = conn.execute("SELECT MIN(date) FROM ohlcv WHERE is_final=1").fetchone()[0]
        logging.info("reconciling %d tickers against coverage window from %s", len(tickers), lo)

        added = failed = 0
        for i, t in enumerate(tickers, 1):
            try:
                y = yf.Ticker(f"{t}.JK")
                for series, action in ((y.dividends, "dividend"), (y.splits, "split")):
                    if series is None or not len(series):
                        continue
                    idx = pd.to_datetime(series.index).tz_localize(None)
                    for dt, val in zip(idx, series.values):
                        d = dt.strftime("%Y-%m-%d")
                        if d < lo or float(val) == 0.0:
                            continue
                        if (t, d, action) in have:
                            continue
                        if not a.dry_run:
                            conn.execute(
                                "INSERT OR IGNORE INTO corporate_actions"
                                " (ticker,date,action,value,source)"
                                " VALUES (?,?,?,?,'yfinance-backfill')",
                                (t, d, action, float(val)))
                        added += 1
                        logging.info("  + %s %s %s %.4f", t, d, action, float(val))
            except Exception as e:
                failed += 1
                logging.warning("[backfill] %s: %s", t, e)
            if i % 100 == 0:
                if not a.dry_run:
                    conn.commit()
                logging.info("  %d/%d added=%d failed=%d", i, len(tickers), added, failed)
            time.sleep(a.sleep)
        if not a.dry_run:
            conn.commit()
        logging.info("DONE added=%d failed=%d%s", added, failed,
                     " (dry run, nothing written)" if a.dry_run else "")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
