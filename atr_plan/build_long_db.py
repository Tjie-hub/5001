"""
Build data/history_long.db (table ohlcv_long) from data the repo ALREADY has, instead of
re-downloading from Yahoo.

  python atr_plan/build_long_db.py --pkl docs/research_programs/P-M/forward_volex/remeasure/work/hist_pre2021.pkl
  python atr_plan/build_long_db.py --pkl <pkl> --db-corpus data/walkforward.db      # + 2021-07-05.. from ohlcv (is_final=1)

hist_pre2021.pkl is ALREADY split-adjusted by Yahoo (checked: 187 of 197 pre-2021 splits show no
price jump in it). Do NOT apply split_hist.pkl to it. The DB corpus is also already adjusted
(data_gaps/README trap 1). So nothing here re-adjusts anything.

Zero-volume bars (19% of the pre-2021 rows) are dropped: they are stale prints, not tradeable bars.
"""
import argparse
import sqlite3
from pathlib import Path

import pandas as pd

CUT = pd.Timestamp("2021-07-05")
COLS = ["ticker", "date", "open", "high", "low", "close", "volume"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkl", required=True)
    ap.add_argument("--db-corpus", help="walkforward.db; adds ohlcv rows with is_final=1 from 2021-07-05")
    ap.add_argument("--out", default="data/history_long.db")
    a = ap.parse_args()

    H = pd.read_pickle(a.pkl)
    H["date"] = pd.to_datetime(H["date"])
    H = H[H["date"] < CUT][COLS]
    parts = [H]
    if a.db_corpus:
        con = sqlite3.connect(f"file:{a.db_corpus}?mode=ro", uri=True)
        D = pd.read_sql("SELECT ticker,date,open,high,low,close,volume FROM ohlcv WHERE is_final=1", con)
        con.close()
        D["date"] = pd.to_datetime(D["date"])
        D = D[(D["ticker"] != "IHSG") & (D["date"] >= CUT)][COLS]
        parts.append(D)
    O = pd.concat(parts, ignore_index=True).drop_duplicates(["ticker", "date"], keep="last")
    n0 = len(O)
    O = O[(O["volume"] > 0) & (O["close"] > 0) & (O["low"] > 0) & (O["high"] >= O["low"])]
    O = O.sort_values(["ticker", "date"])
    O["date"] = O["date"].dt.strftime("%Y-%m-%d")
    O["adj_close"] = O["close"]

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).unlink(missing_ok=True)
    con = sqlite3.connect(a.out)
    con.execute("CREATE TABLE ohlcv_long (ticker TEXT NOT NULL, date TEXT NOT NULL, open REAL, high REAL,"
                " low REAL, close REAL, adj_close REAL, volume REAL, PRIMARY KEY (ticker, date))")
    O[["ticker", "date", "open", "high", "low", "close", "adj_close", "volume"]].to_sql(
        "ohlcv_long", con, if_exists="append", index=False)
    con.commit()
    con.close()
    print(f"{len(O):,} bars kept of {n0:,} ({O.ticker.nunique()} tickers, "
          f"{O.date.min()} .. {O.date.max()}) -> {a.out}")


if __name__ == "__main__":
    main()
