#!/usr/bin/env python3
"""Adversarial pass — UP3 destruction attempts (sections A-J) + pseudo-OOS.

Discovery only. Every result below is exploratory. Kill rules are declared in
ADVERSARIAL_REPORT comments and applied mechanically to the printed surfaces.
No selection of the best cell anywhere: surfaces are reported whole.
"""
import sys, os, json, sqlite3
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import sprint_lib as sl

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = {}

HORIZONS_EXT = (1, 2, 3, 5, 7, 10, 15, 20)


def load_ext_holds(p):
    r1 = p.ret + 1.0
    cum = r1.cumprod()
    holds = {}
    for k in HORIZONS_EXT:
        holds[k] = cum.shift(-1 - k) / cum.shift(-1) - 1.0
    # entry variants: open / typical price of t+1, exit close(t+1+k)
    opens = sl.to_panel(p.adj[p.adj.date >= "2024-06-01"], "open")
    typ = (opens + sl.to_panel(p.adj[p.adj.date >= "2024-06-01"], "high")
           + sl.to_panel(p.adj[p.adj.date >= "2024-06-01"], "low") + p.close) / 4.0
    oq = (opens.shift(-1) / p.close.shift(-1)).where((opens.shift(-1) > 0) & (p.close.shift(-1) > 0))
    oq = oq.clip(0.3, 3.0)                      # open(t+1)/close(t+1): next-day entry ratio
    tq = ((typ / p.close).shift(-1)).where(typ.shift(-1) > 0).clip(0.3, 3.0)
    entry_open = holds.copy()
    entry_typ = holds.copy()
    for k in HORIZONS_EXT:
        entry_open[k] = cum.shift(-1 - k) / oq / cum.shift(-1) - 1.0
        entry_typ[k] = cum.shift(-1 - k) / tq / cum.shift(-1) - 1.0
    return holds, entry_open, entry_typ


def stats(v, name=""):
    v = v[~np.isnan(v)]
    if len(v) == 0:
        return None
    out = {"n": int(len(v)), "mean": float(np.mean(v)), "med": float(np.median(v)),
           "hit": float((v > 0).mean())}
    for t in (5, 10, 20):
        lo, hi = np.percentile(v, [t, 100 - t])
        out[f"trim{t}"] = float(np.mean(v[(v >= lo) & (v <= hi)]))
    for w in (90, 95, 99):
        lo, hi = np.percentile(v, [(100 - w) / 2, (100 + w) / 2])
        out[f"wins{w}"] = float(np.mean(np.clip(v, lo, hi)))
    srt = np.sort(v)
    tot = srt.sum()
    for q in (1, 2, 5, 10):
        m = max(1, int(len(srt) * q / 100))
        out[f"top{q}_share"] = float(srt[-m:].sum() / tot) if tot > 0 else np.nan
    out["max_obs"] = float(srt[-1])
    out["min_obs"] = float(srt[0])
    return out


def sub_periods(r):
    out = {}
    for lab, (lo, hi) in {"25H1": ("2025-01-01", "2025-07-01"), "25H2": ("2025-07-01", "2026-01-01"),
                          "26H1": ("2026-01-01", "2026-07-01"), "26H2": ("2026-07-01", "2026-12-31")}.items():
        sub = r[(r.index >= lo) & (r.index < hi)]
        v = sub.values[sub.notna().values]
        out[lab] = round(float(np.mean(v)), 5) if len(v) > 30 else None
    return out


def monthly(r):
    idx = pd.PeriodIndex(r.index, freq="M").astype(str)
    df = pd.DataFrame({"m": idx, "v": r.values})
    return df.dropna().groupby("m")["v"].agg(["mean", "count"]).round(5)


