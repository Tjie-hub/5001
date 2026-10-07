"""
Drift-free null test for the exit harness (replaces null_test.py as the neutrality gate).

Why: null_test.py builds a geometric random walk with zero LOG drift, so the PRICE drifts up by
sigma^2/2 per day (~8%/yr at 2.5% daily vol). Per-trade net then rewards long holds, and
momentum C (13 bars) beats A (3 bars) by +0.44%/trade with CI > 0 on pure noise.
Here log increments have mean -sigma^2/2, so price is a martingale and any exit rule has
E[net] = -cost. A neutral harness must show CI straddling 0 for every B/C vs A (ohlc mode).

  python atr_plan/null_test_martingale.py            # seed 3
  python atr_plan/null_test_martingale.py 11         # another seed
"""
import sqlite3
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "data" / "null_test_mg.db"


def build(seed=3, n_tickers=25, steps=26):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2012-01-02", "2026-09-23")
    n = len(dates)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.unlink(missing_ok=True)
    con = sqlite3.connect(OUT)
    con.execute("CREATE TABLE ohlcv_long (ticker TEXT, date TEXT, open REAL, high REAL, low REAL,"
                " close REAL, adj_close REAL, volume REAL)")
    for k in range(n_tickers):
        p0 = rng.choice([900, 3000, 8000])
        vol = rng.uniform(0.015, 0.035)
        sg, ss = vol * 0.3, vol * 0.95 / np.sqrt(steps)
        gap = rng.normal(-sg ** 2 / 2, sg, n)                 # martingale correction
        step = rng.normal(-ss ** 2 / 2, ss, (n, steps))       # martingale correction
        logp, rows = np.log(p0), []
        for i in range(n):
            o = logp + gap[i]
            path = o + np.cumsum(step[i])
            hi, lo, c = max(o, path.max()), min(o, path.min()), path[-1]
            logp = c
            v = rng.lognormal(np.log(2e10 / p0), 0.5)
            rows.append((f"NULL{k:02d}", dates[i].strftime("%Y-%m-%d"),
                         *np.exp([o, hi, lo, c, c]), v))
        con.executemany("INSERT INTO ohlcv_long VALUES (?,?,?,?,?,?,?,?)", rows)
    con.commit()
    con.close()


if __name__ == "__main__":
    build(seed=int(sys.argv[1]) if len(sys.argv) > 1 else 3)
    sys.exit(subprocess.call([sys.executable, str(HERE / "exit_compare.py"), "--db", str(OUT),
                              "--out", str(HERE.parent / "reports" / "null_test_mg")]))
