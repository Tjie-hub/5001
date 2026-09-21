#!/usr/bin/env python3
"""FAMILY #2: PRICE / PRICE-STRUCTURE — systematic discovery pass.

PREDECLARED TREE (fixed before running). Daily OHLCV grain only; minute-grain
intraday price structure is declared out of scope for this family (adjacent to
the killed I7/D-family constructions; may be revisited only if daily shows a
survivor needing finer execution study).

  Gaps:
    P1  overnight gap >= +2%          P2  overnight gap <= -2% [mirror]
  Close location / range quality:
    P3  CLV >= 0.9 & range >= median  P4  CLV <= 0.1
  Volatility expansion / compression:
    P5  range/ATR10 >= 1.8 & up day   P6  range/ATR10 >= 1.8 & down day [mirror]
    P7  compression: range/ATR10 <= 0.7 (NR7-style)
  Runs:
    P8  >=4 up closes of last 5
  Structure:
    P9  inside bar                    P10 20d-high breakout (close = new 20d high)
    P11 20d-low breakdown [mirror]
  Overnight/intraday decomposition (5d cumulative):
    P12 overnight-heavy 5d (ovt - intraday >= +2%)   P13 intraday-heavy 5d [mirror]
  Wicks:
    P14 hammer (lower wick >=60% of range, range >=1.5xATR10, ret1<0)
    P15 shooting star (upper wick >=60%, range >=1.5xATR10, ret1>0) [mirror]
  Breakout from compression:
    P16 box breakout: new 20d high & prior 10d range width in bottom tercile of own 60d
  Price x volume confirmation (declared interaction branch, minimal):
    P17 unconfirmed up-move: ret1>=+3% & volz<=0      P18 confirmed: ret1>=+3% & volz>=+1

EVALUATION: suspension-clean liquid base; horizons h1/h2/h3/h5/h10/h20; half-year
stability; trimmed/median/hit/tail at h5; FM incrementality vs [ret1, ret5z,
volz, platform nbz]. ENTRY KILL RULE (declared): net-of-60bp h5 >= +30bp AND
>=3/4 positive halves AND FM beta>0 with |t|>=2 AND n>=1000/50 tickers AND
**pseudo-OOS 2021-07..2024-12 positive** (mandatory for price-only signals).
MIRROR/downside cells are evaluated for the avoidance reading only.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import sprint_lib as sl
from adversarial_flow import build_contam

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = {"cells": [], "oos": {}}
HK = (1, 2, 3, 5, 10, 20)


def cell(name, sel, holds, ledger):
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
        row.update({"med5": float(np.median(vv)), "trim5": float(np.mean(vv[(vv >= lo) & (vv <= vv.__class__(hi))])) if False else float(np.mean(vv[(vv >= lo) & (vv <= hi)])),
                    "hit5": float((vv > 0).mean()),
                    "top1_share": float(srt[-m:].sum() / tot) if tot > 0 else None,
                    "bot1_share": float(srt[:m].sum() / abs(tot)) if tot < 0 else None,
                    "net60_h5": row["h5"] - 0.006, "net60_h10": (row["h10"] - 0.006) if row["h10"] is not None else None,
                    "n_tickers": int(sel.any(axis=0).sum())})
        sp = {}
        for lab, (a, b) in {"25H1": ("2025-01-01", "2025-07-01"), "25H2": ("2025-07-01", "2026-01-01"),
                            "26H1": ("2026-01-01", "2026-07-01"), "26H2": ("2026-07-01", "2026-12-31")}.items():
            x = r5[(r5.index >= a) & (r5.index < b)].values; x = x[~np.isnan(x)]
            sp[lab] = round(float(np.mean(x)), 5) if len(x) > 30 else None
        row["subs"] = sp
        row["pos_halves"] = sum(1 for x in sp.values() if x is not None and x > 0)
    fmt = lambda x, f="+.4f": ("None" if x is None else x.__format__(f))
    print(f"  {name:44s} n={row['n']:6d} h5={fmt(row.get('h5'))} net={fmt(row.get('net60_h5'))} "
          f"med={fmt(row.get('med5'))} trim={fmt(row.get('trim5'))} hit={fmt(row.get('hit5'),'.3f')} "
          + (f"halves={row['pos_halves']}/4 subs={[None if x is None else round(x,4) for x in row['subs'].values()]}" if "subs" in row else ""))
    ledger.append(row)
    return row


def pseudo_oos(p, sel_builder, name):
    """2021-07..2024-12 replication for a price-only signal. sel_builder(full) -> bool panel."""
    c = sl.ro_conn(sl.WF)
    try:
        ohl = pd.read_sql_query("SELECT ticker, date, open, high, low, close, volume FROM ohlcv "
                                "WHERE is_final=1 AND close>0 ORDER BY ticker, date", c)
    finally:
        c.close()
    ohl["traded_value"] = ohl["close"] * ohl["volume"]
    adj = sl.build_adjusted(ohl, sl.load_corporate_actions())
    full = {"close": sl.to_panel(adj, "close"), "open": sl.to_panel(adj, "open"),
            "high": sl.to_panel(adj, "high"), "low": sl.to_panel(adj, "low"),
            "ret": sl.to_panel(adj, "ret"), "volume": sl.to_panel(adj, "volume"),
            "tv": sl.to_panel(adj, "traded_value")}
    full["liq"] = sl.trailing_median_panel(full["tv"]) >= sl.LIQ_FLOOR
    full["tradable"] = full["liq"] & (full["volume"].shift(-1) > 0)
    cum = (full["ret"] + 1.0).cumprod()
    full["h5"] = cum.shift(-6) / cum.shift(-1) - 1.0
    full["h10"] = cum.shift(-11) / cum.shift(-1) - 1.0
    out = {}
    for era, lo, hi in (("2021H2-2022", "2021-07-01", "2023-01-01"), ("2023-2024", "2023-01-01", "2025-01-01")):
        sel = sel_builder(full)
        sel = sel[(sel.index >= lo) & (sel.index < hi)]
        for k in (5, 10):
            v = full[f"h{k}"][sel].values; v = v[~np.isnan(v)]
            out[f"{era}_h{k}"] = {"n": len(v), "mean": float(np.mean(v)) if len(v) else None}
    print(f"  OOS[{name}]: " + " | ".join(f"{k}: n={v['n']} h={None if v['mean'] is None else round(v['mean'],4)}"
                                          for k, v in out.items()))
    OUT["oos"][name] = out
    return out


def main():
    p = sl.SprintPanel()
    mask0 = p.mask_base()
    r1 = p.ret1
    _cum = (p.ret + 1.0).cumprod()
    holds = {k: p.hold[k] if k in p.hold else _cum.shift(-1 - k) / _cum.shift(-1) - 1.0 for k in HK}
    clean = ~build_contam(p)
    mask = mask0 & clean

    op = sl.to_panel(p.adj[p.adj.date >= "2024-06-01"], "open")
    hi = sl.to_panel(p.adj[p.adj.date >= "2024-06-01"], "high")
    lo = sl.to_panel(p.adj[p.adj.date >= "2024-06-01"], "low")
    cl = p.close
    pc = cl.shift(1)
    rng = (hi - lo).replace(0, np.nan)
    gap = op / pc - 1.0
    clv = (cl - lo) / rng
    tr = (hi - lo) / cl
    atr10 = tr.rolling(10, min_periods=6).mean()
    atr_ratio = tr / atr10.shift(1)
    up = (cl > pc).astype(float)
    streak5 = up.rolling(5).sum()
    inside = (hi < hi.shift(1)) & (lo > lo.shift(1))
    hi20 = hi.rolling(20, min_periods=15).max()
    lo20 = lo.rolling(20, min_periods=15).min()
    new_high = cl >= hi20
    new_low = cl <= lo20
    ovt_d = op / pc - 1.0
    int_d = cl / op - 1.0
    ovt5 = ((ovt_d + 1).rolling(5, min_periods=3).apply(np.prod, raw=True) - 1)
    int5 = ((int_d + 1).rolling(5, min_periods=3).apply(np.prod, raw=True) - 1)
    rng_size = rng
    body_top = np.maximum(op, cl)
    body_bot = np.minimum(op, cl)
    up_wick = (hi - body_top) / rng
    lo_wick = (body_bot - lo) / rng
    width10 = (hi.rolling(10).max() - lo.rolling(10).min()) / cl
    width_ter = width10 / (width10.rolling(60, min_periods=30).quantile(0.5).shift(1))  # vs own trailing median
    volz = sl.trailing_z(p.volume)
    ret5z = sl.trailing_z(p.ret5)
    nbz = sl.trailing_z(p.nb)

    L = []
    print("--- GAPS ---")
    cell("P1 gap>=+2%", mask & (gap >= 0.02), holds, L)
    cell("P2 gap<=-2% [mirror]", mask & (gap <= -0.02), holds, L)
    print("--- CLOSE LOCATION ---")
    med_rng = (rng >= rng.rolling(60, min_periods=30).median().shift(1))
    cell("P3 CLV>=0.9 & real range", mask & (clv >= 0.9) & med_rng.fillna(False), holds, L)
    cell("P4 CLV<=0.1", mask & (clv <= 0.1) & med_rng.fillna(False), holds, L)
    print("--- VOL EXPANSION / COMPRESSION ---")
    cell("P5 range>=1.8xATR & up", mask & (atr_ratio >= 1.8) & (cl > op), holds, L)
    cell("P6 range>=1.8xATR & down [mirror]", mask & (atr_ratio >= 1.8) & (cl <= op), holds, L)
    cell("P7 compression <=0.7xATR (NR7)", mask & (atr_ratio <= 0.7), holds, L)
    print("--- RUNS ---")
    cell("P8 up-run >=4 of 5", mask & (streak5 >= 4), holds, L)
    print("--- STRUCTURE ---")
    cell("P9 inside bar", mask & inside.fillna(False), holds, L)
    cell("P10 new 20d-high close", mask & new_high.fillna(False), holds, L)
    cell("P11 new 20d-low close [mirror]", mask & new_low.fillna(False), holds, L)
    print("--- OVERNIGHT/INTRADAY 5d DECOMPOSITION ---")
    cell("P12 overnight-heavy 5d (ovt-int>=+2%)", mask & ((ovt5 - int5) >= 0.02), holds, L)
    cell("P13 intraday-heavy 5d (int-ovt>=+2%)", mask & ((int5 - ovt5) >= 0.02), holds, L)
    print("--- WICKS ---")
    cell("P14 hammer (rejection in down-move)", mask & (lo_wick >= 0.6) & (atr_ratio >= 1.5) & (r1 < 0), holds, L)
    cell("P15 shooting star [mirror]", mask & (up_wick >= 0.6) & (atr_ratio >= 1.5) & (r1 > 0), holds, L)
    print("--- COMPRESSION BREAKOUT ---")
    cell("P16 box breakout (new high & compressed)", mask & new_high.fillna(False) & (width_ter <= 0.75).fillna(False), holds, L)
    print("--- PRICE x VOLUME CONFIRMATION ---")
    up3 = (r1 >= 0.03) & mask
    cell("P17 up-move>=3% & volz<=0 (unconfirmed)", up3 & (volz <= 0), holds, L)
    cell("P18 up-move>=3% & volz>=+1 (confirmed)", up3 & (volz >= 1), holds, L)
    OUT["cells"] = L

    # ---------- FM incrementality for anything near the kill rule ----------
    print("\n--- FM INCREMENTALITY (h5 | ret1, ret5z, volz, platform nbz) ---")
    fm_out = {}
    ctrls = [r1, ret5z, volz, nbz]
    for nm, flag in (("P1 gap>=+2%", (gap >= 0.02)), ("P3 CLV>=0.9", (clv >= 0.9)),
                     ("P5 range-exp up", ((atr_ratio >= 1.8) & (cl > op))),
                     ("P7 compression", (atr_ratio <= 0.7)), ("P8 up-run>=4", (streak5 >= 4)),
                     ("P10 new 20d-high", new_high.fillna(False)),
                     ("P12 overnight-heavy", ((ovt5 - int5) >= 0.02)),
                     ("P13 intraday-heavy", ((int5 - ovt5) >= 0.02)),
                     ("P16 box breakout", (new_high.fillna(False) & (width_ter <= 0.75).fillna(False)))):
        rr = sl.fm_regression(p, flag.fillna(False).astype(float), mask, controls=ctrls, k=5)
        fm_out[nm] = rr
        print(f"  {nm:24s}: beta={rr['fm_mean']:+.5f} t={rr['fm_t']:+.2f} n={rr['n_dates']}")
    OUT["fm"] = fm_out

    # ---------- mandatory pseudo-OOS for anything near the entry rule ----------
    print("\n--- PSEUDO-OOS 2021-07..2024-12 (mandatory for entry-rule passers) ---")
    oos_cands = [c for c in L if c.get("net60_h5") is not None and c["net60_h5"] >= 0.003 and c["pos_halves"] >= 3]
    print("  near-rule candidates:", [c["id"] for c in oos_cands] or "none")
    builders = {
        "P7 compression": lambda F: F["tradable"] & ((F["high"] - F["low"]).div(F["close"]) /
                ((F["high"] - F["low"]).div(F["close"])).rolling(10, min_periods=6).mean().shift(1) <= 0.7),
        "P9 inside bar": lambda F: F["tradable"] & (F["high"] < F["high"].shift(1)) & (F["low"] > F["low"].shift(1)),
        "P13 intraday-heavy": lambda F: F["tradable"] & ((((F["close"] / F["open"] - 1) + 1).rolling(5, min_periods=3).apply(np.prod, raw=True) - 1)
                                  - (((F["open"] / F["close"].shift(1) - 1) + 1).rolling(5, min_periods=3).apply(np.prod, raw=True) - 1) >= 0.02),
        "P16 box breakout": lambda F: F["tradable"] & (F["close"] >= (F["high"].rolling(20, min_periods=15).max()))
                                & (((F["high"].rolling(10).max() - F["low"].rolling(10).min()) / F["close"])
                                   / (((F["high"].rolling(10).max() - F["low"].rolling(10).min()) / F["close"])
                                      .rolling(60, min_periods=30).quantile(0.5).shift(1)) <= 0.75),
    }
    for c_ in oos_cands:
        nm = c_["id"].split(" ")[0]
        if nm in builders:
            pseudo_oos(p, builders[nm], nm)

    _here = os.path.dirname(os.path.abspath(__file__))
    _cache = os.path.normpath(os.path.join(_here, "cache"))
    _out = os.path.normpath(os.path.join(_cache, "price_family.json"))
    if os.path.commonpath([_here, _out]) != _here:
        raise SystemExit("refusing to write outside the sprint directory")
    with open(_out, "w") as f:
        json.dump(OUT, f, indent=1, default=str)
    print("\nsaved -> cache/price_family.json")


if __name__ == "__main__":
    main()
