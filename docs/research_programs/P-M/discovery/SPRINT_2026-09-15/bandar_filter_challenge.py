#!/usr/bin/env python3
"""BANDAR FILTER — ADVERSARIAL CHALLENGE (9 declared attacks).

Challenge object: "bandar buyer-share >= ~0.55-0.60 on signal day => veto".
DEFINITIONS FIXED IN ADVANCE:
  buyer-share s = total_buyer/(total_buyer+total_seller); buyer-heavy s>=theta;
  control = s<0.45; mid band [0.45,0.55) excluded from spreads.
  Base: liquid mask & suspension-clean & bandar coverage.
NO post-hoc thresholds, NO extra combinations. P-value never a selection device.
"""
import sys, os, json, sqlite3
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import sprint_lib as sl
from adversarial_flow import build_contam

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = {}
HK = (1, 2, 3, 5, 10, 20)


def main():
    p = sl.SprintPanel()
    mask0 = p.mask_base()
    r1 = p.ret1
    _cum = (p.ret + 1.0).cumprod()
    holds = {k: p.hold[k] if k in p.hold else _cum.shift(-1 - k) / _cum.shift(-1) - 1.0 for k in HK}
    clean = ~build_contam(p)
    mask = mask0 & clean

    c = sl.ro_conn(sl.WF)
    try:
        bd = pd.read_sql_query("SELECT * FROM bandar_detector", c)
    finally:
        c.close()

    def pnl(col, src=bd):
        return src.pivot_table(index="trade_date", columns="ticker", values=col, aggfunc="last") \
                  .reindex(index=p.close.index, columns=p.close.columns)

    tb, ts = pnl("total_buyer"), pnl("total_seller")
    share = tb / (tb + ts).replace(0, np.nan)
    have = share.notna()
    idx, cols = p.close.index, p.close.columns
    nbz = sl.trailing_z(p.nb)
    volz = sl.trailing_z(p.volume)
    ret5z = sl.trailing_z(p.ret5)
    nb5 = p.nb.rolling(5, min_periods=3).sum()
    accel_z = sl.trailing_z(nb5 - nb5.shift(5))
    adv = p.adv60.where(mask0)
    adv_ter = adv.rank(axis=1, pct=True)
    px_ter = p.close.where(mask0).rank(axis=1, pct=True)

    # ============ 1. THRESHOLD SURFACE ============
    print("=" * 74)
    print("1. THRESHOLD SURFACE (buyer-share veto candidate, covered & suspension-clean)")
    print("=" * 74)
    res = []
    for th in (0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75):
        sel = mask & have & (share >= th)
        ctl = mask & have & (share < 0.45)
        row = {"theta": th}
        for k in HK:
            v = holds[k][sel].values; v = v[~np.isnan(v)]
            row[f"h{k}"] = float(np.mean(v)) if len(v) > 50 else None
        v5 = holds[5][sel]
        vv = v5.values[~np.isnan(v5.values)]
        if len(vv) > 50:
            lo, hi = np.percentile(vv, [5, 95])
            srt = np.sort(vv); tot = srt.sum()
            m = max(1, int(len(srt) * 0.01))
            row.update({"n": len(vv), "med": float(np.median(vv)), "trim5": float(np.mean(vv[(vv >= lo) & (vv <= hi)])),
                        "hit": float((vv > 0).mean()), "bot1_share": float(srt[:m].sum() / tot) if tot < 0 else None,
                        "top1_share": float(srt[-m:].sum() / tot) if tot > 0 else None})
        sp = {}
        for lab, (lo_, hi_) in {"25H1": ("2025-01-01", "2025-07-01"), "25H2": ("2025-07-01", "2026-01-01"),
                                "26H1": ("2026-01-01", "2026-07-01"), "26H2": ("2026-07-01", "2026-12-31")}.items():
            xb = holds[5][sel]; xg = holds[5][ctl]
            xb = xb[(xb.index >= lo_) & (xb.index < hi_)].values; xb = xb[~np.isnan(xb)]
            xg = xg[(xg.index >= lo_) & (xg.index < hi_)].values; xg = xg[~np.isnan(xg)]
            sp[lab] = (round(float(np.mean(xb) - np.mean(xg)), 5) if len(xb) > 30 and len(xg) > 30 else None)
        row["spread_vs_light_halves"] = sp
        row["neg_halves"] = sum(1 for x in sp.values() if x is not None and x < 0)
        res.append(row)
        def fmt(x, f="+.4f"):
            return "None" if x is None else x.__format__(f)
        print(f"θ≥{th:.2f}: n={row.get('n',0):6d} h5={fmt(row['h5'])} med={fmt(row.get('med'))} "
              f"trim5={fmt(row.get('trim5'))} hit={fmt(row.get('hit'),'.3f')} "
              f"top1%share={fmt(row.get('top1_share'),'.2f')}")
        print(f"        h1={fmt(row['h1'])} h2={fmt(row['h2'])} h3={fmt(row['h3'])} h10={fmt(row['h10'])} h20={fmt(row['h20'])}"
              f" | spread halves {[None if x is None else round(x,4) for x in sp.values()]} neg={row['neg_halves']}/4")
    OUT["thresholds"] = res

    # ============ 2. COVERAGE-SELECTION ============
    print()
    print("=" * 74)
    print("2. COVERAGE-SELECTION ATTACK")
    print("=" * 74)
    cov = mask & have
    unc = mask & ~have
    for nm, sel in (("A uncovered", unc), ("B covered share<0.45", cov & (share < 0.45)),
                    ("B' covered 0.45-0.55", cov & (share >= 0.45) & (share < 0.55)),
                    ("C covered share>=0.55", cov & (share >= 0.55))):
        v = holds[5][sel].values; v = v[~np.isnan(v)]
        v10 = holds[10][sel].values; v10 = v10[~np.isnan(v10)]
        print(f"  {nm:24s}: n={len(v):6d} h5={np.mean(v):+.4f} h10={np.mean(v10):+.4f}")
        OUT.setdefault("coverage", {})[nm] = {"n": len(v), "h5": float(np.mean(v)), "h10": float(np.mean(v10))}
    # FM on FULL base: share flag orthogonal to coverage flag
    full = mask
    share_hi_cov = (have & (share >= 0.55)).fillna(False).astype(float)
    cov_flag = have.fillna(False).astype(float)
    r_cov = sl.fm_regression(p, cov_flag, full, controls=[r1, ret5z, volz, nbz], k=5)
    r_sh = sl.fm_regression(p, share_hi_cov, full, controls=[cov_flag, r1, ret5z, volz, nbz], k=5)
    print(f"  FM covered-flag (full base): beta={r_cov['fm_mean']:+.5f} t={r_cov['fm_t']:+.2f}")
    print(f"  FM share>=0.55 | coverage flag + controls: beta={r_sh['fm_mean']:+.5f} t={r_sh['fm_t']:+.2f}")
    OUT["coverage_fm"] = {"covered_flag": r_cov, "share_flag": r_sh}

    # ============ 3. PRICE-CONDITION ============
    print()
    print("=" * 74)
    print("3. PRICE-CONDITION ATTACK (buyer-heavy vs buyer-light within move bands)")
    print("=" * 74)
    pc = {}
    base = mask & have
    for band, sel_band in (("all", pd.DataFrame(True, index=base.index, columns=base.columns)),
                           ("ret1>=+1%", (r1 >= 0.01)), ("ret1>=+2%", (r1 >= 0.02)),
                           ("ret1>=+3%", (r1 >= 0.03)), ("ret1>=+5%", (r1 >= 0.05))):
        hb = base & sel_band.fillna(False)
        heavy = hb & (share >= 0.55)
        light = hb & (share < 0.45)
        def m5(sel):
            v = holds[5][sel].values; v = v[~np.isnan(v)]
            v10 = holds[10][sel].values; v10 = v10[~np.isnan(v10)]
            return (float(np.mean(v)) if len(v) > 30 else None, len(v),
                    float(np.mean(v10)) if len(v10) > 30 else None)
        h5h, nh, h10h = m5(heavy); h5l, nl, h10l = m5(light)
        row = {"band": band, "heavy_h5": h5h, "heavy_n": nh, "heavy_h10": h10h,
               "light_h5": h5l, "light_n": nl, "light_h10": h10l,
               "spread_h5": (h5h - h5l) if (h5h is not None and h5l is not None) else None,
               "spread_h10": (h10h - h10l) if (h10h is not None and h10l is not None) else None}
        pc[band] = row
        print(f"  {band:10s}: heavy n={nh:6d} h5={h5h if h5h is None else round(h5h,4)} h10={h10h if h10h is None else round(h10h,4)}"
              f" | light n={nl:6d} h5={h5l if h5l is None else round(h5l,4)} h10={h10l if h10l is None else round(h10l,4)}"
              f" | spread h5={row['spread_h5'] if row['spread_h5'] is None else round(row['spread_h5'],4)}"
              f" h10={row['spread_h10'] if row['spread_h10'] is None else round(row['spread_h10'],4)}")
    OUT["price_condition"] = pc

    # ============ 4. FLOW-CONTROL (FM ladder) ============
    print()
    print("=" * 74)
    print("4. FLOW-CONTROL LADDER (FM share>=0.55 | successive controls)")
    print("=" * 74)
    flag = (share >= 0.55).astype(float)
    lad = {}
    ladders = {
        "no controls": [],
        "price+volume": [r1, ret5z, volz],
        "+platform flow": [r1, ret5z, volz, nbz],
        "+flow accel": [r1, ret5z, volz, nbz, accel_z],
        "+liquidity": [r1, ret5z, volz, nbz, accel_z, adv_ter],
    }
    for nm, cs in ladders.items():
        rr = sl.fm_regression(p, flag, mask & have, controls=cs, k=5)
        lad[nm] = rr
        print(f"  {nm:16s}: beta={rr['fm_mean']:+.5f} t={rr['fm_t']:+.2f} n_dates={rr['n_dates']}")
    OUT["fm_ladder"] = lad
    # portfolio-level: heavy cells split by platform-flow state
    print("  portfolio: heavy-share cells by platform-flow state")
    for nm, sel in (("heavy & nbz>=0", mask & have & (share >= 0.55) & (nbz >= 0)),
                    ("heavy & nbz<0", mask & have & (share >= 0.55) & (nbz < 0)),
                    ("light & nbz>=0", mask & have & (share < 0.45) & (nbz >= 0)),
                    ("light & nbz<0", mask & have & (share < 0.45) & (nbz < 0))):
        v = holds[5][sel].values; v = v[~np.isnan(v)]
        print(f"    {nm:18s}: n={len(v):6d} h5={np.mean(v):+.4f}" if len(v) > 30 else f"    {nm}: n<30")

    # ============ 5. LABEL / BUYER-SHARE CONSISTENCY ============
    print()
    print("=" * 74)
    print("5. LABEL vs BUYER-SHARE CONSISTENCY")
    print("=" * 74)
    t3 = pnl("top3_accdist")
    acc_class = t3.isin({"Big Acc", "Normal Acc", "Small Acc"})
    dist_class = t3.isin({"Big Dist", "Normal Dist", "Small Dist"})
    for lab_name, lab_sel in (("label=Acc", acc_class), ("label=Dist/Neutral", (dist_class | t3.eq("Neutral")))):
        for sh_name, sh_sel in (("share>=0.55", share >= 0.55), ("share<0.45", share < 0.45)):
            sel = mask & have & lab_sel.fillna(False) & sh_sel.fillna(False)
            v = holds[5][sel].values; v = v[~np.isnan(v)]
            print(f"  {lab_name:20s} & {sh_name:12s}: n={len(v):6d} h5={np.mean(v):+.4f}"
                  if len(v) > 30 else f"  {lab_name} & {sh_name}: n<30")
    # does the label add information beyond share? FM with both
    fm2 = sl.fm_regression(p, acc_class.fillna(False).astype(float), mask & have,
                           controls=[r1, ret5z, volz, nbz, flag], k=5)
    print(f"  FM Acc-label | controls + buyer-share: beta={fm2['fm_mean']:+.5f} t={fm2['fm_t']:+.2f}")
    OUT["label_share"] = {"acc_label_fm": fm2}

    # ============ 6. PIT / updated_at ============
    print()
    print("=" * 74)
    print("6. PIT ATTACK (updated_at)")
    print("=" * 74)
    ua = pd.to_datetime(bd.updated_at, errors="coerce")
    hrs = ua.dt.hour.value_counts().sort_index()
    total = len(ua)
    pre_open = int(((ua.dt.hour < 9)).sum())
    intraday = int(((ua.dt.hour >= 9) & (ua.dt.hour <= 15)).sum())
    evening = int(((ua.dt.hour >= 16) | (ua.dt.hour <= 2)).sum())
    print(f"  rows: {total} | stamped <09:00 WIB: {pre_open} ({pre_open/total:.1%}) | "
          f"09:00-15:59 (intraday): {intraday} ({intraday/total:.1%}) | >=16:00 (post-close): {evening} ({evening/total:.1%})")
    OUT["pit"] = {"pre_open": pre_open, "intraday": intraday, "evening": evening, "total": total}

    # ============ 7. SIZE / LIQUIDITY ============
    print()
    print("=" * 74)
    print("7. SIZE / LIQUIDITY ATTACK (h5 of heavy vs light by tier)")
    print("=" * 74)
    sz = {}
    for tier_name, tier in (("ADV top", adv_ter >= 0.667), ("ADV mid", (adv_ter >= 0.333) & (adv_ter < 0.667)),
                            ("ADV bot", adv_ter < 0.333), ("PX top", px_ter >= 0.667), ("PX bot", px_ter < 0.333)):
        for sh_name, sh in (("heavy", share >= 0.55), ("light", share < 0.45)):
            sel = mask & have & tier.fillna(False) & sh.fillna(False)
            v = holds[5][sel].values; v = v[~np.isnan(v)]
            key = f"{tier_name}/{sh_name}"
            sz[key] = {"n": len(v), "h5": float(np.mean(v)) if len(v) > 30 else None}
            print(f"  {key:14s}: n={len(v):6d} h5={np.mean(v):+.4f}" if len(v) > 30 else f"  {key}: n<30")
    OUT["size"] = sz

    # ============ 8. ROBUSTNESS VS SIMPLE ALTERNATIVES ============
    print()
    print("=" * 74)
    print("8. ALTERNATIVE VETO FILTERS (FM h5 | common controls [ret1, ret5z, volz])")
    print("=" * 74)
    alts = {
        "bandar share>=0.55": flag,
        "coverage flag": have.fillna(False).astype(float),
        "platform nbz>=+1 (chase)": (nbz >= 1).astype(float),
        "platform divergence (up & nbz<=-0.5)": ((r1 >= 0.03) & (nbz <= -0.5)).astype(float),
        "volume spike z>=2": (volz >= 2).astype(float),
        "ret1>=+3% alone (UP3)": (r1 >= 0.03).astype(float),
    }
    alt_out = {}
    common = [r1, ret5z, volz]
    for nm, fl in alts.items():
        rr = sl.fm_regression(p, fl, mask & have, controls=common, k=5)
        alt_out[nm] = rr
        print(f"  {nm:40s}: beta={rr['fm_mean']:+.5f} t={rr['fm_t']:+.2f}")
    # pairwise: does bandar add beyond the best simple alternative (platform divergence)?
    pd_div = alts["platform divergence (up & nbz<=-0.5)"]
    rr = sl.fm_regression(p, flag, mask & have, controls=common + [pd_div], k=5)
    print(f"  {'bandar share | controls + platform-div':40s}: beta={rr['fm_mean']:+.5f} t={rr['fm_t']:+.2f}")
    alt_out["bandar | +platform-divergence"] = rr
    rr = sl.fm_regression(p, pd_div, mask & have, controls=common + [flag], k=5)
    print(f"  {'platform-div | controls + bandar share':40s}: beta={rr['fm_mean']:+.5f} t={rr['fm_t']:+.2f}")
    alt_out["platform-div | +bandar"] = rr
    # overlap cross-tab
    both = mask & have
    a = (share >= 0.55) & (nbz <= -0.5); b_ = (share >= 0.55)
    ov = float((b_ & (nbz <= -0.5)).fillna(False).values.sum() / max(1, b_.fillna(False).values.sum()))
    print(f"  overlap: share of heavy-share obs with platform-divergence flag: {ov:.1%}")
    OUT["alternatives"] = alt_out
    OUT["overlap_div"] = ov

    _here = os.path.dirname(os.path.abspath(__file__))
    _cache = os.path.normpath(os.path.join(_here, "cache"))
    _out = os.path.normpath(os.path.join(_cache, "bandar_filter_challenge.json"))
    if os.path.commonpath([_here, _out]) != _here:
        raise SystemExit("refusing to write outside the sprint directory")
    with open(_out, "w") as f:
        json.dump(OUT, f, indent=1, default=str)
    print("\nsaved -> cache/bandar_filter_challenge.json")


if __name__ == "__main__":
    main()
