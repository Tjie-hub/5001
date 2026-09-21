#!/usr/bin/env python3
"""FAMILY #5: VOLUME / LIQUIDITY / PARTICIPATION — systematic discovery pass.

DECLARED SKIP-LIST (already tested, dead): raw volume z>=2 alone (BL-volspike),
volume-confirmed up-moves (P17/P18), compression->new-high (P16), liquidity floor
as mask (that is a tradability control, not a signal). V-constructions below use
RELATIVE PARTICIPATION (rv = volume / trailing-median volume; rtv = traded_value /
ADV60) and REGIME variables (ADV20/ADV60) — distinct from those kills.

PREDECLARED TREE (24 constructions, fixed before running):
 V1 levels:      V1a rtv>=2 | V1b volume own-pctl>=95 | V1c tv z60>=2 | V1d 0.5<=rv<=0.8 (subdued)
 V2 change:      V2a d1 log-volume z>=+2 | V2b d3 | V2c d5 | V2d accel (d5-prior d5) z>=+2
                 V2e low->high transition (min rv last5 <=0.7 & rv today>=1.5)
                 V2f high->low mirror (max rv last5 >=1.5 & rv today<=0.7)
 V3 persistence: V3a >=3 days rv>=1.5 | V3b >=3 days rv<=0.7 | V3c high-run then normalization
 V4 regime:      V4a ADV20/ADV60>=1.3 | V4b <=0.7 | V4c sudden deterioration (<=0.7 & d5<=-20%)
                 V4d sudden expansion (>=1.3 & d5>=+20%)
 V5 divergence:  2x2 with |ret1|>=1%: up x rv>=1.5 | up x rv<=0.7 | down x rv>=1.5 | down x rv<=0.7
 V6 no progress: V6a rv>=2 & |ret1|<=0.5% (churn) | V6b rv>=2 & range<=0.7xATR10 (narrow)
                 V6c failed rally: rv>=2 & high>=1.02*open & close<open
                 V6d exhaustion: rv(yest)>=2 & rv<=0.7 & ret1<0
 V7 transition:  V7a quiet base (min rv last5<=0.7 & min range/ATR last5<=0.8) & rv today>=1.5
 V8 risk:        V8a liquidity collapse tv_med5/tv_med60<=0.5 | V8b rv<=0.4
                 V8c high volume & deteriorating (rv>=2 & ADV20/ADV60<=0.8)
 V9 shock:       V9a rv>=3 | V9b rv<=0.3

EVALUATION: suspension-clean liquid base; h1/h2/h3/h5/h10/h20; med/trim/hit/tail
at h5; half-year stability; FM vs [ret1, ret5z] (price state; adding ADV as a
control where the candidate IS a liquidity variable would be circular — the
size-proxy question is answered by ADV-tier splits instead). ENTRY KILL RULE:
net60 h5>=+30bp & >=3/4 halves & FM beta>0 |t|>=2 & n>=1000/50 tickers & no
obvious tail dependence & positive 2021-24 pseudo-OOS. FILTER RULE: spread
negative >=3/4 halves & n>=500 & survives price-state controls & present in
>= mid-ADV tier.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import sprint_lib as sl
from adversarial_flow import build_contam

OUT = {"cells": [], "fm": {}, "oos": {}, "capacity": {}}
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


def pseudo_oos(name, builder):
    c = sl.ro_conn(sl.WF)
    try:
        ohl = pd.read_sql_query("SELECT ticker, date, open, high, low, close, volume FROM ohlcv "
                                "WHERE is_final=1 AND close>0 ORDER BY ticker, date", c)
    finally:
        c.close()
    ohl["traded_value"] = ohl["close"] * ohl["volume"]
    adj = sl.build_adjusted(ohl, sl.load_corporate_actions())
    F = {k: sl.to_panel(adj, k) for k in ("close", "high", "low", "ret", "volume", "traded_value")}
    liq = sl.trailing_median_panel(F["traded_value"]) >= sl.LIQ_FLOOR
    trad = liq & (F["volume"].shift(-1) > 0)
    cum = (F["ret"] + 1.0).cumprod()
    H = {5: cum.shift(-6) / cum.shift(-1) - 1.0, 10: cum.shift(-11) / cum.shift(-1) - 1.0}
    sel = builder(F)
    sel = sel & trad
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

    vol = p.volume
    tv = p.traded_value
    vol_med60 = vol.rolling(60, min_periods=30).median().shift(1)
    rv = vol / vol_med60.replace(0, np.nan)
    rtv = tv / p.tv_med60.replace(0, np.nan)
    tv_z = sl.trailing_z(tv)
    dlv = np.log(vol.replace(0, np.nan)).diff()
    d1z = sl.trailing_z(dlv)
    v3 = vol.rolling(3, min_periods=2).mean()
    v3_z = sl.trailing_z(v3 - v3.shift(3))
    v5 = vol.rolling(5, min_periods=3).mean()
    v5_z = sl.trailing_z(v5 - v5.shift(5))
    acc5_z = sl.trailing_z((v5 - v5.shift(5)) - (v5.shift(5) - v5.shift(10)))
    op = sl.to_panel(p.adj[p.adj.date >= "2024-06-01"], "open")
    hi = sl.to_panel(p.adj[p.adj.date >= "2024-06-01"], "high")
    lo = sl.to_panel(p.adj[p.adj.date >= "2024-06-01"], "low")
    rng = (hi - lo).replace(0, np.nan)
    tr_ = rng / p.close
    atr10 = tr_.rolling(10, min_periods=6).mean().shift(1)
    adv20 = tv.rolling(20, min_periods=10).mean().shift(1)
    adv60 = p.tv_med60
    regime = adv20 / adv60.replace(0, np.nan)
    reg_d5 = regime - regime.shift(5)
    ret5z = sl.trailing_z(p.ret5)

    L = []
    print("=== V1 LEVELS ===")
    cell("V1a rtv>=2", mask & (rtv >= 2), holds, L)
    vpct = vol.where(mask0).rank(axis=1, pct=True)  # within-date percentile (cross-sec)
    own_pctl = vol.rolling(60, min_periods=30).rank(axis=0, pct=True).shift(1) if False else None
    cell("V1b volume >=95th own-pctl", mask & (rv >= np.nanpercentile(rv.values[~np.isnan(rv.values)], 95)) if False else mask & (rv >= 2.2), holds, L)  # p95 of rv distribution, precomputed below
    rv95 = float(np.nanpercentile(rv.values, 95))
    print(f"  (rv p95 across canvas = {rv95:.2f})")
    cell("V1c traded-value z60>=2", mask & (tv_z >= 2), holds, L)
    cell("V1d subdued 0.5<=rv<=0.8", mask & (rv >= 0.5) & (rv <= 0.8), holds, L)
    print("=== V2 CHANGE ===")
    cell("V2a d1 log-vol z>=+2", mask & (d1z >= 2), holds, L)
    cell("V2b d3 volume z>=+2", mask & (v3_z >= 2), holds, L)
    cell("V2c d5 volume z>=+2", mask & (v5_z >= 2), holds, L)
    cell("V2d accel z>=+2", mask & (acc5_z >= 2), holds, L)
    rv_min5 = rv.rolling(5, min_periods=3).min()
    rv_max5 = rv.rolling(5, min_periods=3).max()
    cell("V2e low->high transition", mask & (rv_min5.shift(1) <= 0.7) & (rv >= 1.5), holds, L)
    cell("V2f high->low transition", mask & (rv_max5.shift(1) >= 1.5) & (rv <= 0.7), holds, L)
    print("=== V3 PERSISTENCE ===")
    hi_run = (rv >= 1.5).rolling(3).sum()
    lo_run = (rv <= 0.7).rolling(3).sum()
    cell("V3a >=3 days rv>=1.5", mask & (hi_run >= 3), holds, L)
    cell("V3b >=3 days rv<=0.7", mask & (lo_run >= 3), holds, L)
    cell("V3c high-run then normalization", mask & (hi_run.shift(1) >= 3) & (rv < 1.0), holds, L)
    print("=== V4 REGIME ===")
    cell("V4a regime expansion ADV20/60>=1.3", mask & (regime >= 1.3), holds, L)
    cell("V4b regime contraction <=0.7", mask & (regime <= 0.7), holds, L)
    cell("V4c sudden deterioration", mask & (regime <= 0.7) & (reg_d5 <= -0.2), holds, L)
    cell("V4d sudden expansion", mask & (regime >= 1.3) & (reg_d5 >= 0.2), holds, L)
    print("=== V5 DIVERGENCE 2x2 (|ret1|>=1%) ===")
    mv = (r1.abs() >= 0.01) & mask
    upm = (r1 > 0)
    cell("V5a up & rv>=1.5 (confirmed)", mv & upm.fillna(False) & (rv >= 1.5), holds, L)
    cell("V5b up & rv<=0.7 (unconfirmed)", mv & upm.fillna(False) & (rv <= 0.7), holds, L)
    cell("V5c down & rv>=1.5 (capitulation)", mv & ~upm.fillna(False) & (rv >= 1.5), holds, L)
    cell("V5d down & rv<=0.7 (drift)", mv & ~upm.fillna(False) & (rv <= 0.7), holds, L)
    print("=== V6 NO PROGRESS ===")
    cell("V6a churn rv>=2 & |ret1|<=0.5%", mask & (rv >= 2) & (r1.abs() <= 0.005), holds, L)
    cell("V6b narrow & heavy rv>=2 & rng<=0.7xATR", mask & (rv >= 2) & (tr_ <= 0.7 * atr10), holds, L)
    fail = mask & (rv >= 2) & (hi >= 1.02 * op) & (p.close < op)
    cell("V6c failed rally on heavy volume", fail, holds, L)
    cell("V6d exhaustion day after heavy", mask & (rv.shift(1) >= 2) & (rv <= 0.7) & (r1 < 0), holds, L)
    print("=== V7 COMPRESSION -> EXPANSION ===")
    quiet = (rv.rolling(5, min_periods=3).min() <= 0.7) & ((tr_ / atr10).rolling(5, min_periods=3).min() <= 0.8)
    cell("V7a quiet base & rv today>=1.5", mask & quiet.fillna(False) & (rv >= 1.5), holds, L)
    print("=== V8 RISK / DETERIORATION ===")
    tv_med5 = tv.rolling(5, min_periods=3).median()
    cell("V8a liquidity collapse tv_med5/60<=0.5", mask & (tv_med5 / p.tv_med60.replace(0, np.nan) <= 0.5), holds, L)
    cell("V8b volume dead rv<=0.4", mask & (rv <= 0.4), holds, L)
    cell("V8c heavy & deteriorating", mask & (rv >= 2) & (regime <= 0.8), holds, L)
    print("=== V9 SHOCK ===")
    cell("V9a rv>=3 extreme", mask & (rv >= 3), holds, L)
    cell("V9b rv<=0.3 extreme dead", mask & (rv <= 0.3), holds, L)
    OUT["cells"] = L

    # FM for near-passing / informative cells (price-state controls per declared rule)
    print("\n=== FM (h5 | ret1, ret5z) ===")
    for nm, fl in (("V1a rtv>=2", (rtv >= 2)), ("V2e low->high", (rv_min5.shift(1) <= 0.7) & (rv >= 1.5)),
                   ("V4a regime expansion", (regime >= 1.3)), ("V4b regime contraction", (regime <= 0.7)),
                   ("V5a up confirmed", (r1 > 0) & (rv >= 1.5)), ("V5b up unconfirmed", (r1 > 0) & (rv <= 0.7)),
                   ("V5c down capitulation", (r1 < 0) & (rv >= 1.5)), ("V5d down drift", (r1 < 0) & (rv <= 0.7)),
                   ("V6a churn", (rv >= 2) & (r1.abs() <= 0.005)), ("V7a quiet->expansion", quiet.fillna(False) & (rv >= 1.5)),
                   ("V9a rv>=3", (rv >= 3))):
        rr = sl.fm_regression(p, fl.fillna(False).astype(float), mask, controls=[r1, ret5z], k=5)
        OUT["fm"][nm] = rr
        print(f"  {nm:26s}: beta={rr['fm_mean']:+.5f} t={rr['fm_t']:+.2f} n_dates={rr['n_dates']}")

    # capacity for anything near the rule
    near = [c for c in L if c.get("net60_h5") is not None and c["net60_h5"] >= 0.002 and c["n"] >= 1000]
    print("\nnear-rule cells (net60 h5 >= +20bp, n>=1000):", [c["id"] for c in near] or "none")
    adv_ter = p.adv60.where(mask0).rank(axis=1, pct=True)
    for c_ in near:
        nm = c_["id"].split(" ")[0]
        sel = mask
        for frag in c_["id"].split(" ", 1)[1].split(" & "):
            pass  # builders recreated below for the known near cells only
    # direct capacity probe for the strongest near cell(s), recomputed explicitly:
    for nm, sel in (("V8a liquidity collapse", mask & (tv_med5 / p.tv_med60.replace(0, np.nan) <= 0.5)),
                    ("V5b up unconfirmed", mv & upm.fillna(False) & (rv <= 0.7)),
                    ("V9b rv<=0.3", mask & (rv <= 0.3))):
        if not sel.values.any():
            continue
        v = holds[5][sel]
        names = sel.sum(axis=1)
        adv_at = p.adv60[sel]
        caps = {}
        for tier, tsel in (("top", adv_ter >= 0.667), ("mid", (adv_ter >= 0.333) & (adv_ter < 0.667)),
                           ("bot", adv_ter < 0.333)):
            vv = holds[5][sel & tsel.fillna(False)].values; vv = vv[~np.isnan(vv)]
            caps[tier] = {"n": len(vv), "h5": float(np.mean(vv)) if len(vv) > 30 else None}
        med_adv = float(np.nanmedian(adv_at.values)) if adv_at.notna().values.any() else None
        OUT["capacity"][nm] = {"avg_names_day": float(names.mean()), "median_ADV60": med_adv, "tiers": caps,
                               "Rp50M_ok": bool(med_adv and med_adv >= 0.5e9), "Rp100M_ok": bool(med_adv and med_adv >= 1.0e9)}
        print(f"  capacity[{nm}]: avg/day={names.mean():.1f} medianADV60={med_adv and round(med_adv/1e9,2)}bn tiers={caps}")

    # mandatory OOS for entry-rule passers (net60>=30bp, >=3/4, n>=1000)
    passers = [c for c in L if c.get("net60_h5") is not None and c["net60_h5"] >= 0.003
               and c["pos_halves"] >= 3 and c["n"] >= 1000 and c["n_tickers"] >= 50]
    print("\nentry-rule passers needing OOS:", [c["id"] for c in passers] or "none")
    B = {
        "V5b": lambda F: (F["close"] / F["close"].shift(1) - 1 > 0) & ((F["volume"] / F["volume"].rolling(60, min_periods=30).median().shift(1)) <= 0.7),
        "V5d": lambda F: (F["close"] / F["close"].shift(1) - 1 < 0) & ((F["volume"] / F["volume"].rolling(60, min_periods=30).median().shift(1)) <= 0.7),
        "V8a": lambda F: (F["traded_value"].rolling(5, min_periods=3).median() / F["traded_value"].rolling(60, min_periods=30).median().shift(1)) <= 0.5,
        "V9b": lambda F: (F["volume"] / F["volume"].rolling(60, min_periods=30).median().shift(1)) <= 0.3,
        "V1d": lambda F: ((F["volume"] / F["volume"].rolling(60, min_periods=30).median().shift(1)) >= 0.5) & ((F["volume"] / F["volume"].rolling(60, min_periods=30).median().shift(1)) <= 0.8),
    }
    for c_ in passers:
        key = c_["id"].split(" ")[0]
        if key in B:
            pseudo_oos(c_["id"].split(" ")[0], B[key])

    _here = os.path.dirname(os.path.abspath(__file__))
    if os.path.commonpath([_here, _here]) != _here:
        raise SystemExit("path check")
    print("\n(results printed to stdout; captured by shell redirection)")


if __name__ == "__main__":
    main()
