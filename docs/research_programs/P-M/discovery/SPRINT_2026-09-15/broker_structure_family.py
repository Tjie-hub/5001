#!/usr/bin/env python3
"""FAMILY #4: BROKER-STRUCTURE — the genuinely new representation:
per-broker investor_type classes (Asing / Lokal / Pemerintah = foreign / local /
government BROKER DOMICILE CLASS) on the frozen Dataset B IDX100 store.
Broker domicile is NOT end-investor identity (program rule). All-broker net is
identically zero per ticker-day, so Asing+Lokal+Pemerintah nets sum to 0 (2 dof).

Already tested and DEAD in prior passes (declared skip-list): aggregate top-3
lean, concentration/HHI, few-sellers, same-broker persistence, vendor bandar
labels. This family tests ONLY the investor-class split.

DECLARED TREE (12 constructions, fixed before running):
  F1  Asing net z60 >= +1 (foreign inflow)          F2  Asing net z60 <= -1 [mirror]
  F3  Asing net / ADV60 >= +5% (intensity)
  F4  disagreement: Asing net > 0 & Lokal net < 0   F4b mirror (foreign sells into local buying)
  F5  government-broker event: |Pemerintah net| >= 1% ADV60
  F6  foreign persistence: Asing net > 0 >= 3 consecutive days
  F7  foreign flip after >= 3-day run
  F8  foreign absorption: ret1 <= -1% & Asing net z >= +1
  F9  foreign distribution: ret1 >= +1% & Asing net z <= -1
  F10 foreign activity share: Asing gross / total gross z >= +2
  F11 F1 restricted to ADV top tercile
  F12 up-move x Asing-net quartile profile (informational)

EVALUATION: suspension-clean base, IDX100 universe (min 500 obs / 25 tickers),
h1/h2/h3/h5/h10/h20, half-year stability, trimmed/hit/tail at h5, FM vs
[ret1, ret5z, volz, platform nbz]. ENTRY KILL RULE as declared in prior families
(net60 h5 >= +30bp & >=3/4 halves & FM beta>0 |t|>=2 & breadth). Filter rule:
spread negative >=3/4 halves & n>=500 & survives FM incl. liquidity.
Results printed to stdout (captured by shell redirection).
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import sprint_lib as sl
from adversarial_flow import build_contam

OUT = {"audit": {}, "cells": [], "fm": {}}
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

    # ---- audit: investor_type constancy per broker ----
    c = sl.ro_conn(sl.VIEWS)
    try:
        bd = pd.read_sql_query(
            "SELECT ticker, trade_date, broker_code, investor_type, gross, net FROM v_a_broker_day", c)
    finally:
        c.close()
    bd = bd[bd.broker_code != "DM"].copy()
    types_per_broker = bd.groupby("broker_code")["investor_type"].nunique()
    OUT["audit"] = {"brokers": int(types_per_broker.shape[0]),
                    "brokers_with_multiple_types": int((types_per_broker > 1).sum()),
                    "type_counts": bd.drop_duplicates("broker_code")["investor_type"].value_counts().to_dict()}
    print("audit:", OUT["audit"])

    def cls_net(t):
        g = bd[bd.investor_type == t]
        return g.groupby(["ticker", "trade_date"])["net"].sum()

    def cls_gross(t):
        g = bd[bd.investor_type == t]
        return g.groupby(["ticker", "trade_date"])["gross"].sum()

    idx, cols = p.close.index, p.close.columns

    def pnl(s):
        return s.reset_index().pivot_table(index="trade_date", columns="ticker", values=s.name or 0, aggfunc="last") \
                .reindex(index=idx, columns=cols)

    a_net = pnl(cls_net("Asing").rename("v"))
    l_net = pnl(cls_net("Lokal").rename("v"))
    g_net = pnl(cls_net("Pemerintah").rename("v"))
    a_gr = pnl(cls_gross("Asing").rename("v"))
    tot_gr = bd.groupby(["ticker", "trade_date"])["gross"].sum()
    tot_gr_p = tot_gr.reset_index().pivot_table(index="trade_date", columns="ticker", values="gross", aggfunc="last") \
                     .reindex(index=idx, columns=cols)

    have = a_net.notna()
    bmask = mask & have
    print(f"covered liquid tradable obs: {int(bmask.values.sum())} of {int(mask.values.sum())}")

    a_z = sl.trailing_z(a_net)
    adv60 = p.adv60.reindex(index=idx, columns=cols)
    a_int = a_net / adv60
    ashare = a_gr / tot_gr.replace(0, np.nan)
    ashare_z = sl.trailing_z(ashare)
    nbz = sl.trailing_z(p.nb)
    volz = sl.trailing_z(p.volume)
    ret5z = sl.trailing_z(p.ret5)
    a_run = (a_net > 0).rolling(3).sum()
    a_sgn = np.sign(a_net)

    L = []
    print("=== FOREIGN/LOCAL/GOV CLASS CONSTRUCTIONS (h5) ===")
    cell("F1 Asing net z>=+1 (foreign inflow)", bmask & (a_z >= 1), holds, L)
    cell("F2 Asing net z<=-1 (foreign outflow) [mirror]", bmask & (a_z <= -1), holds, L)
    cell("F3 Asing net/ADV60 >= +5%", bmask & (a_int >= 0.05), holds, L)
    cell("F4 disagreement: Asing buys, Lokal sells", bmask & (a_net > 0) & (l_net < 0), holds, L)
    cell("F4b mirror: Asing sells, Lokal buys", bmask & (a_net < 0) & (l_net > 0), holds, L)
    cell("F5 Pemerintah |net| >= 1% ADV60", bmask & (g_net.abs() >= 0.01 * adv60), holds, L)
    cell("F6 foreign persistence >=3 days", bmask & (a_run >= 3), holds, L)
    cell("F7 foreign flip after >=3-day run", bmask & (a_run.shift(1) >= 3) & (a_sgn < 0), holds, L)
    cell("F8 foreign absorption: down & Asing z>=+1", bmask & (r1 <= -0.01) & (a_z >= 1), holds, L)
    cell("F9 foreign distribution: up & Asing z<=-1", bmask & (r1 >= 0.01) & (a_z <= -1), holds, L)
    cell("F10 foreign activity share z>=+2", bmask & (ashare_z >= 2), holds, L)
    ter = adv60.where(mask0).rank(axis=1, pct=True)
    cell("F11 F1 & ADV top tercile", bmask & (a_z >= 1) & (ter >= 0.667).fillna(False), holds, L)
    print("  [F12 up-move x Asing-net quartile profile]")
    q = a_z.where((r1 >= 0.01).fillna(False)).rank(axis=1, pct=True)
    for qa, lab in ((0.0, "Q1 most-negative"), (0.25, "Q2"), (0.5, "Q3"), (0.75, "Q4 most-positive")):
        sel = bmask & (r1 >= 0.01) & (q > qa)
        v = holds[5][sel].values; v = v[~np.isnan(v)]
        print(f"    up-move {lab:18s}: n={len(v):6d} h5={np.mean(v):+.4f}" if len(v) > 30 else f"    {lab}: n<30")
    OUT["cells"] = L

    print("\n=== FM INCREMENTALITY (h5 | ret1, ret5z, volz, platform nbz) ===")
    ctrls = [r1, ret5z, volz, nbz]
    for nm, fl in (("F1 Asing z>=+1", (a_z >= 1)), ("F2 Asing z<=-1", (a_z <= -1)),
                   ("F3 Asing/ADV>=5%", (a_int >= 0.05)),
                   ("F4 disagreement", ((a_net > 0) & (l_net < 0))), ("F6 persistence>=3", (a_run >= 3)),
                   ("F8 foreign absorption", ((r1 <= -0.01) & (a_z >= 1))),
                   ("F9 foreign distribution", ((r1 >= 0.01) & (a_z <= -1))),
                   ("F10 share z>=2", (ashare_z >= 2))):
        rr = sl.fm_regression(p, fl.fillna(False).astype(float), bmask, controls=ctrls, k=5)
        OUT["fm"][nm] = rr
        print(f"  {nm:26s}: beta={rr['fm_mean']:+.5f} t={rr['fm_t']:+.2f} n_dates={rr['n_dates']}")


if __name__ == "__main__":
    main()
