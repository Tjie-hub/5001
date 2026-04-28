#!/usr/bin/env python3
"""
IDX Ticker Discovery
====================
Finds all valid .JK tickers via yfinance batch checks.
Run once (takes ~30-60 min) to populate data/idx_master.csv,
then refresh weekly/monthly to catch new listings.

Usage:
  python3 -m data.ticker_discovery              # full 4-letter scan
  python3 -m data.ticker_discovery --prefix BB  # only BB** tickers
  python3 -m data.ticker_discovery --recheck    # recheck existing idx_master.csv only
  python3 -m data.ticker_discovery --save-db    # also upsert into idx_tickers table
"""

import argparse
import csv
import itertools
import os
import string
import time
from datetime import datetime

import yfinance as yf

_HERE = os.path.dirname(os.path.abspath(__file__))
MASTER_CSV = os.path.join(_HERE, "idx_master.csv")
BATCH_SIZE = 100
PERIOD = "5d"
RATE_DELAY = 0.5


def _all_4letter(prefix=""):
    prefix = prefix.upper()
    remaining = 4 - len(prefix)
    if remaining < 0:
        return
    for combo in itertools.product(string.ascii_uppercase, repeat=remaining):
        yield prefix + "".join(combo)


def _check_batch(tickers: list) -> dict[str, bool]:
    """Returns {ticker: True/False} for whether .JK data exists."""
    symbols = [t + ".JK" for t in tickers]
    try:
        df = yf.download(
            symbols, period=PERIOD, auto_adjust=True,
            progress=False, threads=True
        )
        if df.empty:
            return {t: False for t in tickers}

        results = {}
        if len(symbols) == 1:
            has = not df.empty and df["Close"].notna().any().item() if hasattr(df["Close"].notna().any(), "item") else bool(df["Close"].notna().any())
            results[tickers[0]] = has
        else:
            # MultiIndex columns: ('Close', 'BBCA.JK') or ('BBCA.JK', 'Close')
            cols = df.columns
            if hasattr(cols, "levels"):
                level0 = [str(c) for c in cols.get_level_values(0)]
                level1 = [str(c) for c in cols.get_level_values(1)]
                # determine which level has the symbol
                if any(".JK" in v for v in level1):
                    sym_level = 1
                else:
                    sym_level = 0
                for t, sym in zip(tickers, symbols):
                    if sym_level == 1:
                        try:
                            has = df.xs(sym, axis=1, level=1)["Close"].notna().any()
                        except KeyError:
                            has = False
                    else:
                        try:
                            has = df[sym]["Close"].notna().any()
                        except KeyError:
                            has = False
                    results[t] = bool(has)
            else:
                for t in tickers:
                    results[t] = False
        return results
    except Exception:
        return {t: False for t in tickers}


def _batches(items, size):
    items = list(items)
    for i in range(0, len(items), size):
        yield items[i : i + size]


def load_master_csv() -> dict[str, dict]:
    """Load existing idx_master.csv into {ticker: row_dict}."""
    result = {}
    if not os.path.exists(MASTER_CSV):
        return result
    with open(MASTER_CSV, newline="") as f:
        for row in csv.DictReader(f):
            result[row["ticker"]] = row
    return result


def save_master_csv(records: dict[str, dict]):
    """Write records to idx_master.csv."""
    fieldnames = ["ticker", "status", "first_seen", "last_checked"]
    with open(MASTER_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for ticker in sorted(records):
            row = records[ticker]
            w.writerow({
                "ticker": ticker,
                "status": row.get("status", "active"),
                "first_seen": row.get("first_seen", ""),
                "last_checked": row.get("last_checked", ""),
            })
    print(f"Saved {len(records)} tickers to {MASTER_CSV}")


def upsert_to_db(records: dict[str, dict]):
    """Upsert active tickers into idx_tickers table."""
    from data.db import get_db
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS idx_tickers (
            ticker TEXT PRIMARY KEY,
            status TEXT DEFAULT 'active',
            first_seen TEXT,
            last_checked TEXT,
            last_fetch_date TEXT,
            last_fetch_status TEXT,
            fail_count INTEGER DEFAULT 0,
            in_idx30 INTEGER DEFAULT 0,
            in_lq45 INTEGER DEFAULT 0,
            in_idx80 INTEGER DEFAULT 0,
            updated_at TEXT
        )
    """)
    now = datetime.now().isoformat()
    for ticker, row in records.items():
        conn.execute("""
            INSERT INTO idx_tickers (ticker, status, first_seen, last_checked, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(ticker) DO UPDATE SET
                status=excluded.status,
                last_checked=excluded.last_checked,
                updated_at=excluded.updated_at
        """, (ticker, row.get("status", "active"), row.get("first_seen", ""), row.get("last_checked", ""), now))
    conn.commit()
    conn.close()
    active = sum(1 for r in records.values() if r.get("status") == "active")
    print(f"Upserted {active} active tickers into idx_tickers table")


def run_discovery(prefix="", recheck_only=False, save_db=False):
    today = datetime.now().strftime("%Y-%m-%d")
    existing = load_master_csv()

    if recheck_only:
        candidates = list(existing.keys())
        print(f"Rechecking {len(candidates)} known tickers...")
    else:
        candidates = list(_all_4letter(prefix))
        label = f"prefix={prefix!r}" if prefix else "full 4-letter"
        total = len(candidates)
        print(f"Discovery scan [{label}]: {total:,} candidates in batches of {BATCH_SIZE}")

    found = {}
    checked = 0
    start = time.time()

    for batch in _batches(candidates, BATCH_SIZE):
        results = _check_batch(batch)
        for ticker, has_data in results.items():
            if has_data:
                prior = existing.get(ticker, {})
                found[ticker] = {
                    "status": "active",
                    "first_seen": prior.get("first_seen") or today,
                    "last_checked": today,
                }
            elif ticker in existing and existing[ticker].get("status") == "active":
                # was active, now missing → mark delisted
                found[ticker] = {**existing[ticker], "status": "delisted", "last_checked": today}
        checked += len(batch)
        elapsed = time.time() - start
        rate = checked / elapsed
        remaining = (len(candidates) - checked) / rate if rate > 0 else 0
        print(f"  {checked:,}/{len(candidates):,} checked | {len(found)} found | ETA {remaining/60:.1f}m", end="\r")
        time.sleep(RATE_DELAY)

    print()

    # Merge: keep existing records not in this scan unchanged
    if not recheck_only:
        for ticker, row in existing.items():
            if ticker not in found:
                found[ticker] = row

    active_count = sum(1 for r in found.values() if r.get("status") == "active")
    print(f"\nResult: {active_count} active tickers found ({len(found)} total including delisted)")

    save_master_csv(found)
    if save_db:
        upsert_to_db(found)

    return found


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IDX ticker discovery via yfinance")
    parser.add_argument("--prefix", default="", help="Only scan tickers starting with this prefix (e.g. BB)")
    parser.add_argument("--recheck", action="store_true", help="Only recheck tickers already in idx_master.csv")
    parser.add_argument("--save-db", action="store_true", help="Also upsert results into idx_tickers DB table")
    args = parser.parse_args()

    run_discovery(prefix=args.prefix, recheck_only=args.recheck, save_db=args.save_db)
