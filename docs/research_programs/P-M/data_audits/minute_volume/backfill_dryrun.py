"""3-day backfill dry run (Task B) — READ-ONLY, stores NOTHING.

Question: can fetch_flow(date=...) recover the post-2026-07-10 volume gap in
stockbit_flow_bars? For 3 affected dates and 4 liquid names, fetch the
HISTORICAL payload (date param) and compare its cumulative buy+sell lots
against (a) the stored bars rows (written by the 18:30 live cron) and
(b) ohlcv volume. Prints NO token, writes nothing to any DB.

Run: venv/bin/python docs/research_programs/P-M/data_audits/minute_volume/backfill_dryrun.py
"""
from __future__ import annotations

import json
import sqlite3
import sys
import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
SNAP = "/home/tjiesar/scratch/g0_snapshots_2026-10-08/walkforward_snapshot_2026-10-08.db"
TOKEN_FILE = Path("/home/tjiesar/idx-walkforward-5001/.stockbit_token")
BASE = "https://exodus.stockbit.com"
DATES = ["2026-07-14", "2026-08-24", "2026-10-06"]
TICKERS = ["BBCA", "TLKM", "BMRI", "ACES"]


def fetch_flow(token: str, ticker: str, date: str):
    assert BASE.startswith("https://exodus.stockbit.com"), "host pinned"
    r = requests.get(
        f"{BASE}/order-trade/trade-book/chart",
        params={"symbol": ticker, "time_interval": "1m", "date": date},
        headers={"Authorization": f"Bearer {token}",
                 "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                 "Origin": "https://stockbit.com", "Referer": "https://stockbit.com/"},
        timeout=15,
    )
    if r.status_code != 200:
        return None
    return r.json().get("data", {})


def main() -> None:
    token = TOKEN_FILE.read_text().strip()
    conn = sqlite3.connect(f"file:{SNAP}?mode=ro", uri=True)
    out = []
    for tk in TICKERS:
        for dt in DATES:
            d = fetch_flow(token, tk, dt)
            time.sleep(1.2)
            if not d:
                out.append({"ticker": tk, "date": dt, "fetch": "NO DATA"})
                continue
            buys, sells = d.get("buy", []), d.get("sell", [])
            # buy[]/sell[] are PER-MINUTE CUMULATIVE counters (parse_bars stores
            # them as-is); the day total is the MAX of each series, not the sum.
            tot = (max(int(b["lot"]["raw"]) for b in buys if b.get("lot"))
                   + max(int(s["lot"]["raw"]) for s in sells if s.get("lot")))
            bars = d.get("prices", [])
            stored = conn.execute(
                "SELECT MAX(buy_lot)+MAX(sell_lot), COUNT(*) FROM stockbit_flow_bars"
                " WHERE ticker=? AND trade_date=?", (tk, dt)).fetchone()
            oh = conn.execute(
                "SELECT volume FROM ohlcv WHERE ticker=? AND date=? AND COALESCE(is_final,1)=1",
                (tk, dt)).fetchone()
            row = {"ticker": tk, "date": dt,
                   "fetched_total_lots": tot, "fetched_bars": len(bars),
                   "fetched_vs_ohlcv": round(tot * 100 / oh[0], 4) if oh and oh[0] else None,
                   "stored_total_lots": stored[0], "stored_bars": stored[1],
                   "stored_vs_ohlcv": round(stored[0] * 100 / oh[0], 4) if oh and stored[0] else None,
                   "identical_totals": (stored[0] == tot) if stored[0] else None}
            out.append(row)
            print(json.dumps(row))
    conn.close()
    (HERE / "backfill_dryrun.json").write_text(json.dumps(out, indent=1) + "\n")
    print("WROTE backfill_dryrun.json")


if __name__ == "__main__":
    main()
