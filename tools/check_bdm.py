#!/usr/bin/env python3
"""Live-data sanity check for the /bdm broker-flow screen (engine/bdm.py). Read-only.

Two checks against independent sources, on one settled trade date:
  1. Gross reconstruction: lots rebuilt from broker_flow (listed-side lot_value + the other side
     = lot_value - |lot|) must equal the trade-book regular volume (stockbit_flow buy_lot+sell_lot,
     D-089 final totals). 2026-10-09 baseline: median ratio 1.000, 98% of 551 names within +-5%.
     A drop means the vendor changed field meanings or the top-25 lists are truncating.
  2. Direction: our bandar accumulation (top-5 buyers' net + top-5 sellers' net, / value) must
     agree in sign with the vendor's own top5_accdist label where that label is not Neutral.
     Baseline: 100% of 226, Spearman 0.84.
(bandar_detector.value is NOT total turnover -- a median 3x below it -- so it is not used.)

Usage:  venv/bin/python3 tools/check_bdm.py [YYYY-MM-DD]      (default: latest broker_flow date)
Exit 1 if either check falls below its threshold.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data.db import connect  # noqa: E402
from engine import bdm  # noqa: E402

RECON_MIN_SHARE = 0.90     # share of names whose rebuilt lots are within +-5% of the trade-book
SIGN_MIN_SHARE = 0.95      # sign agreement with the vendor's non-neutral top-5 labels
LABEL = {"Big Dist": -3, "Dist": -2, "Small Dist": -1, "Neutral": 0, "Small Acc": 1, "Acc": 2, "Big Acc": 3}


def reconstruction(conn, d: str) -> np.ndarray:
    tb = {t: (b or 0) + (s or 0) for t, b, s in
          conn.execute("SELECT ticker, buy_lot, sell_lot FROM stockbit_flow WHERE trade_date=?", (d,))}
    agg: dict[str, float] = {}
    for t, lot, lv in conn.execute("SELECT ticker, lot, lot_value FROM broker_flow WHERE trade_date=?", (d,)):
        listed, net = (lv or 0) / 100.0, abs(lot or 0)
        agg[t] = agg.get(t, 0.0) + listed + max(listed - net, 0.0)
    return np.asarray([v / 2.0 / tb[t] for t, v in agg.items() if tb.get(t, 0) > 1000])


def direction(conn, d: str) -> tuple[np.ndarray, np.ndarray]:
    vend = {t: LABEL.get(lab) for t, lab in
            conn.execute("SELECT ticker, top5_accdist FROM bandar_detector WHERE trade_date=?", (d,))}
    ours, theirs = [], []
    for (t, _), brokers in bdm._load(conn, d, d).items():
        lab = vend.get(t)
        s = bdm.day_stats(brokers)
        if lab is None or s["value"] <= 0:
            continue
        ours.append(s["net"]["bandar"] / s["value"])
        theirs.append(lab)
    return np.asarray(ours), np.asarray(theirs)


def main(argv: list[str]) -> int:
    conn = connect(read_only=True)
    d = argv[0] if argv else conn.execute("SELECT MAX(trade_date) FROM broker_flow").fetchone()[0]
    r = reconstruction(conn, d)
    ok_r = float(np.mean(np.abs(r - 1.0) < 0.05)) if len(r) else 0.0
    print(f"{d}  reconstruction: {len(r)} names, median {np.median(r):.3f}, within +-5% {ok_r:.0%}"
          f"  (min {RECON_MIN_SHARE:.0%})" if len(r) else f"{d}  reconstruction: no trade-book rows")
    o, v = direction(conn, d)
    nz = v != 0
    ok_s = float(np.mean(np.sign(o[nz]) == np.sign(v[nz]))) if nz.any() else 0.0
    print(f"{d}  direction: sign agreement {ok_s:.0%} of {int(nz.sum())} non-neutral vendor labels"
          f"  (min {SIGN_MIN_SHARE:.0%})")
    good = ok_r >= RECON_MIN_SHARE and ok_s >= SIGN_MIN_SHARE
    print("PASS" if good else "FAIL")
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
