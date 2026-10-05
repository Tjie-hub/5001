"""A-OPEN minute-bar leg (REVIEW_R2 §1) -- reviewer-run on XPS-13, read-only.

Compares the corpus daily `open` (production walkforward.db, yfinance-fed) with the 09:00
minute bar's `price` in the frozen Stockbit flow-bars v002 store (independent source), for the
60 highest median-traded-value names, 2025-01-02 -> 2026-04-27. The 09:00 bar price is the last
print of the first minute, not the auction print, so the test is BETWEEN GROUPS: if opens equal to
the previous close were fabricated, the independent first print on those days would sit a normal
gap away from the recorded open.
"""
import json, sqlite3
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[4]
db = sqlite3.connect(f"file:{ROOT/'data/walkforward.db'}?mode=ro", uri=True)
fb = sqlite3.connect(f"file:{ROOT/'data/frozen/stockbit-flow-bars-v002/stockbit-flow-bars-v002.db'}"
                     "?mode=ro&immutable=1", uri=True)
d = pd.read_sql("select ticker,date,open,close,volume from ohlcv "
                "where date>='2024-12-01' and date<='2026-04-27'", db)
d = d.sort_values(["ticker", "date"]); d["pc"] = d.groupby("ticker").close.shift()
d["tv"] = d.close * d.volume
top = d[d.date >= "2025-01-01"].groupby("ticker").tv.median().nlargest(60).index.tolist()
d = d[d.ticker.isin(top) & (d.date >= "2025-01-02") & (d.volume > 0)].dropna(subset=["pc"])
b = pd.concat([pd.read_sql("select trade_date date, price from stockbit_flow_bars "
                           "where ticker=? and bar_time='09:00'", fb, params=(t,)).assign(ticker=t)
               for t in top])
j = d.merge(b, on=["ticker", "date"], how="inner")
j["tk"] = np.select([j.pc < 200, j.pc < 500, j.pc < 2000, j.pc < 5000], [1, 2, 5, 10], 25)
j["stale"] = j.open == j.pc
j["dev"] = (j.price - j.open).abs() / j.tk
out = {"all": {"n": len(j), "stale_share_pct": round(100 * j.stale.mean(), 1),
               "tickers": j.ticker.nunique(), "sessions": j.date.nunique()}}
for s, g in j.groupby("stale"):
    out["stale" if s else "nonstale"] = {
        "n": len(g), "bar09_eq_open_pct": round(100 * (g.dev == 0).mean(), 1),
        "within_1tick_pct": round(100 * (g.dev <= 1).mean(), 1),
        "median_dev_ticks": float(g.dev.median()), "p90_dev_ticks": float(g.dev.quantile(.9))}
nst = j[~j.stale]
out["nonstale_median_abs_open_minus_pc_ticks"] = float(((nst.open - nst.pc).abs() / nst.tk).median())
Path(__file__).with_suffix(".json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
