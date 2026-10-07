"""
Harness neutrality check (run BEFORE trusting real results).

Builds pure random-walk data (zero drift, real intraday paths -> honest high/low) and runs
exit_compare on it. A neutral harness should show mean Δ/trade ≈ 0 for B/C vs A under
same-bar = ohlc (CI straddling 0). stop_first is expected to favour wide stops (it's pessimistic).

  python atr_plan/null_test.py
"""
import sqlite3
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "data" / "null_test.db"


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
        gap = rng.normal(0, vol * 0.3, n)
        step = rng.normal(0, vol * 0.95 / np.sqrt(steps), (n, steps))
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
    build()
    sys.exit(subprocess.call([sys.executable, str(HERE / "exit_compare.py"), "--db", str(OUT),
                              "--out", str(HERE.parent / "reports" / "null_test")]))
