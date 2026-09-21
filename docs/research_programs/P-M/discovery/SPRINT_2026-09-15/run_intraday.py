#!/usr/bin/env python3
"""Discovery sprint — intraday-structure candidates (family D) from the
frozen v002 minute-bar store.

Declared exclusions enforced: fixture 2025-04-14; integrity-contradiction
zone 2025-08-04..2025-09-17; window ends 2026-04-27. Sessions additionally
require minute coverage into the last trading hour (>= 12 buckets of 30 min).
Signals are formed from same-session data (known by close of day t); entry at
close(t+1) as everywhere else in the sprint."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import sprint_lib as sl

LEDGER = []


def load_buckets():
    c = sl.ro_conn(sl.V002)
    try:
        bdf = pd.read_sql_query(
            "SELECT ticker, trade_date, (CAST(substr(bar_time,1,2) AS INTEGER)*60"
            "+CAST(substr(bar_time,4,2) AS INTEGER)-540)/30 AS b, SUM(buy_lot) bl,"
            "SUM(sell_lot) sl, SUM(net_value) nv, SUM(buy_lot+sell_lot) vol,"
            "SUM(price*(buy_lot+sell_lot)) pv FROM stockbit_flow_bars"
            " WHERE trade_date<='2026-04-27' GROUP BY 1,2,3", c)
    finally:
        c.close()
    return bdf


def main():
    p = sl.SprintPanel()
    mask = p.mask_base()
    bdf = load_buckets()
    print("bucket rows:", len(bdf))
    # declared exclusions
    bdf = bdf[~bdf.trade_date.isin(sl.V002_FIXTURE_DATES)]
    zone = (bdf.trade_date >= sl.V002_INTEGRITY_ZONE[0]) & (bdf.trade_date <= sl.V002_INTEGRITY_ZONE[1])
    bdf = bdf[~zone]
    bdf = bdf[bdf.vol > 0]
    bdf = bdf.sort_values(["ticker", "trade_date", "b"])

    g = bdf.groupby(["ticker", "trade_date"])
    nmin = g["b"].transform("max")
    bdf = bdf[(nmin >= 12) & (g["b"].transform("min") <= 1)]   # full-session requirement
    print("after session-completeness filter:", len(bdf), "sessions:",
          bdf[["ticker", "trade_date"]].drop_duplicates().shape[0])

    g = bdf.groupby(["ticker", "trade_date"])
    feats = g.agg(day_nv=("nv", "sum"), day_vol=("vol", "sum"), day_pv=("pv", "sum"),
                  nb_ = ("b", "size")).reset_index()
    # open/close vwap from first/last active buckets
    first = bdf[bdf.b == g["b"].transform("min")]
    last = bdf[bdf.b == g["b"].transform("max")]
    op = (first.set_index(["ticker", "trade_date"]).pv / first.set_index(["ticker", "trade_date"]).vol)
    cl = (last.set_index(["ticker", "trade_date"]).pv / last.set_index(["ticker", "trade_date"]).vol)
    feats = feats.set_index(["ticker", "trade_date"])
    feats["open_px"] = op
    feats["close_px"] = cl
    feats["ret_intra"] = feats.close_px / feats.open_px - 1.0
    # early window (by 10:30) and late window (last two active buckets)
    bmax = bdf.groupby(["ticker", "trade_date"])["b"].transform("max")
    early = bdf[bdf.b <= 2].groupby(["ticker", "trade_date"]).agg(e_nv=("nv", "sum"),
              e_pv=("pv", "sum"), e_vol=("vol", "sum"))
    late = bdf[bdf.b >= bmax - 1].groupby(["ticker", "trade_date"]).agg(l_nv=("nv", "sum"),
              l_pv=("pv", "sum"), l_vol=("vol", "sum"))
    feats = feats.join(early).join(late)
    feats["late_share"] = feats.l_nv / feats.day_nv.abs().replace(0, np.nan)
    feats["e_move"] = (feats.e_pv / feats.e_vol) / feats.open_px - 1.0
    # heavy-tape share: nv in top-quintile-volume buckets
    bdf["vq"] = bdf.groupby(["ticker", "trade_date"])["vol"].rank(pct=True)
    tape = bdf[bdf.vq >= 0.8].groupby(["ticker", "trade_date"])["nv"].sum().rename("tape_nv")
    feats = feats.join(tape)
    feats["tape_share"] = feats.tape_nv / feats.day_nv.abs().replace(0, np.nan)
    feats = feats.reset_index()

    # panels on the minute canvas
    idx, cols = p.close.index, p.close.columns
    def pnl(col):
        f = feats.pivot_table(index="trade_date", columns="ticker", values=col, aggfunc="last")
        return f.reindex(index=idx, columns=cols)
    day_nv, day_vol = pnl("day_nv"), pnl("day_vol")
    late_share, e_nv, e_move = pnl("late_share"), pnl("e_nv"), pnl("e_move")
    tape_share, ret_intra = pnl("tape_share"), pnl("ret_intra")
    day_nv_z = sl.trailing_z(day_nv)
    vol_z = sl.trailing_z(day_vol)
    e_nv_z = sl.trailing_z(e_nv)

    admitted = sl.in_v002_window(pd.Index(idx))
    dmask = mask.copy()
    dmask.loc[~dmask.index.isin(admitted)] = False
    dmask = dmask & day_nv.notna()
    print("intraday mask obs:", int(dmask.values.sum()))

    r1 = p.ret1
    # D1: red day, flow kept buying into the close
    for rt in (-0.02, -0.03):
        sig = day_nv_z.where((r1 <= rt) & (day_nv > 0) & (late_share >= 0) & (day_nv_z >= 1.0), 0.0)
        sl.eval_signal(f"D1-dip-lateflow-confirms_r{rt}", sig, dmask, p, LEDGER,
                       {"family": "D", "def": f"ret1<={rt:.0%} & day bar-net>0 & late-30m net>=0 & day_nv_z>=1",
                        "source": "frozen v002 minute bars", "grain": "ticker-day (full canvas, v002 window)"},
                       min_obs=300, min_tickers=40)
    # D2: late-buy concentration with muted close
    for lt in (0.6, 0.75):
        sig = day_nv_z.where((late_share >= lt) & (day_nv_z >= 1.5) & (ret_intra.abs() <= 0.01), 0.0)
        sl.eval_signal(f"D2-latebuy-muted-close_{lt}", sig, dmask, p, LEDGER,
                       {"family": "D", "def": f"last-30m net share>={lt:.0%} & day_nv_z>=1.5 & |intraday ret|<=1%",
                        "grain": "ticker-day (v002 window)"}, min_obs=300, min_tickers=40)
    # D3: buying at the tape (top-volume buckets carry the net flow)
    for tt in (0.5, 0.7):
        sig = day_nv_z.where((tape_share >= tt) & (vol_z >= 1.5) & (day_nv > 0), 0.0)
        sl.eval_signal(f"D3-heavy-tape-buying_{tt}", sig, dmask, p, LEDGER,
                       {"family": "D", "def": f"net in top-vol-quintile buckets >= {tt:.0%} of |day net| & vol_z>=1.5 & day net>0",
                        "grain": "ticker-day (v002 window)"}, min_obs=300, min_tickers=40)
    # D4: early flow leads, price has not followed by 10:30
    for zt in (1.0, 1.5):
        sig = e_nv_z.where((e_nv_z >= zt) & (e_move <= 0), 0.0)
        sl.eval_signal(f"D4-earlyflow-pricelag_z{zt}", sig, dmask, p, LEDGER,
                       {"family": "D", "def": f"z60(net by 10:30)>={zt} & vwap move to 10:30 <= 0",
                        "grain": "ticker-day (v002 window)"}, min_obs=300, min_tickers=40)
    # D5: intraday reversal with late flow confirm (deep red day, flow held)
    sig = day_nv_z.where((r1 <= -0.03) & (day_nv > 0) & (ret_intra >= r1.fillna(0) * 0.5), 0.0)
    sl.eval_signal("D5-red-reversal-flowconfirm", sig, dmask, p, LEDGER,
                   {"family": "D", "def": "ret1<=-3% & day bar-net>0 & intraday close-loss recovered >= half",
                    "grain": "ticker-day (v002 window)"}, min_obs=300, min_tickers=40)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache", "ledger_intraday.json")
    sl.save_ledger(LEDGER, out)
    print(f"ledger entries: {len(LEDGER)} -> {out}")
    for e in LEDGER:
        h5 = e.get("h5")
        print(f"{e['id']:38s} {e['status']:18s} n={e.get('n_obs',0):7d} "
              + (f"h5 gross={h5['gross_mean']:.4f} net={h5['net_floor']:+.4f} sub={h5['by_subperiod']}" if h5 else ""))


if __name__ == "__main__":
    main()
