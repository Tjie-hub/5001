"""Minute-bar volume under-capture audit (Task B) — READ-ONLY.

capture(ticker, day) = (max cum buy_lot + max cum sell_lot) x 100 / ohlcv volume
(stockbit lot = 100 shares; buy_lot/sell_lot are cumulative counters within the
session - unit verified: ACES 2026-04-20 09:00 (4590-2172) x 100 x 378 = 91.36m
~= net_value -91.14m).

One grouped query per month (the full-table GROUP BY is too slow). All reads on
the pinned 2026-10-08 walkforward snapshot (mode=ro); nothing is written.

Run: venv/bin/python docs/research_programs/P-M/data_audits/minute_volume/capture_audit.py
Writes capture_daily.json next to this file.
"""
from __future__ import annotations

import json
import sqlite3
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SNAP = "/home/tjiesar/scratch/g0_snapshots_2026-10-08/walkforward_snapshot_2026-10-08.db"


def months(first: str, last: str):
    y, m = int(first[:4]), int(first[5:7])
    out = []
    while (y, m) <= (int(last[:4]), int(last[5:7])):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def main() -> None:
    t0 = time.time()
    conn = sqlite3.connect(f"file:{SNAP}?mode=ro", uri=True)
    lo, hi = conn.execute("SELECT MIN(trade_date), MAX(trade_date) FROM stockbit_flow_bars").fetchone()
    # ohlcv daily volumes for the whole window, once
    vol = {}
    for t, d, v, c in conn.execute(
            "SELECT ticker, date, volume, close FROM ohlcv WHERE COALESCE(is_final,1)=1"
            " AND date BETWEEN ? AND ?", (lo, hi)):
        vol[(t, d)] = (v, c)
    # per-ticker median daily rupiah turnover (scope classification only, naive close x volume)
    turn = defaultdict(list)
    for (t, d), (v, c) in vol.items():
        if v and c:
            turn[t].append(v * c)
    tier = {}
    for t, xs in turn.items():
        med = float(np.median(xs))
        tier[t] = (">=10bn" if med >= 1e10 else "1-10bn" if med >= 1e9
                   else "100m-1bn" if med >= 1e8 else "<100m")

    daily = {}
    per_month_runtime = {}
    for mo in months(lo, hi):
        tm = time.time()
        n1_mo = int(mo[5:]) % 12 + 1
        n1_y = int(mo[:4]) + (1 if int(mo[5:]) == 12 else 0)
        n0, n1 = f"{mo}-01", f"{n1_y:04d}-{n1_mo:02d}-01"
        rows = conn.execute(
            "SELECT ticker, trade_date, MAX(buy_lot), MAX(sell_lot), COUNT(*),"
            " MIN(bar_time), MAX(bar_time) FROM stockbit_flow_bars"
            " WHERE trade_date >= ? AND trade_date < ? GROUP BY ticker, trade_date", (n0, n1)).fetchall()
        per_month_runtime[mo] = round(time.time() - tm, 1)
        byday = defaultdict(list)
        for t, d, mb, ms, nb, t0_, t1_ in rows:
            v, _ = vol.get((t, d), (None, None))
            if v and v > 0:
                byday[d].append((t, (mb + ms) * 100.0 / v, nb, t1_))
        for d, items in byday.items():
            caps = np.asarray([x[1] for x in items])
            lastbars = Counter(x[3] for x in items).most_common(3)
            nbars = np.asarray([x[2] for x in items], float)
            tiers = defaultdict(list)
            for t, cap, _, _ in items:
                tiers[tier.get(t, "?")].append(cap)
            daily[d] = {
                "n_tickers": len(items),
                "median_capture": round(float(np.median(caps)), 4),
                "p25_capture": round(float(np.percentile(caps, 25)), 4),
                "p75_capture": round(float(np.percentile(caps, 75)), 4),
                "frac_lt_90": round(float((caps < 0.90).mean()), 4),
                "median_bars_per_ticker": float(np.median(nbars)),
                "top_last_bars": lastbars,
                "median_capture_by_tier": {k: round(float(np.median(v)), 4)
                                           for k, v in sorted(tiers.items())},
            }

    dates = sorted(daily)
    meds = [daily[d]["median_capture"] for d in dates]
    # break detection: first date starting a run of >= 5 sessions with median < 0.90
    break_date = None
    run = 0
    for d, m in zip(dates, meds):
        run = run + 1 if m < 0.90 else 0
        if run >= 5 and break_date is None:
            break_date = dates[dates.index(d) - 4]
    pre = [m for d, m in zip(dates, meds) if break_date and d < break_date] or meds[:5]
    post = [m for d, m in zip(dates, meds) if break_date and d >= break_date] or meds[-5:]
    out = {
        "snapshot": {"path": SNAP,
                     "note": "pinned 2026-10-08 walkforward snapshot, read-only (rule: no writes to walkforward.db)"},
        "window": [lo, hi],
        "per_month_query_seconds": per_month_runtime,
        "daily": daily,
        "break": {
            "rule": "first date of a >=5-session run with median daily capture < 90%",
            "break_date": break_date,
            "median_capture_pre": round(float(np.median(pre)), 4) if pre else None,
            "median_capture_post": round(float(np.median(post)), 4) if post else None,
            "min_median_capture_post": round(float(min(post)), 4) if post else None,
        },
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "runtime_minutes": round((time.time() - t0) / 60.0, 1),
    }
    (HERE / "capture_daily.json").write_text(json.dumps(out, indent=1) + "\n")
    print("WROTE capture_daily.json")
    print("break:", out["break"], "| pre/post medians:", out["break"]["median_capture_pre"],
          out["break"]["median_capture_post"])
    print("runtime_minutes:", out["runtime_minutes"], "| per-month seconds:", per_month_runtime)


if __name__ == "__main__":
    main()
