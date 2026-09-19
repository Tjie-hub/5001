"""Populate `ticker_sector` from the market-data source.

Why this exists: before 2026-09-19 the repository had no usable sector map --
`candidate_watchlist_snapshot.sector` was 100% NULL and
`engine/sector_rotation.py` covered 82 of 959 tickers. Sector concentration was
therefore the largest untestable confound in P-M research, and when it finally
was tested it cut the best candidate's t-statistic from 2.29 to 1.03.

Idempotent: re-running refreshes labels in place. Reference data only -- no
research table is touched, so this stays clear of the write fence.

    venv/bin/python scripts/backfill_ticker_sector.py [--limit N] [--dry-run]
"""
import argparse
import logging
import sys
import time

sys.path.insert(0, ".")

from data.db import connect as db_connect
from data.market_schema import ensure_market_data_schema
from config import DB_PATH


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sleep", type=float, default=0.2)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    import yfinance as yf

    ensure_market_data_schema(DB_PATH)
    conn = db_connect(DB_PATH, timeout=30)
    try:
        rows = conn.execute(
            "SELECT DISTINCT ticker FROM ohlcv WHERE ticker != 'IHSG' ORDER BY ticker"
        ).fetchall()
        tickers = [r[0] for r in rows][: a.limit]
        logging.info("resolving sector for %d tickers", len(tickers))
        ok = miss = fail = 0
        for i, t in enumerate(tickers, 1):
            try:
                info = yf.Ticker(f"{t}.JK").info
                sec, ind = info.get("sector"), info.get("industry")
                if not sec:
                    miss += 1
                else:
                    ok += 1
                if not a.dry_run:
                    conn.execute(
                        "INSERT INTO ticker_sector (ticker,sector,industry,source,updated_at)"
                        " VALUES (?,?,?,'yfinance',CURRENT_TIMESTAMP)"
                        " ON CONFLICT(ticker) DO UPDATE SET"
                        " sector=excluded.sector, industry=excluded.industry,"
                        " source=excluded.source, updated_at=CURRENT_TIMESTAMP",
                        (t, sec, ind),
                    )
            except Exception as e:
                fail += 1
                logging.warning("[sector] %s: %s", t, e)
            if i % 100 == 0:
                if not a.dry_run:
                    conn.commit()
                logging.info("  %d/%d ok=%d miss=%d fail=%d", i, len(tickers), ok, miss, fail)
            time.sleep(a.sleep)
        if not a.dry_run:
            conn.commit()
        logging.info("DONE labelled=%d unlabelled=%d failed=%d", ok, miss, fail)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