def main():
    p = sl.SprintPanel()
    mask = p.mask_base()
    r1 = p.ret1
    holds, entry_open, entry_typ = load_ext_holds(p)

    # market state: equal-weight canvas index, trailing 60d return terciles
    mkt = p.ret[p.mask_base()].mean(axis=1)
    mkt60 = (mkt + 1).rolling(60, min_periods=40).apply(np.prod, raw=True) - 1
    state = pd.qcut(mkt60.rank(method="first"), 3, labels=["bear", "side", "bull"]).astype(object)
    state = pd.Series(state, index=mkt60.index)

    up3 = (r1 >= 0.03) & mask
    OUT["base_n"] = int(up3.values.sum())

    # ---------- A. TAIL DECOMPOSITION ----------
    print("=" * 70); print("A. TAIL DECOMPOSITION (UP3, entry close)"); print("=" * 70)
    OUT["tail"] = {}
    for k in (5, 10):
        v = holds[k][up3]
        arr = v.values[v.notna().values]
        s = stats(arr)
        OUT["tail"][k] = s
        print(f"h{k}: mean={s['mean']:+.4f} med={s['med']:+.4f} hit={s['hit']:.3f} n={s['n']}")
        print(f"     trimmed 5/10/20%: {s['trim5']:+.4f} {s['trim10']:+.4f} {s['trim20']:+.4f}")
        print(f"     winsor 90/95/99%: {s['wins90']:+.4f} {s['wins95']:+.4f} {s['wins99']:+.4f}")
        print(f"     top1/2/5/10% share of total: {s['top1_share']:.2f} {s['top2_share']:.2f} {s['top5_share']:.2f} {s['top10_share']:.2f}")
        print(f"     max obs {s['max_obs']:+.3f}  min obs {s['min_obs']:+.3f}")
    # daily-basket view (the tradeable object): equal weight per day
    bask5 = holds[5][up3].mean(axis=1).dropna()
    print(f"daily basket h5: mean={bask5.mean():+.4f} med={bask5.median():+.4f} "
          f"worst day {bask5.min():+.4f} best {bask5.max():+.4f} days={len(bask5)}")
    OUT["tail"]["basket_h5"] = {"mean": float(bask5.mean()), "med": float(bask5.median()),
                                "min": float(bask5.min()), "max": float(bask5.max()),
                                "pct5": float(bask5.quantile(0.05))}

    # ---------- B. TIME STABILITY ----------
    print(); print("=" * 70); print("B. TIME STABILITY (h5 daily-basket)"); print("=" * 70)
    mm = monthly(bask5)
    OUT["monthly"] = mm.reset_index().to_dict("records")
    print(mm.to_string())
    print(f"positive months: {(mm['mean'] > 0).sum()}/{len(mm)}")
    for w in (3, 6):
        roll = bask5.rolling(w, min_periods=max(2, w // 2)).mean()
        OUT[f"roll{w}m"] = {"min": float(roll.min()), "frac_pos": float((roll > 0).mean())}
        print(f"rolling {w}m mean: min={roll.min():+.4f} frac positive={(roll > 0).mean():.2f}")
    # market-state conditional
    print("\nby market state (trailing 60d canvas return tercile at event):")
    OUT["by_state"] = {}
    st_al = state.reindex(up3.index)
    for st in ("bear", "side", "bull"):
        sel = up3.mul((st_al == st).fillna(False).astype(bool), axis=0)   # row-aligned
        v = holds[5][sel].values; v = v[~np.isnan(v)]
        OUT["by_state"][st] = {"n": len(v), "h5": float(np.mean(v)) if len(v) else None}
        print(f"  {st:5s}: n={len(v):6d} h5={np.mean(v):+.4f}" if len(v) else f"  {st}: n=0")

    # extreme-observation identification (top 5 h5 events)
    print("\ntop-5 individual h5 events (artifact check):")
    stk = holds[5][up3].stack().sort_values(ascending=False)
    for (d, t), v in stk.head(5).items():
        print(f"  {t} {d}: h5={v:+.3f}")
    OUT["extremes"] = [(t, d, float(v)) for (d, t), v in stk.head(5).items()]

    # ---------- C. THRESHOLD SURFACE ----------
    print(); print("=" * 70); print("C. THRESHOLD SURFACE (predeclared grid)"); print("=" * 70)
    OUT["thresholds"] = []
    for thr in (0.01, 0.02, 0.03, 0.04, 0.05, 0.07, 0.10):
        ev = (r1 >= thr) & mask
        row = {"thr": thr, "n": int(ev.values.sum())}
        for k in (5, 10):
            v = holds[k][ev].values; v = v[~np.isnan(v)]
            row[f"h{k}"] = float(np.mean(v)) if len(v) else None
            row[f"net{k}"] = row[f"h{k}"] - sl.COST_RT_FLOOR if len(v) else None
        sp = sub_periods(holds[5][ev])
        vals = [x for x in sp.values() if x is not None]
        row["h5_subs"] = sp
        row["pos_halves"] = sum(1 for x in vals if x > 0)
        row["neg_halves"] = sum(1 for x in vals if x <= 0)
        OUT["thresholds"].append(row)
        print(f"  >={thr:.0%}: n={row['n']:6d} h5={row['h5']:+.4f} net={row['net5']:+.4f} "
              f"h10={row['h10']:+.4f} net10={row['net10']:+.4f} pos_halves={row['pos_halves']}/4 "
              f"subs={[round(x,4) if x is not None else None for x in sp.values()]}")

    # ---------- D. HORIZON SURFACE ----------
    print(); print("=" * 70); print("D. HORIZON SURFACE (>=+3%)"); print("=" * 70)
    OUT["horizons"] = []
    for k in HORIZONS_EXT:
        v = holds[k][up3].values; v = v[~np.isnan(v)]
        # amortized cost per horizon: one RT per k-day trade
        row = {"k": k, "n": len(v), "gross": float(np.mean(v)), "net60": float(np.mean(v) - sl.COST_RT_FLOOR)}
        OUT["horizons"].append(row)
        print(f"  k={k:2d}: n={len(v):6d} gross={row['gross']:+.4f} net60={row['net60']:+.4f}")

    # ---------- E. ENTRY MECHANICS ----------
    print(); print("=" * 70); print("E. ENTRY MECHANICS (h5, exit close t+1+k)"); print("=" * 70)
    OUT["entry"] = {}
    for label, panels, slip in (("close(t+1)", holds, 0.0), ("open(t+1)", entry_open, 0.0025),
                                ("typ4(t+1)", entry_typ, 0.0025)):
        v = panels[5][up3].values - slip
        v = v[~np.isnan(v)]
        OUT["entry"][label] = {"mean": float(np.mean(v)), "net60": float(np.mean(v) - sl.COST_RT_FLOOR)}
        print(f"  {label:11s} (slip {slip:.2%}): h5={np.mean(v):+.4f} net60={np.mean(v)-sl.COST_RT_FLOOR:+.4f}")

    # ---------- F. LIQUIDITY / CAPACITY ----------
    print(); print("=" * 70); print("F. LIQUIDITY & CAPACITY (ADV60 at event)"); print("=" * 70)
    adv = p.adv60.where(mask)
    OUT["capacity"] = []
    buckets = [(0, 0.5e9, "<0.5bn"), (0.5e9, 1e9, "0.5-1bn"), (1e9, 5e9, "1-5bn"), (5e9, 1e18, ">5bn")]
    for lo, hi, lab in buckets:
        sel = up3 & (adv >= lo) & (adv < hi)
        v = holds[5][sel].values; v = v[~np.isnan(v)]
        names = sel.sum(axis=1)
        OUT["capacity"].append({"bucket": lab, "n": len(v),
                                "h5": float(np.mean(v)) if len(v) else None,
                                "avg_names_day": float(names.mean())})
        print(f"  ADV {lab:8s}: n={len(v):6d} h5={np.mean(v):+.4f} avg names/day={names.mean():.1f}"
              if len(v) else f"  ADV {lab}: n=0")
    # executable capacity at Rp50M / Rp100M, 10% participation
    for cap, need in (("Rp50M", 0.5e9), ("Rp100M", 1.0e9)):
        sel = up3 & (adv >= need)
        v = holds[5][sel].values; v = v[~np.isnan(v)]
        names = sel.sum(axis=1)
        OUT[f"cap_{cap}"] = {"n": len(v), "h5": float(np.mean(v)),
                             "avg_names_day": float(names.mean()),
                             "days_zero": int((sel.sum(axis=1) == 0).sum())}
        print(f"  executable @{cap} (ADV>={need/1e9:.1f}bn @10% part): n={len(v)} h5={np.mean(v):+.4f} "
              f"names/day={names.mean():.1f} days_with_zero={int((sel.sum(axis=1)==0).sum())}")

    # ---------- G. SUSPENSIONS ----------
    print(); print("=" * 70); print("G. SUSPENSION CONTAMINATION"); print("=" * 70)
    susp = sl.load_suspensions()
    dates_idx = {d: i for i, d in enumerate(p.close.index)}
    K_MAX = 20
    contam = pd.DataFrame(False, index=up3.index, columns=up3.columns)
    n_susp_windows = len(susp)
    for _, row in susp.iterrows():
        t, tk = row["ticker"], row["ticker"]
        if tk not in contam.columns:
            continue
        ln, rs = row["last_normal_date"], row["resume_date"]
        # window (last_normal_date, resume_date + K_MAX sessions] contaminates events before it
        i_ln = dates_idx.get(ln)
        if i_ln is None:
            continue
        lo_i = max(0, i_ln - K_MAX)
        hi_i = min(len(contam.index) - 1, dates_idx.get(rs, i_ln) + K_MAX)
        contam.iloc[lo_i:hi_i + 1, contam.columns.get_loc(tk)] = True
    clean = up3 & ~contam
    v_all = holds[5][up3].values; v_all = v_all[~np.isnan(v_all)]
    v_cln = holds[5][clean].values; v_cln = v_cln[~np.isnan(v_cln)]
    OUT["suspension"] = {"n_events": len(v_all), "n_clean": len(v_cln),
                         "n_excluded": len(v_all) - len(v_cln),
                         "h5_all": float(np.mean(v_all)), "h5_clean": float(np.mean(v_cln)),
                         "susp_windows": n_susp_windows}
    print(f"  suspension windows in store: {n_susp_windows}")
    print(f"  UP3 events: {len(v_all)}  clean: {len(v_cln)}  excluded(by overlap): {len(v_all)-len(v_cln)}")
    print(f"  h5 all = {np.mean(v_all):+.4f}   h5 clean = {np.mean(v_cln):+.4f}")
    print(f"  (excluded events averaged h5 = "
          f"{(np.sum(v_all)*len(v_all) - 0) / max(1,len(v_all)):+.4f} baseline; implied excluded mean = "
          f"{(float(np.sum(v_all)) - float(np.sum(v_cln))) / max(1, len(v_all)-len(v_cln)):+.4f})")
    for kk in (10, 20):
        va = holds[kk][up3].values; va = va[~np.isnan(va)]
        vc = holds[kk][clean].values; vc = vc[~np.isnan(vc)]
        OUT[f"suspension_h{kk}"] = {"all": float(np.mean(va)), "clean": float(np.mean(vc))}
        print(f"  h{kk}: all={np.mean(va):+.4f}  clean={np.mean(vc):+.4f}")

    # ---------- H. CORPORATE ACTIONS ----------
    print(); print("=" * 70); print("H. CORPORATE-ACTION CONTAMINATION"); print("=" * 70)
    ca = sl.load_corporate_actions()
    # split basis detection result per (ticker, ex_date): reused from build_adjusted logic
    splits = ca[ca.action == "split"]
    divs = ca[ca.action == "dividend"]
    ev_days = up3[up3].index.get_level_values(0) if False else None
    # event list: (ticker, date)
    ev = up3.stack()
    ev = ev[ev].reset_index()[["ticker", "date"]]
    ev["k_end_pos"] = ev["date"].map(dates_idx)
    spl_by_ticker = {t: g["date"].tolist() for t, g in splits.groupby("ticker")}
    div_by_ticker = {t: set(g["date"]) for t, g in divs.groupby("ticker")}
    cls = []
    for _, r in ev.iterrows():
        t, d = r["ticker"], r["date"]
        i0 = r["k_end_pos"]
        win = set(p.close.index[i0 + 1: i0 + 1 + 20]) if i0 is not None else set()
        s_win = [x for x in spl_by_ticker.get(t, []) if x in win]
        d_win = len(div_by_ticker.get(t, set()) & win)
        if s_win:
            cls.append("split_in_window")
        elif d_win:
            cls.append("div_only")
        else:
            cls.append("clean")
    ev["ca_class"] = cls
    OUT["ca"] = ev["ca_class"].value_counts().to_dict()
    print(ev["ca_class"].value_counts().to_string())
    key = ev.set_index(["ticker", "date"])["ca_class"]
    def sel_from_key(mask_series):
        s = mask_series.unstack(level=0)   # rows=date, cols=ticker
        return s.reindex(index=up3.index, columns=up3.columns).fillna(False).astype(bool) & up3
    for cc in ("clean", "div_only", "split_in_window"):
        sel = sel_from_key(key == cc)
        v = holds[5][sel].values; v = v[~np.isnan(v)]
        print(f"  {cc:16s}: n={len(v):6d} h5={np.mean(v):+.4f}" if len(v) else f"  {cc}: n=0")
        OUT["ca_" + cc] = {"n": len(v), "h5": float(np.mean(v)) if len(v) else None}
    # clean := no split in window (dividends are held-side cash, adjusted correctly)
    sel_clean = sel_from_key(key != "split_in_window")
    v = holds[5][sel_clean].values; v = v[~np.isnan(v)]
    OUT["ca_ex_split"] = {"n": len(v), "h5": float(np.mean(v))}
    print(f"  ex-split-window subset : n={len(v):6d} h5={np.mean(v):+.4f}")

    # ---------- FM with market control ----------
    print(); print("=" * 70); print("FM: UP3 flag controlling ret1/ret5z/volz/market_ret1 (h5)"); print("=" * 70)
    ret5z = sl.trailing_z(p.ret5)
    volz = sl.trailing_z(p.volume)
    mkt_al = p.ret.mul(0).add(mkt, axis=0)   # broadcast market return across columns
    fm = sl.fm_regression(p, up3.astype(float), mask,
                          controls=[r1, ret5z, volz, mkt_al], k=5)
    OUT["fm_up3_mkt"] = fm
    print(f"  beta={fm['fm_mean']:+.5f} t={fm['fm_t']:+.2f} n_dates={fm['n_dates']}")

    # ---------- I. LOTTERY / SMALL-CAP ----------
    print(); print("=" * 70); print("I. LOTTERY / SMALL-CAP DECOMPOSITION (h5)"); print("=" * 70)
    adv_ter = adv.rank(axis=1, pct=True)
    px_ter = p.close.where(mask).rank(axis=1, pct=True)
    vol_ter = (p.volume.where(mask)).rank(axis=1, pct=True)
    OUT["lottery"] = []
    for lab, sel in (("ADV top-3rd", adv_ter >= 0.667), ("ADV mid-3rd", (adv_ter >= 0.333) & (adv_ter < 0.667)),
                     ("ADV bot-3rd", adv_ter < 0.333), ("PX top-3rd", px_ter >= 0.667), ("PX bot-3rd", px_ter < 0.333),
                     ("VOL top-3rd", vol_ter >= 0.667), ("VOL bot-3rd", vol_ter < 0.333),
                     ("mega: ADV&PX top-3rd", (adv_ter >= 0.667) & (px_ter >= 0.667))):
        s = up3 & sel.fillna(False)
        v = holds[5][s].values; v = v[~np.isnan(v)]
        OUT["lottery"].append({"bucket": lab, "n": len(v), "h5": float(np.mean(v)) if len(v) else None})
        print(f"  {lab:22s}: n={len(v):6d} h5={np.mean(v):+.4f}" if len(v) else f"  {lab}: n=0")

    # ---------- J. OVERLAP WITH PRODUCTION FASTMOVER ----------
    print(); print("=" * 70); print("J. OVERLAP WITH PRODUCTION fastmover_patterns"); print("=" * 70)
    c = sl.ro_conn(sl.WF)
    try:
        fmv = pd.read_sql_query(
            "SELECT ticker, move_date, move_pct, pattern_type FROM fastmover_patterns", c)
    finally:
        c.close()
    fmv_any = set(zip(fmv.ticker, fmv.move_date))
    fmv_cont = set(zip(fmv[fmv.pattern_type == "CONTINUATION"].ticker,
                       fmv[fmv.pattern_type == "CONTINUATION"].move_date))
    fmv_window = (fmv.move_date >= "2025-01-01") & (fmv.move_date <= "2026-05-06")
    ev_pairs = list(zip(ev.ticker, ev.date))
    ov_any = np.array([(t, d) in fmv_any for t, d in ev_pairs])
    ov_cont = np.array([(t, d) in fmv_cont for t, d in ev_pairs])
    # restrict comparison to the fastmover coverage window
    in_win = np.array([("2025-01-01" <= d <= "2026-05-06") for _, d in ev_pairs])
    OUT["overlap"] = {
        "fastmover_rows": int(len(fmv)), "fmv_window": "2024-05-08..2026-05-06",
        "up3_events_in_window": int(in_win.sum()),
        "overlap_any_%": round(float(ov_any[in_win].mean()), 3),
        "overlap_continuation_%": round(float(ov_cont[in_win].mean()), 3),
    }
    h5s = holds[5][up3]
    ev["ov"] = np.where(ov_any, "fastmover", "up3_only")
    key2 = ev.set_index(["ticker", "date"])["ov"]
    for lab in ("fastmover", "up3_only"):
        sel = (key2 == lab).unstack().reindex(index=up3.index, columns=up3.columns).fillna(False).astype(bool)
        sel &= up3
        v = holds[5][sel].values; v = v[~np.isnan(v)]
        OUT[f"overlap_h5_{lab}"] = {"n": len(v), "h5": float(np.mean(v)) if len(v) else None}
        print(f"  {lab:12s}: n={len(v):6d} h5={np.mean(v):+.4f}" if len(v) else f"  {lab}: n=0")

    # ---------- SURVIVORSHIP BOUND ----------
    print(); print("=" * 70); print("SURVIVORSHIP BOUND (canvas has ZERO dropouts)"); print("=" * 70)
    v = holds[5][up3].values; v = v[~np.isnan(v)]
    base_mean = v.mean()
    for hazard in (0.005, 0.01, 0.02, 0.05):
        # assume missing delisting tail: rate*hazard of events end at avg -60% over 5d
        adj = base_mean * (1 - hazard) + hazard * (-0.60)
        OUT[f"surv_bound_h{hazard}"] = adj
        print(f"  if {hazard:.1%} of events actually ended in -60% delisting tail: adj h5 = {adj:+.4f} "
              f"(net60 {adj - sl.COST_RT_FLOOR:+.4f})")

    # ---------- PSEUDO-OOS: 2021-07 .. 2024-12 (price-only, untouched by program) ----------
    print(); print("=" * 70); print("PSEUDO-OOS 2021-07..2024-12 (never used in any discovery)"); print("=" * 70)
    c = sl.ro_conn(sl.WF)
    try:
        ohl = pd.read_sql_query(
            "SELECT ticker, date, open, high, low, close, volume FROM ohlcv "
            "WHERE is_final=1 AND close>0 ORDER BY ticker, date", c)
    finally:
        c.close()
    ca = sl.load_corporate_actions()
    ohl["traded_value"] = ohl["close"] * ohl["volume"]
    adj = sl.build_adjusted(ohl, ca)
    full_ret = sl.to_panel(adj, "ret")
    full_tv = sl.to_panel(adj, "traded_value")
    full_liq = sl.trailing_median_panel(full_tv) >= sl.LIQ_FLOOR
    full_r1 = full_ret + 1.0
    full_cum = full_r1.cumprod()
    full_h5 = full_cum.shift(-6) / full_cum.shift(-1) - 1.0
    full_h10 = full_cum.shift(-11) / full_cum.shift(-1) - 1.0
    tradable = full_liq & (sl.to_panel(adj, "volume").shift(-1) > 0)
    oos = {}
    for era, lo, hi in (("2021H2-2022", "2021-07-01", "2023-01-01"),
                        ("2023-2024", "2023-01-01", "2025-01-01")):
        for thr in (0.02, 0.03, 0.05):
            ev = (full_ret >= thr) & tradable
            ev = ev[(ev.index >= lo) & (ev.index < hi)]
            v = full_h5[ev].values; v = v[~np.isnan(v)]
            v10 = full_h10[ev].values; v10 = v10[~np.isnan(v10)]
            oos[f"{era}_thr{thr}"] = {"n": len(v), "h5": float(np.mean(v)) if len(v) else None,
                                      "h10": float(np.mean(v10)) if len(v10) else None}
            print(f"  {era} >={thr:.0%}: n={len(v):6d} h5={np.mean(v):+.4f} h10={np.mean(v10):+.4f}"
                  if len(v) else f"  {era} >={thr:.0%}: n=0")
    OUT["pseudo_oos"] = oos

    with open(os.path.join(HERE, "cache", "adv_up3.json"), "w") as f:
        json.dump(OUT, f, indent=1, default=str)
    print("\nsaved -> cache/adv_up3.json")


if __name__ == "__main__":
    main()
