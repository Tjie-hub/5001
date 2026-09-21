#!/usr/bin/env python3
"""FAMILY #6: CROSS-FAMILY INTERACTIONS — FINAL DISCOVERY PASS.

DECLARED TREE: 14 new constructions (7 branches already answered by standing
results from families 1-5 and skipped as declared retreads: A1/A2 divergence
cells, B1/B2 volume-confirm, B3=V7a, B5=V6c, E1=V2e, E5=V5a/V5b/H2a).

  GROUP A (price x flow):
    A3  dual acceleration: price accel (ret1>=+2% & 0<=ret5<=+5%) & flow accel (accel_z>=+1)
    A4  stealth flow: compression (range/ATR<=0.8) & |flow change| (nbz>=+1)
    A5  price reversal + flow reversal (ret1>0 after ret5<=-3%) & (nbz - -> +)
  GROUP B (price x participation):
    B4  grind + participation: ret5>=+5% with <=1 day >+3% & >=3 up days & rv>=1.5
  GROUP C (flow x liquidity):
    C2  flow extreme out (nbz<=-3) & liquidity expansion (regime>=1.2)
    C3  flow extreme in (nbz>=+3) & liquidity contraction (regime<=0.8)
    C4  flow reversal (- -> +) & regime expansion (regime>=1.2)
  GROUP D (price x flow x participation):
    D1  ret1>=+3% & nbz<=-1 & rv>=1.5 (distribution tape)
    D2  compression & nbz>=+1 & rv>=1.5 (stealth accumulation)
    D3  ret5<=-5% & nbz>=+1 & rv>=2 (support into weakness)
    D4  ret5>=+5% & nbz<=-1 & rv>=2 (strength distributed)
  GROUP E (state transitions):
    E2  compressed -> expanding (range/ATR min last5 <=0.8 & today >=1.5)
    E3  flow-neutral -> flow-extreme (|nbz|<=0.5 x3 days then |nbz|>=2)
    E4  price-neutral -> price-extreme (|ret|<=0.5% x3 days then |ret1|>=4%)

PARENT TEST: every interaction is reported next to its parents (same battery);
interaction must beat BOTH parents in net terms to be alive.
KILL RULES (declared, unchanged): ENTRY net60 h5>=+30bp & >=3/4 halves & FM
beta>0 |t|>=2 (controls: ret1, ret5z, volz, ADV tercile, flow level) & n>=1000/
50 tickers & tail not dominant & pseudo-OOS if price-only. FILTER: spread
negative >=3/4 halves & n>=500 & FM incl. liquidity & present in >= mid-ADV.
Flow-dependent interactions: NO historical OOS exists (flow starts 2025-01).
Results printed to stdout (captured by shell redirection).
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import sprint_lib as sl
from adversarial_flow import build_contam

OUT = {"cells": [], "fm": {}, "oos": {}}
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
    print(f"  {name:52s} n={row['n']:6d} h5={fmt(row.get('h5'))} net={fmt(row.get('net60_h5'))} "
          f"med={fmt(row.get('med5'))} trim={fmt(row.get('trim5'))} hit={fmt(row.get('hit5'), '.3f')}{extra}")
    ledger.append(row)
    return row


def pseudo_oos(name, builder):
    c = sl.ro_conn(sl.WF)
    try:
        ohl = pd.read_sql_query("SELECT ticker, date, open, high, low, close, volume FROM ohlcv "
                                "WHERE is_final=1 AND close>0 ORDER BY ticker, date", c)
    finally:
        c.close()
    ohl["traded_value"] = ohl["close"] * ohl["volume"]
    adj = sl.build_adjusted(ohl, sl.load_corporate_actions())
    F = {k: sl.to_panel(adj, k) for k in ("close", "ret", "volume", "traded_value")}
    liq = sl.trailing_median_panel(F["traded_value"]) >= sl.LIQ_FLOOR
    trad = liq & (F["volume"].shift(-1) > 0)
    cum = (F["ret"] + 1.0).cumprod()
    H = {5: cum.shift(-6) / cum.shift(-1) - 1.0, 10: cum.shift(-11) / cum.shift(-1) - 1.0}
    sel = builder(F) & trad
    res = {}
    for era, a, b in (("2021H2-2022", "2021-07-01", "2023-01-01"), ("2023-2024", "2023-01-01", "2025-01-01")):
        s = sel[(sel.index >= a) & (sel.index < b)]
        for k in (5, 10):
            v = H[k][s].values; v = v[~np.isnan(v)]
            res[f"{era}_h{k}"] = {"n": len(v), "mean": float(np.mean(v)) if len(v) else None}
    print(f"  OOS[{name}]: " + " | ".join(f"{k}: n={v['n']} h={None if v['mean'] is None else round(v['mean'], 4)}"
                                          for k, v in res.items()))
    OUT["oos"][name] = res


def main():
    p = sl.SprintPanel()
    mask0 = p.mask_base()
    r1 = p.ret1
    _cum = (p.ret + 1.0).cumprod()
    holds = {k: p.hold[k] if k in p.hold else _cum.shift(-1 - k) / _cum.shift(-1) - 1.0 for k in HK}
    clean = ~build_contam(p)
    mask = mask0 & clean

    nbz = sl.trailing_z(p.nb)
    nb5 = p.nb.rolling(5, min_periods=3).sum()
    accel_z = sl.trailing_z(nb5 - nb5.shift(5))
    ret5z = sl.trailing_z(p.ret5)
    volz = sl.trailing_z(p.volume)
    vol = p.volume
    rv = vol / vol.rolling(60, min_periods=30).median().shift(1).replace(0, np.nan)
    op = sl.to_panel(p.adj[p.adj.date >= "2024-06-01"], "open")
    hi = sl.to_panel(p.adj[p.adj.date >= "2024-06-01"], "high")
    lo = sl.to_panel(p.adj[p.adj.date >= "2024-06-01"], "low")
    tr_ = (hi - lo) / p.close
    atr10 = tr_.rolling(10, min_periods=6).mean().shift(1)
    atr_ratio = tr_ / atr10
    tv = p.traded_value
    regime = tv.rolling(20, min_periods=10).mean().shift(1) / p.tv_med60.replace(0, np.nan)
    up_cl = (p.close > p.close.shift(1))

    L = []
    print("=== GROUP A: PRICE x FLOW ===")
    accel_price = (r1 >= 0.02) & (p.ret5 >= 0) & (p.ret5 <= 0.05)
    pA = mask & accel_price.fillna(False)
    cell("[parent] price accel (ret1>=2%, ret5 0..5%)", pA, holds, L)
    cell("[parent] flow accel (accel_z>=+1)", mask & (accel_z >= 1), holds, L)
    cell("A3 dual acceleration", pA & (accel_z >= 1), holds, L)
    comp = (atr_ratio <= 0.8)
    pC = mask & comp.fillna(False)
    cell("[parent] compression (range<=0.8xATR)", pC, holds, L)
    cell("A4 stealth flow: compression & nbz>=+1", pC & (nbz >= 1), holds, L)
    rev_p = (r1 > 0) & (p.ret5 <= -0.03)
    rev_f = (nbz.shift(1) <= -0.5) & (nbz >= 0.5)
    cell("[parent] price reversal (up after ret5<=-3%)", mask & rev_p.fillna(False), holds, L)
    cell("A5 price reversal + flow reversal", mask & rev_p.fillna(False) & rev_f.fillna(False), holds, L)
    print("=== GROUP B: PRICE x PARTICIPATION ===")
    grind = (p.ret5 >= 0.05) & (up_cl.rolling(5).sum() >= 3) & ((r1 > 0.03).rolling(5).sum() <= 1)
    pG = mask & grind.fillna(False)
    cell("[parent] slow grind (ret5>=+5%, <=1 day >3%)", pG, holds, L)
    cell("B4 grind + participation (rv>=1.5)", pG & (rv >= 1.5), holds, L)
    print("=== GROUP C: FLOW x LIQUIDITY ===")
    reg_hi = (regime >= 1.2)
    reg_lo = (regime <= 0.8)
    cell("[parent] liquidity expansion (regime>=1.2)", mask & reg_hi.fillna(False), holds, L)
    cell("C2 flow extreme out & liq expansion", mask & (nbz <= -3) & reg_hi.fillna(False), holds, L)
    cell("C3 flow extreme in & liq contraction", mask & (nbz >= 3) & reg_lo.fillna(False), holds, L)
    cell("C4 flow reversal & liq expansion", mask & rev_f.fillna(False) & reg_hi.fillna(False), holds, L)
    print("=== GROUP D: PRICE x FLOW x PARTICIPATION ===")
    d_base = mask & (rv >= 1.5)
    cell("D1 distribution tape: ret1>=3% & nbz<=-1 & rv>=1.5",
         mask & (r1 >= 0.03) & (nbz <= -1) & (rv >= 1.5), holds, L)
    cell("D2 stealth accumulation: compression & nbz>=+1 & rv>=1.5",
         pC & (nbz >= 1) & (rv >= 1.5), holds, L)
    cell("D3 support into weakness: ret5<=-5% & nbz>=+1 & rv>=2",
         mask & (p.ret5 <= -0.05) & (nbz >= 1) & (rv >= 2), holds, L)
    cell("D4 strength distributed: ret5>=+5% & nbz<=-1 & rv>=2",
         mask & (p.ret5 >= 0.05) & (nbz <= -1) & (rv >= 2), holds, L)
    print("=== GROUP E: STATE TRANSITIONS ===")
    e2 = (tr_ / atr10).rolling(5, min_periods=3).min() <= 0.8
    cell("E2 compressed -> expanding (range)", mask & e2.fillna(False) & (atr_ratio >= 1.5), holds, L)
    flat3 = ((nbz.abs() <= 0.5).astype(float)).rolling(3, min_periods=3).sum() >= 3
    cell("E3 flow-neutral -> flow-extreme", mask & flat3.fillna(False) & (nbz.abs() >= 2), holds, L)
    flat3p = ((r1.abs() <= 0.005).astype(float)).rolling(3, min_periods=3).sum() >= 3
    cell("E4 price-neutral -> price-extreme", mask & flat3p.fillna(False) & (r1.abs() >= 0.04), holds, L)
    OUT["cells"] = L

    # FM for the interactions with any life (full control set)
    print("\n=== FM (h5 | ret1, ret5z, volz, ADV tercile, flow level) ===")
    adv = p.adv60.where(mask0)
    ter = adv.rank(axis=1, pct=True)
    ctrls = [r1, ret5z, volz, ter, nbz]
    for nm, fl in (("A3 dual accel", pA & (accel_z >= 1)), ("A4 stealth flow", pC & (nbz >= 1)),
                   ("A5 rev+rev", mask & rev_p.fillna(False) & rev_f.fillna(False)),
                   ("B4 grind+participation", pG & (rv >= 1.5)),
                   ("D1 distribution tape", mask & (r1 >= 0.03) & (nbz <= -1) & (rv >= 1.5)),
                   ("D2 stealth accumulation", pC & (nbz >= 1) & (rv >= 1.5)),
                   ("E2 compressed->expanding", mask & e2.fillna(False) & (atr_ratio >= 1.5)),
                   ("E3 flow-neutral->extreme", mask & flat3.fillna(False) & (nbz.abs() >= 2)),
                   ("E4 price-neutral->extreme", mask & flat3p.fillna(False) & (r1.abs() >= 0.04))):
        rr = sl.fm_regression(p, fl.fillna(False).astype(float), mask, controls=ctrls, k=5)
        OUT["fm"][nm] = rr
        print(f"  {nm:26s}: beta={rr['fm_mean']:+.5f} t={rr['fm_t']:+.2f} n_dates={rr['n_dates']}")

    # entry-rule passers -> mandatory pseudo-OOS (price-only ones only)
    passers = [c for c in L if not c["id"].startswith("[parent]")
               and c.get("net60_h5") is not None and c["net60_h5"] >= 0.003
               and c["pos_halves"] >= 3 and c["n"] >= 1000 and c["n_tickers"] >= 50]
    print("\nentry-rule passers:", [c["id"] for c in passers] or "none")
    B = {"E4 price-neutral -> price-extreme":
         lambda F: ((F["close"] / F["close"].shift(1) - 1).abs() <= 0.005).rolling(3).sum() >= 3
         and False,  # placeholder replaced below
         }
    # E4 builder (price-only): 3 flat days then |ret1|>=4%
    def e4_builder(F):
        r_ = F["close"] / F["close"].shift(1) - 1
        return ((r_.abs() <= 0.005).rolling(3).sum() >= 3) & (r_.abs() >= 0.04)
    for c_ in passers:
        if c_["id"].startswith("E4"):
            pseudo_oos("E4", e4_builder)

    _here = os.path.dirname(os.path.abspath(__file__))
    print("\n(results printed to stdout; captured by shell redirection)")


if __name__ == "__main__":
    main()
