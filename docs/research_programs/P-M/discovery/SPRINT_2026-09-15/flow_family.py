#!/usr/bin/env python3
"""FAMILY #3: FLOW — systematic discovery pass (new constructions only).

EXCLUDED AS RETREADS (declared skip-list): A4 (net_value/ADV60 level), A5
(z60(5d net - prior 5d net)), raw-flow z>=2, volspike+buyflow (E1 sprint 1),
flow/ADV x liquidity normalization (A4 family), streak-4-of-5 rolling count.

DECLARED TREE (~30 constructions, fixed before running):
 A DIVERGENCE: A1 up-move & nbz<=-1 | A2 down-move & nbz>=+1 [absorption ctl]
              A3 extreme div: ret1>=+2% & nbz<=-2 | A4x nbz-quartile profile in up-moves
 B REVERSAL:  B1 flip + -> - | B2 flip - -> + | B3 3d-sum sign flip | B4 5d-sum sign flip
 C PERSISTENCE: C1 nb>0 run>=4 | C2 exhaustion (run>=4 then nb<0) | C3 nb<0 run>=4 | C4 neg-run exhaustion
 D ACCEL/DECEL (new variables): D1 lot-share d5 z | D2 persistence accel | D3 fading inflow
 E EXTREMES: E1 nbz>=+3 | E2 nbz<=-3 | E3 own-percentile p95
 F x PRICE STATE: F1a quiet / F1b charged divergence | F2a dist at 20d-highs / F2b absorption at lows [ctl]
              F3a against uptrend / F3b against downtrend [ctl]
 H x VOLUME: H2a up & hi-vol & nbz<=-0.5 | H2b high vol & flow absent | H3 flow on dead tape
 I RISK FILTER (attack incumbent): I1 grid ret1>={+2,+3}% x nbz<={-0.5,-1,-1.5} | I2 half spreads
              I3 FM ladder | I4 ADV tiers

KILL RULES (declared): ENTRY: net60 h5 >= +30bp & >=3/4 halves & FM beta>0 |t|>=2 &
n>=1000/50 tickers (no flow OOS exists => entry survivors cap at CONDITIONAL).
FILTER: spread negative >=3/4 halves & n>=500 & survives FM incl. liquidity &
present in >= mid-ADV tier.
Results are printed to stdout (captured by shell redirection).
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import sprint_lib as sl
from adversarial_flow import build_contam

OUT = {"cells": [], "fm": {}, "i1_grid": []}
HK = (1, 2, 3, 5, 10, 20)


def cell(name, sel, holds, ledger, full=False):
    row = {"id": name, "n": int(sel.values.sum())}
    for k in HK:
        v = holds[k][sel].values; v = v[~np.isnan(v)]
        row[f"h{k}"] = float(np.mean(v)) if len(v) > 50 else None
    if row["h5"] is not None:
        r5 = holds[5][sel]
        vv = r5.values[~np.isnan(r5.values)]
        lo, hi = np.percentile(vv, [5, 95])
        srt = np.sort(vv); tot = srt.sum()
        m = max(1, int(len(srt) * 0.01))
        row.update({"med5": float(np.median(vv)),
                    "trim5": float(np.mean(vv[(vv >= lo) & (vv <= hi)])),
                    "hit5": float((vv > 0).mean()),
                    "top1_share": float(srt[-m:].sum() / tot) if tot > 0 else None,
                    "bot1_share": float(srt[:m].sum() / abs(tot)) if tot < 0 else None,
                    "net60_h5": row["h5"] - 0.006,
                    "n_tickers": int(sel.any(axis=0).sum())})
        sp = {}
        for lab, (a, b) in {"25H1": ("2025-01-01", "2025-07-01"), "25H2": ("2025-07-01", "2026-01-01"),
                            "26H1": ("2026-01-01", "2026-07-01"), "26H2": ("2026-07-01", "2026-12-31")}.items():
            x = r5[(r5.index >= a) & (r5.index < b)].values; x = x[~np.isnan(x)]
            sp[lab] = round(float(np.mean(x)), 5) if len(x) > 30 else None
        row["subs"] = sp
        row["pos_halves"] = sum(1 for x in sp.values() if x is not None and x > 0)
    fmt = lambda x, f="+.4f": ("None" if x is None else x.__format__(f))
    extra = ""
    if full and "subs" in row:
        extra = (f" h10={fmt(row['h10'])} h20={fmt(row['h20'])} halves={row['pos_halves']}/4 "
                 f"subs={[None if x is None else round(x, 4) for x in row['subs'].values()]}")
    print(f"  {name:46s} n={row['n']:6d} h5={fmt(row.get('h5'))} net={fmt(row.get('net60_h5'))} "
          f"med={fmt(row.get('med5'))} trim={fmt(row.get('trim5'))} hit={fmt(row.get('hit5'), '.3f')}{extra}")
    ledger.append(row)
    return row


def main():
    p = sl.SprintPanel()
    mask0 = p.mask_base()
    r1 = p.ret1
    _cum = (p.ret + 1.0).cumprod()
    holds = {k: p.hold[k] if k in p.hold else _cum.shift(-1 - k) / _cum.shift(-1) - 1.0 for k in HK}
    clean = ~build_contam(p)
    mask = mask0 & clean

    nbz = sl.trailing_z(p.nb)
    volz = sl.trailing_z(p.volume)
    ret5z = sl.trailing_z(p.ret5)
    bl = p.buy_lot; sl_ = p.sell_lot
    lot_share = bl / (bl + sl_).replace(0, np.nan)
    nb = p.nb
    hi = sl.to_panel(p.adj[p.adj.date >= "2024-06-01"], "high")
    lo = sl.to_panel(p.adj[p.adj.date >= "2024-06-01"], "low")
    tr = (hi - lo) / p.close
    atr_ratio = tr / tr.rolling(10, min_periods=6).mean().shift(1)
    hi20 = hi.rolling(20, min_periods=15).max()
    lo20 = lo.rolling(20, min_periods=15).min()
    new_high = (p.close >= hi20)
    new_low = (p.close <= lo20)
    adv = p.adv60.where(mask0)
    adv_ter = adv.rank(axis=1, pct=True)

    up1 = (r1 >= 0.01); dn1 = (r1 <= -0.01)
    L = []
    print("=== A. DIVERGENCE ===")
    cell("A1 up-move & nbz<=-1 (outflow into strength)", mask & up1.fillna(False) & (nbz <= -1), holds, L)
    cell("A2 down-move & nbz>=+1 [absorption ctl]", mask & dn1.fillna(False) & (nbz >= 1), holds, L)
    cell("A3 extreme div: ret1>=+2% & nbz<=-2", mask & (r1 >= 0.02) & (nbz <= -2), holds, L)
    print("  [A4x magnitude profile: nbz-quartile means within up-moves]")
    q = nbz.where(up1.fillna(False)).rank(axis=1, pct=True)
    for qa, lab in ((0.0, "Q1 most-negative"), (0.25, "Q2"), (0.5, "Q3"), (0.75, "Q4 most-positive")):
        sel = mask & up1.fillna(False) & (q > qa)
        v = holds[5][sel].values; v = v[~np.isnan(v)]
        print(f"    up-move {lab:18s}: n={len(v):6d} h5={np.mean(v):+.4f}" if len(v) > 30 else f"    {lab}: n<30")
    print("=== B. REVERSAL ===")
    cell("B1 flow flip + -> -", mask & (nbz.shift(1) >= 0.5) & (nbz <= -0.5), holds, L)
    cell("B2 flow flip - -> +", mask & (nbz.shift(1) <= -0.5) & (nbz >= 0.5), holds, L)
    s3p = np.sign(nb.rolling(3, min_periods=2).sum())
    cell("B3 3d-sum sign flip", mask & (s3p > 0) & (s3p.shift(3) < 0), holds, L)
    s5p = np.sign(nb.rolling(5, min_periods=3).sum())
    cell("B4 5d-sum sign flip", mask & (s5p > 0) & (s5p.shift(5) < 0), holds, L)
    print("=== C. PERSISTENCE ===")
    pos_run = (nb > 0).rolling(4).sum()
    cell("C1 nb>0 run >=4 days", mask & (pos_run >= 4), holds, L)
    cell("C2 exhaustion: run>=4 then nb<0 today", mask & (pos_run.shift(1) >= 4) & (nb < 0), holds, L)
    neg_run = (nb < 0).rolling(4).sum()
    cell("C3 nb<0 run >=4 days", mask & (neg_run >= 4), holds, L)
    cell("C4 neg-run exhaustion (nb>0 today)", mask & (neg_run.shift(1) >= 4) & (nb > 0), holds, L)
    print("=== D. ACCEL/DECEL (new variables) ===")
    ls_chg = (lot_share - lot_share.shift(5))
    cell("D1 lot-share d5 z>=+1.5", mask & (sl.trailing_z(ls_chg) >= 1.5), holds, L)
    frac_pos = (nb > 0).astype(float)
    cell("D2 persistence accel (frac_pos 5d - prior5d >= +0.4)",
         mask & ((frac_pos.rolling(5).sum() - frac_pos.shift(5).rolling(5).sum()) >= 0.4), holds, L)
    m3 = nb.rolling(3, min_periods=2).mean()
    cell("D3 fading inflow (3d mean>0, <40% of prior 3d)",
         mask & (m3 > 0) & (m3 < 0.4 * m3.shift(3)) & (m3.shift(3) > 0), holds, L)
    print("=== E. EXTREMES ===")
    cell("E1 nbz>=+3 (extreme chase)", mask & (nbz >= 3), holds, L)
    cell("E2 nbz<=-3 (extreme capitulation)", mask & (nbz <= -3), holds, L)
    pctl = nbz.where(mask0).rank(axis=1, pct=True)
    cell("E3 nbz p95+ (own-percentile)", mask & (pctl >= 0.95), holds, L)
    print("=== F. x PRICE STATE ===")
    div_base = mask & up1.fillna(False) & (nbz <= -1)
    cell("F1a quiet divergence (ATR<=1x)", div_base & (atr_ratio <= 1.0), holds, L)
    cell("F1b charged divergence (ATR>=1.5x)", div_base & (atr_ratio >= 1.5), holds, L)
    cell("F2a distribution at 20d-highs", mask & new_high.fillna(False) & (nbz <= -0.5), holds, L)
    cell("F2b absorption at 20d-lows [ctl]", mask & new_low.fillna(False) & (nbz >= 0.5), holds, L)
    cell("F3a flow against uptrend (ret5>0 & nbz<=-1)", mask & (p.ret5 > 0) & (nbz <= -1), holds, L)
    cell("F3b flow against downtrend [ctl]", mask & (p.ret5 < 0) & (nbz >= 1), holds, L)
    print("=== H. x VOLUME ===")
    cell("H2a up-move & hi-vol & nbz<=-0.5", mask & up1.fillna(False) & (volz >= 1.5) & (nbz <= -0.5), holds, L)
    cell("H2b high volume & flow absent", mask & (volz >= 1.5) & (nbz.abs() <= 0.5), holds, L)
    cell("H3 flow on dead tape (volz<=-1 & |nbz|>=1.5)", mask & (volz <= -1) & (nbz.abs() >= 1.5), holds, L)
    OUT["cells"] = L

    print("=== I. RISK FILTER: platform-outflow-into-strength ===")
    for mv in (0.02, 0.03):
        for zt in (-0.5, -1.0, -1.5):
            sel = mask & (r1 >= mv) & (nbz <= zt)
            ctl = mask & (r1 >= mv) & (nbz.abs() < 0.5)
            r = cell(f"I1 veto: ret1>=+{mv:.0%} & nbz<= {zt}", sel, holds, L, full=True)
            sp = {}
            for lab, (a, b) in {"25H1": ("2025-01-01", "2025-07-01"), "25H2": ("2025-07-01", "2026-01-01"),
                                "26H1": ("2026-01-01", "2026-07-01"), "26H2": ("2026-07-01", "2026-12-31")}.items():
                xb = holds[5][sel]; xg = holds[5][ctl]
                xb = xb[(xb.index >= a) & (xb.index < b)].values; xb = xb[~np.isnan(xb)]
                xg = xg[(xg.index >= a) & (xg.index < b)].values; xg = xg[~np.isnan(xg)]
                sp[lab] = round(float(np.mean(xb) - np.mean(xg)), 4) if len(xb) > 30 and len(xg) > 30 else None
            r["spread_halves"] = sp
            r["neg_halves"] = sum(1 for x in sp.values() if x is not None and x < 0)
            print(f"      spread vs flow-neutral up-moves: {sp} neg={r['neg_halves']}/4")
            OUT["i1_grid"].append(r)

    print("\n  I3 FM ladder for the veto cell (h5):")
    flag = ((r1 >= 0.03) & (nbz <= -1)).fillna(False).astype(float)
    ladder = {"price": [r1], "price+volume": [r1, ret5z, volz],
              "+liquidity": [r1, ret5z, volz, adv_ter],
              "+chase flag": [r1, ret5z, volz, adv_ter, (nbz >= 0.5).astype(float)]}
    for nm, cs in ladder.items():
        rr = sl.fm_regression(p, flag, mask, controls=cs, k=5)
        OUT["fm"][f"veto|{nm}"] = rr
        print(f"    {nm:14s}: beta={rr['fm_mean']:+.5f} t={rr['fm_t']:+.2f} n_dates={rr['n_dates']}")
    print("  I4 veto cell by ADV tier (h5):")
    for tname, tsel in (("ADV top", adv_ter >= 0.667), ("ADV mid", (adv_ter >= 0.333) & (adv_ter < 0.667)),
                        ("ADV bot", adv_ter < 0.333)):
        sel = mask & (r1 >= 0.03) & (nbz <= -1) & tsel.fillna(False)
        v = holds[5][sel].values; v = v[~np.isnan(v)]
        print(f"    {tname}: n={len(v):6d} h5={np.mean(v):+.4f}" if len(v) > 30 else f"    {tname}: n<30")

    print("\n  FM for notable ENTRY cells (h5 | ret1, ret5z, volz, adv_ter, chase):")
    ctrls = [r1, ret5z, volz, adv_ter, (nbz >= 0.5).astype(float)]
    for nm, fl in (("B2 flip - ->+", (nbz.shift(1) <= -0.5) & (nbz >= 0.5)),
                   ("E2 nbz<=-3", (nbz <= -3)),
                   ("C4 neg-run exhaustion", (neg_run.shift(1) >= 4) & (nb > 0)),
                   ("D1 lot-share accel", (sl.trailing_z(ls_chg) >= 1.5))):
        rr = sl.fm_regression(p, fl.fillna(False).astype(float), mask, controls=ctrls, k=5)
        OUT["fm"][nm] = rr
        print(f"    {nm:26s}: beta={rr['fm_mean']:+.5f} t={rr['fm_t']:+.2f}")


if __name__ == "__main__":
    main()
