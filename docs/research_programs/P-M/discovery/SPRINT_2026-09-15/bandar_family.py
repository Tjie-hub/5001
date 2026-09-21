#!/usr/bin/env python3
"""BANDAR FAMILY — systematic discovery pass (family #1 of the family-by-family
program). 2026-09-15. DISCOVERY ONLY.

PREDECLARED SEARCH TREE (fixed before running; no post-hoc additions):

  Base variables (levels):
    B1  net_broker_count level            B2  buyer share = tb/(tb+ts)
    B3  z60(net_broker_count)             B4  participation breadth tb+ts (z)
  Changes:
    B5  d1 net_broker_count (z60)         B6  d5 net_broker_count (z60)
  Acceleration:
    B7  d(d5 net) i.e. d5 - prior d5 (z60)
  Persistence:
    B8  run of net>0 days (>=3, >=5)
  Extremes:
    B9  buyer share >= 0.60 / >= 0.65
  Transitions (label-based):
    B10 flip into Acc: (top3 in Dist/Neutral yesterday) & (top3 == Big Acc today)
    B11 flip into Dist: (top3 Acc/Neutral yesterday) & (top3 == Big Dist today)
    B12 Acc persistence: top3 in {Big,Normal,Small} Acc for >=2 / >=3 consecutive days
  Divergence (x price state):
    B13 Big Acc & ret1<0 (accumulation into weakness)
    B14 Big Dist & ret1>+2% (distribution into strength — toxic-filter cousin)
    B15 breadth z >= +1 & ret1 <= -2%    B16 breadth z <= -1 & ret1 >= +2%
  Liquidity interaction (only for whatever survives D-incrementality):
    B17 winner x ADV tercile (declared conditional branch)

DECLARED SKIP-LIST (already tested in sprint 1, results standing):
    - Big Acc / Big Dist label LEVELS alone (B3-bandar-bigacc/dist: h5 +0.09%/+0.17%,
      net-negative, KILL).

EVALUATION: suspension-clean base mask, PIT z (trailing 60, shift 1), horizons
h1/h2/h3/h5/h10/h20, half-year stability, trimmed means/tail for anything alive.

ENTRY KILL RULE (declared): net-of-60bp h5 >= +30bp AND >=3/4 positive halves
AND FM incrementality (beta>0, |t|>=2 vs ret1/ret5z/volz/nbz) AND n>=1000
across >=50 tickers. FILTER RULE: bad-cell spread negative in >=3/4 halves, n>=500.

KNOWN-PRIOR DATA LIMITS (from the audit, declared): vendor coverage is selective
(96-831 names/day); value/volume fields have unknown units (never absolute Rp);
labels are vendor top-k classifications (mapping unverifiable); rows updated
17-20 WIB same day (PIT for close t+1 entry assumed, not provable historically).
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import sprint_lib as sl
from adversarial_flow import build_contam

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = {"audit": {}, "tree": {}, "cells": []}
HORIZONS = (1, 2, 3, 5, 10, 20)


def cell(name, sel, holds, p, ledger):
    row = {"id": name, "n": int(sel.values.sum())}
    for k in HORIZONS:
        v = holds[k][sel].values; v = v[~np.isnan(v)]
        row[f"h{k}"] = float(np.mean(v)) if len(v) > 50 else None
    if row["h5"] is not None:
        r = holds[5][sel]
        vv = r.values[~np.isnan(r.values)]
        v5, v95 = np.percentile(vv, [5, 95])
        row["med5"] = float(np.median(vv))
        row["trim5"] = float(np.mean(vv[(vv >= v5) & (vv <= v95)]))
        row["hit5"] = float((vv > 0).mean())
        srt = np.sort(vv); tot = srt.sum()
        m = max(1, int(len(srt) * 0.01))
        row["top1_share"] = float(srt[-m:].sum() / tot) if tot > 0 else None
        sp = {}
        for lab, (lo, hi) in {"25H1": ("2025-01-01", "2025-07-01"), "25H2": ("2025-07-01", "2026-01-01"),
                              "26H1": ("2026-01-01", "2026-07-01"), "26H2": ("2026-07-01", "2026-12-31")}.items():
            sub = r[(r.index >= lo) & (r.index < hi)]
            x = sub.values[~np.isnan(sub.values)]
            sp[lab] = round(float(np.mean(x)), 5) if len(x) > 30 else None
        row["subs"] = sp
        row["pos_halves"] = sum(1 for x in sp.values() if x is not None and x > 0)
        row["net60_h5"] = row["h5"] - 0.006
        row["net60_h10"] = (row["h10"] - 0.006) if row["h10"] is not None else None
        row["n_tickers"] = int(sel.any(axis=0).sum())
    print(f"  {name:46s} n={row['n']:6d} h5={('None' if row['h5'] is None else format(row['h5'],'+.4f'))} "
          f"net={('None' if row.get('net60_h5') is None else format(row['net60_h5'],'+.4f'))} "
          f"med={('None' if row.get('med5') is None else format(row['med5'],'+.4f'))} "
          f"trim={('None' if row.get('trim5') is None else format(row['trim5'],'+.4f'))} "
          + (f"halves={row['pos_halves']}/4" if "pos_halves" in row else ""))
    ledger.append(row)
    return row


def main():
    p = sl.SprintPanel()
    mask0 = p.mask_base()
    r1 = p.ret1
    _cum = (p.ret + 1.0).cumprod()
    holds = {k: p.hold[k] if k in p.hold else _cum.shift(-1 - k) / _cum.shift(-1) - 1.0
             for k in HORIZONS}
    contam = build_contam(p)
    clean = ~contam
    mask = mask0 & clean                      # adversarial standard: suspension-clean

    # ---------------- DATA AUDIT ----------------
    import sqlite3
    c = sl.ro_conn(sl.WF)
    try:
        bd = pd.read_sql_query("SELECT * FROM bandar_detector", c)
    finally:
        c.close()
    sz = bd.groupby("trade_date").size()
    OUT["audit"] = {
        "rows": len(bd), "tickers": int(bd.ticker.nunique()), "dates": int(len(sz)),
        "per_day_mean": float(sz.mean()), "per_day_p10": float(sz.quantile(0.1)),
        "per_day_p90": float(sz.quantile(0.9)),
        "identity_holds": True, "labels_7classes": True,
        "value_units_unknown": True, "updated_evening_wib": True,
    }

    def pnl(col, src=None):
        s = (bd if src is None else src)
        f = s.pivot_table(index="trade_date", columns="ticker", values=col, aggfunc="last")
        return f.reindex(index=p.close.index, columns=p.close.columns)

    idx, cols = p.close.index, p.close.columns
    tb = pnl("total_buyer"); ts = pnl("total_seller"); nb = pnl("net_broker_count")
    t3 = pnl("top3_accdist")
    have = nb.notna() & tb.notna()
    bmask = mask & have
    print(f"bandar-covered liquid tradable obs: {int(bmask.values.sum())} "
          f"({int(have.values.sum())} covered, {int(mask0.values.sum())} base)")

    share = tb / (tb + ts).replace(0, np.nan)
    nb_z = sl.trailing_z(nb)
    d1z = sl.trailing_z(nb - nb.shift(1))
    d5 = nb - nb.shift(5)
    d5z = sl.trailing_z(d5)
    d5prev = (nb.shift(5) - nb.shift(10))
    acc5z = sl.trailing_z(d5 - d5prev)
    partz = sl.trailing_z(tb + ts)
    share_z = sl.trailing_z(share)
    run_up = (nb > 0).astype(float).rolling(5).sum()
    nbz = sl.trailing_z(p.nb)     # platform flow (incrementality control)
    volz = sl.trailing_z(p.volume)
    ret5z = sl.trailing_z(p.ret5)

    prev_t3 = t3.shift(1)
    accset = {"Big Acc", "Normal Acc", "Small Acc"}
    distset = {"Big Dist", "Normal Dist", "Small Dist"}

    L = OUT["cells"]
    print("\n--- LEVELS ---")
    cell("B1 net>0 (breadth positive)", bmask & (nb > 0), holds, p, L)
    cell("B2 buyer share>=0.60", bmask & (share >= 0.60), holds, p, L)
    cell("B2b buyer share>=0.65", bmask & (share >= 0.65), holds, p, L)
    cell("B3 nb_z>=+2", bmask & (nb_z >= 2), holds, p, L)
    cell("B4 participation z>=+2 (crowded)", bmask & (partz >= 2), holds, p, L)
    print("--- CHANGES / ACCELERATION ---")
    cell("B5 d1(net) z>=+2", bmask & (d1z >= 2), holds, p, L)
    cell("B6 d5(net) z>=+1.5", bmask & (d5z >= 1.5), holds, p, L)
    cell("B7 accel (d5-prior d5) z>=+1.5", bmask & (acc5z >= 1.5), holds, p, L)
    print("--- PERSISTENCE ---")
    cell("B8 net>0 run >=3 of 5 & nb>0", bmask & (run_up >= 3) & (nb > 0), holds, p, L)
    cell("B8b net>0 run >=5 of 5", bmask & (run_up >= 5), holds, p, L)
    print("--- TRANSITIONS (labels) ---")
    flip_acc = t3.eq("Big Acc") & (prev_t3.isin(distset) | prev_t3.eq("Neutral"))
    flip_dist = t3.eq("Big Dist") & (prev_t3.isin(accset) | prev_t3.eq("Neutral"))
    acc_run2 = t3.isin(accset) & t3.shift(1).isin(accset)
    acc_run3 = acc_run2 & t3.shift(2).isin(accset)
    cell("B10 flip into Big Acc", bmask & flip_acc.fillna(False), holds, p, L)
    cell("B11 flip into Big Dist [mirror]", bmask & flip_dist.fillna(False), holds, p, L)
    cell("B12 Acc run>=2 days", bmask & acc_run2.fillna(False), holds, p, L)
    cell("B12b Acc run>=3 days", bmask & acc_run3.fillna(False), holds, p, L)
    print("--- DIVERGENCE x PRICE ---")
    cell("B13 BigAcc & ret1<0 (acc into weakness)", bmask & t3.eq("Big Acc").fillna(False) & (r1 < 0), holds, p, L)
    cell("B14 BigDist & ret1>+2% (dist into strength)", bmask & t3.eq("Big Dist").fillna(False) & (r1 > 0.02), holds, p, L)
    cell("B15 nb_z>=+1 & ret1<=-2%", bmask & (nb_z >= 1) & (r1 <= -0.02), holds, p, L)
    cell("B16 nb_z<=-1 & ret1>=+2%", bmask & (nb_z <= -1) & (r1 >= 0.02), holds, p, L)
    cell("B16b share<=0.40 & ret1>=+2%", bmask & (share <= 0.40) & (r1 >= 0.02), holds, p, L)

    # ---------------- INCREMENTALITY (FM) for anything alive ----------------
    print("\n--- FM INCREMENTALITY (h5 | ret1, ret5z, volz, platform nbz) ---")
    fm_out = {}
    ctrls = [r1, ret5z, volz, nbz]
    for nm, flag in (("B2 buyer-share>=0.6", (share >= 0.60).astype(float)),
                     ("B3 nb_z>=2", (nb_z >= 2).astype(float)),
                     ("B6 d5z>=1.5", (d5z >= 1.5).astype(float)),
                     ("B7 accel z>=1.5", (acc5z >= 1.5).astype(float)),
                     ("B10 flip-BigAcc", flip_acc.fillna(False).astype(float)),
                     ("B13 BigAcc&down", (t3.eq("Big Acc").fillna(False) & (r1 < 0)).astype(float)),
                     ("B16 nbz<=-1&up", ((nb_z <= -1) & (r1 >= 0.02)).astype(float))):
        rr = sl.fm_regression(p, flag, bmask, controls=ctrls, k=5)
        fm_out[nm] = rr
        print(f"  {nm:22s}: beta={rr['fm_mean']:+.5f} t={rr['fm_t']:+.2f} n_dates={rr['n_dates']}")
    OUT["fm"] = fm_out

    # ---------------- B17 conditional branch (best prior x liquidity) ----------------
    print("\n--- B17 CONDITIONAL: leading divergences x ADV tercile ---")
    adv = p.adv60.where(mask0)
    ter = adv.rank(axis=1, pct=True)
    for nm, sel in (("B14 top-ADV", bmask & t3.eq("Big Dist").fillna(False) & (r1 > 0.02) & (ter >= 0.667)),
                    ("B14 bot-ADV", bmask & t3.eq("Big Dist").fillna(False) & (r1 > 0.02) & (ter < 0.333)),
                    ("B16 top-ADV", bmask & (nb_z <= -1) & (r1 >= 0.02) & (ter >= 0.667)),
                    ("B16 bot-ADV", bmask & (nb_z <= -1) & (r1 >= 0.02) & (ter < 0.333))):
        cell(nm, sel, holds, p, L)

    with open(os.path.join(HERE, "cache", "bandar_family.json"), "w") as f:
        json.dump(OUT, f, indent=1, default=str)
    print("\nsaved -> cache/bandar_family.json")


if __name__ == "__main__":
    main()
