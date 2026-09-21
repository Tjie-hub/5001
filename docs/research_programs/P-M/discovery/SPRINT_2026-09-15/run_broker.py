#!/usr/bin/env python3
"""Discovery sprint — broker-grain candidates (families B, C2/C3) on the
frozen Dataset B IDX100 store. Broker DM excluded.

Direction note: the all-broker net is identically zero at ticker-day level
(frozen Dataset B invariant), so directional lean is defined as the NET OF THE
TOP-3 GROSS BROKERS (a subset — well-defined). bandar_topK_accdist numeric
columns are empty in the store (vendor label text instead); the label regime
from production bandar_detector is used as the B3 event flag instead.
Long-only, same mask/forward-return/cost conventions as run_daily.py."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import sprint_lib as sl

LEDGER = []


def z(panel):
    return sl.trailing_z(panel)


def main():
    p = sl.SprintPanel()
    mask = p.mask_base()
    r1 = p.ret1
    idx, cols = p.close.index, p.close.columns

    # ---- directional lean: net of top-3 gross brokers per ticker-day
    bd = sl.load_broker_day()
    tot = bd.groupby(["ticker", "trade_date"]).gross.sum().rename("tot")
    bd = bd.merge(tot, on=["ticker", "trade_date"])
    bd = bd.sort_values(["ticker", "trade_date", "gross"], ascending=[True, True, False])
    bd["rk"] = bd.groupby(["ticker", "trade_date"]).cumcount()
    lean = (bd[bd.rk < 3].groupby(["ticker", "trade_date"]).net.sum()
            .rename("lean").reset_index())

    conc = sl.load_concentration()
    for ccol in conc.columns:
        if ccol not in ("ticker", "trade_date"):
            conc[ccol] = pd.to_numeric(conc[ccol], errors="coerce")
    conc = conc.merge(lean, on=["ticker", "trade_date"], how="left")

    def panelize(col, src):
        return src.pivot_table(index="trade_date", columns="ticker", values=col, aggfunc="last")

    top3 = panelize("top3_gross_share", conc).reindex(index=idx, columns=cols)
    hhi = panelize("hhi_gross", conc).reindex(index=idx, columns=cols)
    nsell = panelize("n_sell_brokers", conc).reindex(index=idx, columns=cols)
    leanp = panelize("lean", conc).reindex(index=idx, columns=cols)
    lean_z = z(leanp)
    adv60 = p.adv60.reindex(index=idx, columns=cols)
    have = leanp.notna()
    bmask = mask & have

    # ---- B1: concentration z + dominant-broker lean
    t3z = z(top3)
    for zt in (1.0, 1.5):
        sig = t3z.where((t3z >= zt) & (lean_z >= 1.0), 0.0)
        sl.eval_signal(f"B1-top3conc+lean_z{zt}", sig, bmask, p, LEDGER,
                       {"family": "B", "def": f"z60(top3_gross_share)>={zt} & z60(top3_brokers_net)>=1",
                        "source": "Dataset B v_b_concentration + v_a_broker_day",
                        "grain": "ticker-day (IDX100)"}, min_obs=500, min_tickers=25)
    # ---- B2: HHI + lean
    hz = z(hhi)
    for zt in (1.0, 1.5):
        sig = hz.where((hz >= zt) & (lean_z >= 1.0), 0.0)
        sl.eval_signal(f"B2-hhi+lean_z{zt}", sig, bmask, p, LEDGER,
                       {"family": "B", "def": f"z60(hhi_gross)>={zt} & z60(top3_brokers_net)>=1",
                        "grain": "ticker-day (IDX100)"}, min_obs=500, min_tickers=25)
    # ---- B3': bandar regime label events (production bandar_detector)
    import sqlite3
    c = sqlite3.connect("file:" + sl.WF + "?mode=ro", uri=True)
    try:
        c.execute("PRAGMA query_only = ON;")
        bdet = pd.read_sql_query(
            "SELECT ticker, trade_date, top3_accdist AS regime FROM bandar_detector", c)
    finally:
        c.close()
    for label, lab_id in (("Big Acc", "B3-bandar-bigacc"), ("Big Dist", "B3b-bandar-bigdist[MIRROR]")):
        bdet["flag"] = (bdet.regime == label).astype(float)
        fl = panelize("flag", bdet).reindex(index=idx, columns=cols)
        sl.eval_signal(lab_id, fl, bmask, p, LEDGER,
                       {"family": "B", "def": f"long ticker-days where bandar regime == '{label}'"
                        + (" (mirror: label precedes rebound?)" if label != "Big Acc" else ""),
                        "grain": "ticker-day (IDX100)"}, direction=1,
                       min_obs=500, min_tickers=25)
    # ---- B4: few sellers (date pct-rank) + lean
    pct = nsell.rank(axis=1, pct=True)
    for pt in (0.2, 0.4):
        sig = (1.0 - pct).where((pct <= pt) & (lean_z >= 1.0), 0.0)
        sl.eval_signal(f"B4-few-sellers_{pt}", sig, bmask, p, LEDGER,
                       {"family": "B", "def": f"n_sell_brokers date-pctrank<={pt} & z60(top3_brokers_net)>=1",
                        "grain": "ticker-day (IDX100)"}, min_obs=500, min_tickers=25)
    # ---- B5: B1 restricted to below-median ADV
    med_adv = adv60.median(axis=1)
    small = adv60.lt(med_adv, axis=0)
    sig = t3z.where((t3z >= 1.5) & (lean_z >= 1.0) & small, 0.0)
    sl.eval_signal("B5-top3conc+lean+smallADV", sig, bmask, p, LEDGER,
                   {"family": "B", "def": "B1(1.5) restricted to ADV60 < cross-sec median",
                    "grain": "ticker-day (IDX100)"}, min_obs=500, min_tickers=25)
    # ---- broker baseline: lean alone
    sig = lean_z.where(lean_z >= 2.0, 0.0)
    sl.eval_signal("BL-broker-lean-z2", sig, bmask, p, LEDGER,
                   {"family": "BL", "def": "z60(top3_brokers_net)>=2 (unconditioned)",
                    "grain": "ticker-day (IDX100)"}, min_obs=500, min_tickers=25)

    # ---- C2: same-broker persistence, two intensities
    cal = pd.Index(sorted(bd.trade_date.unique()))
    pos = {d: i for i, d in enumerate(cal)}
    bd["pos"] = bd.trade_date.map(pos)
    ADV_all = adv60.reindex(index=cal, columns=cols)
    for tag, need_days, cum_thr in (("any>=0.5%", 4, 0.005), ("top>=2.0%", 4, 0.020)):
        ok_frames = []
        for b, g in bd.groupby("broker_code"):
            f = g.pivot_table(index="pos", columns="ticker", values="net", aggfunc="last")
            if f.empty:
                continue
            f = f.reindex(range(len(cal))).fillna(0.0)
            flag = pd.DataFrame((f > 0).astype(float).rolling(6, min_periods=4).sum().values,
                                index=cal, columns=f.columns)
            cum = pd.DataFrame(f.rolling(6, min_periods=4).sum().values, index=cal, columns=f.columns)
            ADV_b = pd.DataFrame(ADV_all.reindex(index=cal, columns=f.columns).values,
                                 index=cal, columns=f.columns)
            ok_b = (flag >= need_days) & (cum >= cum_thr * ADV_b) & (cum > 0)
            ok_frames.append(pd.DataFrame(ok_b.values, index=cal, columns=f.columns)
                             .assign(_broker=b).set_index("_broker", append=True))
        ok = pd.concat(ok_frames).swaplevel().sort_index(level=0)
        any_broker = ok.stack().groupby(level=[1, 2]).max().unstack()
        sig = any_broker.reindex(index=idx, columns=cols).fillna(0.0).astype(float)
        sl.eval_signal(f"C2-broker-persist6d_{tag}", sig, bmask, p, LEDGER,
                       {"family": "C", "def": f"exists broker: buy-side >=4 of last 6 sessions & 6d cum net >= {cum_thr:.1%} ADV60",
                        "grain": "ticker-day (IDX100)"}, min_obs=500, min_tickers=25)
    # ---- C3: concentration persistence
    hot = ((t3z >= 1.0) & (lean_z >= 0.0)).astype(float)
    run3 = hot.rolling(3, min_periods=3).sum()
    sig = t3z.where(run3 >= 3, 0.0)
    sl.eval_signal("C3-conc-persist-3d", sig, bmask, p, LEDGER,
                   {"family": "C", "def": "top3-z>=1 & lean_z>=0 for 3 consecutive sessions",
                    "grain": "ticker-day (IDX100)"}, min_obs=500, min_tickers=25)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache", "ledger_broker.json")
    sl.save_ledger(LEDGER, out)
    print(f"ledger entries: {len(LEDGER)} -> {out}")
    for e in LEDGER:
        h5 = e.get("h5")
        print(f"{e['id']:36s} {e['status']:18s} n={e.get('n_obs',0):7d} "
              + (f"h5 gross={h5['gross_mean']:.4f} net={h5['net_floor']:+.4f} sub={h5['by_subperiod']}" if h5 else ""))


if __name__ == "__main__":
    main()
