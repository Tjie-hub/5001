#!/usr/bin/env python3
"""PEAD G0 data: Yahoo earnings dates for the point-in-time universe (EPS + dates only).

Closes the survivorship gap in the 2026-10-15 fetch (`~/scratch/pead_g0/fetch_earnings_dates.py`), which
covered only the 274 names liquid in 2025-26. The universe here is every ticker that ranked in the top 200 by
KSEI month-end market cap (listed shares x price, all listed equities including later-delisted ones) at any
month-end 2009-03 .. 2026-09. Names already in the 10-15 file are copied over unchanged, not re-fetched, so the
10-15 rows stay byte-for-byte what was fetched then.

No price, return, signal or outcome is read or computed here. Writes only data/earnings_dates_pit.json and
data/fetch_pit.log in this directory. Yahoo only; nothing from Stockbit.

    venv/bin/python3 docs/research_programs/P-M/pead/fetch_earnings_pit.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "data" / "earnings_dates_pit.json"
SEED = Path.home() / "scratch" / "pead_g0" / "earnings_dates.json"     # the 2026-10-15 fetch
KSEI = HERE / "data" / "ksei_mcap_2009_2026.csv"
TOP_N = 200


# Ran 2026-10-23 on this unfiltered ranking (628 tickers). The G0 later drops KSEI month-rows worth > 25% of the
# month total (BCIC 2010-17 share-count error); that filtered top-200 universe is a subset of the fetched set
# (0 tickers missing, checked 2026-10-23), so no re-fetch was needed.
def pit_universe(ksei_csv: Path = KSEI, top_n: int = TOP_N) -> list[str]:
    k = pd.read_csv(ksei_csv, usecols=["date", "ticker", "sec_num", "price"])
    k["mcap"] = k["sec_num"] * k["price"]
    k["rk"] = k.groupby("date")["mcap"].rank(ascending=False, method="first")
    return sorted(set(k.loc[k["rk"] <= top_n, "ticker"]))


def rows_from_frame(e) -> list[dict]:
    if e is None or e.empty:
        return []
    nan = lambda v: v != v  # noqa: E731
    return [{"ts": str(ix),
             "est": None if nan(r["EPS Estimate"]) else float(r["EPS Estimate"]),
             "rep": None if nan(r["Reported EPS"]) else float(r["Reported EPS"])}
            for ix, r in e.iterrows()]


def main() -> int:
    import yfinance as yf
    OUT.parent.mkdir(exist_ok=True)
    seed = json.loads(SEED.read_text())
    done = json.loads(OUT.read_text()) if OUT.exists() else {}
    for t, v in seed.items():
        done.setdefault(t, v)
    uni = pit_universe()
    todo = [t for t in uni if t not in done]
    print(f"PIT universe {len(uni)}; seeded {len(seed)}; to fetch {len(todo)}", flush=True)
    for i, t in enumerate(todo):
        try:
            done[t] = rows_from_frame(yf.Ticker(t + ".JK").get_earnings_dates(limit=60))
        except Exception as ex:                       # delisted names usually land here or as []
            done[t] = {"error": ex.__class__.__name__}
        if i % 25 == 0:
            OUT.write_text(json.dumps(done, sort_keys=True))
            print(i, t, flush=True)
        time.sleep(1.0)
    OUT.write_text(json.dumps(done, sort_keys=True))
    print("done", len(done), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
