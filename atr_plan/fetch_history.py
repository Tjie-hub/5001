"""
Step 1 — Extend price history to 2010+ into a SEPARATE db (does not touch walkforward.db).

Stores per bar:
  open/high/low/close  = yfinance raw (split-adjusted, NOT dividend-adjusted)
  adj_close            = split + dividend adjusted
Signals/ATR should use open/high/low/close. adj_close is kept for total-return checks.

Usage (on the Ubuntu box, inside the repo):
  python atr_plan/fetch_history.py --from-db data/walkforward.db
  python atr_plan/fetch_history.py --tickers-file tickers.txt --start 2010-01-01
  python atr_plan/fetch_history.py --from-db data/walkforward.db --update   # incremental
"""
import argparse
import sqlite3
import sys
import time
from pathlib import Path

import pandas as pd

OUT_DB_DEFAULT = "data/history_long.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS ohlcv_long (
    ticker TEXT NOT NULL,
    date   TEXT NOT NULL,
    open REAL, high REAL, low REAL, close REAL,
    adj_close REAL, volume REAL,
    PRIMARY KEY (ticker, date)
);
CREATE TABLE IF NOT EXISTS fetch_log (
    ticker TEXT PRIMARY KEY, first_date TEXT, last_date TEXT, n_bars INTEGER,
    fetched_at TEXT, note TEXT
);
"""


def tickers_from_db(db_path: str) -> list[str]:
    """Find a ticker list in walkforward.db without knowing its schema:
    scan every table for a 'ticker'/'symbol'/'kode' column and take the largest distinct set."""
    con = sqlite3.connect(db_path)
    best: set[str] = set()
    for (tbl,) in con.execute("SELECT name FROM sqlite_master WHERE type='table'"):
        cols = [r[1] for r in con.execute(f"PRAGMA table_info('{tbl}')")]
        for c in cols:
            if c.lower() in ("ticker", "symbol", "kode", "code", "stock"):
                vals = {r[0] for r in con.execute(f"SELECT DISTINCT \"{c}\" FROM \"{tbl}\"") if r[0]}
                if len(vals) > len(best):
                    best = vals
    con.close()
    out = sorted({str(t).upper().replace(".JK", "") for t in best})
    return out


def normalize(t: str) -> str:
    t = t.strip().upper()
    return t if t.endswith(".JK") or t.startswith("^") else f"{t}.JK"


def fetch_one(yf, ticker: str, start: str) -> pd.DataFrame:
    d = yf.download(ticker, start=start, auto_adjust=False, actions=False,
                    progress=False, threads=False)
    if d is None or d.empty:
        return pd.DataFrame()
    if isinstance(d.columns, pd.MultiIndex):
        d.columns = d.columns.get_level_values(0)
    d = d.rename(columns=str.lower).rename(columns={"adj close": "adj_close"})
    d = d[["open", "high", "low", "close", "adj_close", "volume"]].dropna(subset=["close"])
    # drop zero-volume stale bars (suspension / holidays echoed by Yahoo)
    d = d[(d["volume"] > 0) & (d["high"] >= d["low"])]
    d.index = pd.to_datetime(d.index).strftime("%Y-%m-%d")
    d.index.name = "date"
    return d


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--from-db", help="walkforward.db to read ticker list from")
    g.add_argument("--tickers-file", help="one ticker per line (BBCA or BBCA.JK)")
    ap.add_argument("--out", default=OUT_DB_DEFAULT)
    ap.add_argument("--start", default="2010-01-01")
    ap.add_argument("--update", action="store_true", help="only fetch after last stored date")
    ap.add_argument("--sleep", type=float, default=0.7, help="seconds between tickers")
    a = ap.parse_args()

    import yfinance as yf

    if a.from_db:
        tickers = tickers_from_db(a.from_db)
        if not tickers:
            sys.exit("No ticker column found in db; use --tickers-file")
    else:
        tickers = [l.strip() for l in Path(a.tickers_file).read_text().splitlines() if l.strip()]
    tickers = [normalize(t) for t in tickers]
    if "^JKSE" not in tickers:
        tickers.append("^JKSE")  # benchmark / regime
    print(f"{len(tickers)} tickers -> {a.out}")

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(a.out)
    con.executescript(SCHEMA)

    ok, fail = 0, []
    for i, t in enumerate(tickers, 1):
        start = a.start
        if a.update:
            r = con.execute("SELECT MAX(date) FROM ohlcv_long WHERE ticker=?", (t,)).fetchone()
            if r and r[0]:
                start = r[0]
        try:
            d = fetch_one(yf, t, start)
        except Exception as e:  # noqa: BLE001
            fail.append((t, str(e)[:80]))
            continue
        if d.empty:
            fail.append((t, "empty"))
            continue
        rows = [(t, idx, *map(float, row)) for idx, row in d.iterrows()]
        con.executemany("INSERT OR REPLACE INTO ohlcv_long VALUES (?,?,?,?,?,?,?,?)", rows)
        con.execute("INSERT OR REPLACE INTO fetch_log VALUES (?,?,?,?,datetime('now'),?)",
                    (t, d.index.min(), d.index.max(), len(d), "update" if a.update else "full"))
        con.commit()
        ok += 1
        print(f"[{i:>3}/{len(tickers)}] {t:<10} {d.index.min()} .. {d.index.max()}  {len(d):>5} bars")
        time.sleep(a.sleep)

    con.close()
    print(f"\nDone: {ok} ok, {len(fail)} failed")
    for t, why in fail:
        print(f"  FAIL {t}: {why}")


if __name__ == "__main__":
    main()
