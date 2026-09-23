"""D-053 pre-declared re-measurement of FWD-PM-VOLEX-SN-001 spec v2.

Implements PROTOCOL_DRAFT.md v2 sections 2-3 exactly, on the extended panel
(pre-2021 yfinance backfill + settled DB corpus), with ex-ante filters only.

GATE (frozen in D-053 before this script runs): formations 2000-07..2020-12,
    t >= 2.87  AND  mean increment >= +0.10 %/month.

Modes
    --selftest   synthetic panel with a planted effect / no effect; validates the
                 code path. Touches no real data.
    --dry        real data, STRUCTURAL counts only (months, universe sizes,
                 flags). Computes no return, so it is not a look at the outcome.
    (default)    the one real run. Refuses to run if RESULT.json exists: the
                 re-measurement is spent exactly once (D-053).

Why each choice (so nobody "fixes" it later):
- zero-volume filter looks only at the trailing 60 bars. The 2026-09-19 panel
  also required zero zero-volume bars in the 21 bars AFTER formation
  (ext_panel.py z_fwd) -- look-ahead, audit finding F-1.
- entry at close(E), E = first session after formation: the formation-day
  close computes the signal and cannot also be traded (F-3).
- a name with no bar at exit exits at its last traded close and is flagged,
  never dropped (F-8) -- dropping it would condition on survival.
- split back-adjustment applies to pre-2021 rows only; the DB corpus is
  already adjusted (data_gaps/README trap 1).
"""
import sys, os, json, hashlib, argparse
from datetime import datetime, timezone
import numpy as np, pandas as pd, warnings
warnings.filterwarnings('ignore')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, *[".."] * 5))
PM = os.path.join(HERE, "..", "..")
HIST = os.path.join(HERE, "work", "hist_pre2021.pkl")
SPLITS = os.path.join(PM, "data_gaps", "data", "split_hist.pkl")
SECTORS = os.path.join(HERE, "..", "sector_map_frozen_v2.csv")
RESULT = os.path.join(HERE, "RESULT.json")
CUT = pd.Timestamp("2021-07-05")          # DB corpus start; backfill ends here

# ---- frozen spec constants (PROTOCOL v2 section 2-4, D-053) ----
N_HIST, ADV_MIN, PX_MIN = 60, 1e9, 50.0
EXCL_Q, SECTOR_MIN = 0.90, 10
UNIV_MIN, HELD_MIN = 50, 20
COST_RT = 0.60                            # % round trip, reported only
GATE_T, GATE_MEAN = 2.87, 0.10
PRE = ("2000-07", "2020-12")


def sha256_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def frame_fp(df):
    return hashlib.sha256(pd.util.hash_pandas_object(
        df.reset_index(drop=True), index=False).values.tobytes()).hexdigest()


# ------------------------------------------------------------------ data
def load_real():
    sys.path.insert(0, ROOT)
    from data.db import connect
    H = pd.read_pickle(HIST)
    with connect(read_only=True) as c:
        D = pd.read_sql("SELECT ticker,date,open,high,low,close,volume "
                        "FROM ohlcv WHERE is_final=1", c)
    D = D[D.ticker != 'IHSG']
    D['date'] = pd.to_datetime(D.date); H['date'] = pd.to_datetime(H.date)
    H = H[H.date < CUT]
    cols = ['ticker', 'date', 'open', 'high', 'low', 'close', 'volume']
    prov = {"hist_fp": frame_fp(H[cols].sort_values(['ticker', 'date'])),
            "hist_bars": int(len(H)),
            "db_fp": frame_fp(D[cols].sort_values(['ticker', 'date'])),
            "db_bars": int(len(D)), "db_max_date": str(D.date.max().date()),
            "splits_sha256": sha256_file(SPLITS),
            "sectors_sha256": sha256_file(SECTORS)}
    O = pd.concat([H[cols], D[cols]], ignore_index=True)
    O = O.drop_duplicates(['ticker', 'date'], keep='last')
    O = O[(O.close > 0) & (O.low > 0) & (O.high >= O.low)]
    O = O.sort_values(['ticker', 'date']).reset_index(drop=True)
    O = split_adjust(O, pd.read_pickle(SPLITS))
    sec = pd.read_csv(SECTORS)
    # formations only in completed calendar months
    last_full = (pd.Timestamp(datetime.now()).to_period('M') - 1)
    return O, sec, prov, last_full


def split_adjust(O, SPL):
    SPL = SPL[SPL.ratio > 0].sort_values(['ticker', 'date'])
    fac = np.ones(len(O))
    idx = O.groupby('ticker', sort=False).indices
    dts_all = O.date.values
    for t, ev in SPL.groupby('ticker', sort=False):
        ii = idx.get(t)
        if ii is None:
            continue
        dts = dts_all[ii]; f = np.ones(len(ii))
        for sd, rt in zip(ev.date.values.astype('datetime64[ns]'), ev.ratio.values):
            f[dts < sd] *= rt
        f[dts >= np.datetime64(CUT)] = 1.0       # DB corpus already adjusted
        fac[ii] = f
    for c in ['open', 'high', 'low', 'close']:
        O[c] = O[c].astype('float64') / fac
    O['volume'] = O.volume.astype('float64') * fac
    return O


# ------------------------------------------------------------------ features
def features(O):
    g = O.groupby('ticker', sort=False)
    O['n_hist'] = g.cumcount() + 1
    O['val'] = O.close * O.volume
    r60 = lambda s, f: s.groupby(O.ticker, sort=False).transform(
        lambda x: getattr(x.rolling(N_HIST, min_periods=N_HIST), f)())
    O['adv60'] = r60(O.val, 'mean')
    hl2 = np.log(O.high / O.low) ** 2
    O['park60'] = np.sqrt(r60(hl2, 'mean') / (4 * np.log(2)))
    O['z60'] = r60((O.volume <= 0).astype(float), 'sum')
    O['ret1'] = g.close.pct_change()
    return O


# ------------------------------------------------------------------ core
def run_overlay(O, sec, last_full, returns=True, keep_names=False):
    O = features(O)
    cal = np.sort(O.date.unique())
    months = pd.Series(cal).dt.to_period('M')
    form = pd.Series(cal).groupby(months).max()
    form = form[form.index <= last_full]
    # entry session E = first calendar session after t
    pos = np.searchsorted(cal, form.values, side='right')
    ok = pos < len(cal)
    form = form[ok]; E = pd.Series(cal[pos[ok]], index=form.index)

    close_w = O.pivot(index='date', columns='ticker', values='close')
    close_ff = close_w.ffill()
    ret_w = O.pivot(index='date', columns='ticker', values='ret1')
    smap = dict(zip(sec.ticker, sec.sector))

    rows, prev_w = [], None
    per = list(form.index)
    for k, m in enumerate(per):
        t, e = form[m], E[m]
        if k + 1 >= len(per):
            break                                  # no exit: next entry unknown
        e2 = E[per[k + 1]]
        U = O[(O.date == t) & (O.n_hist >= N_HIST) & (O.adv60 >= ADV_MIN)
              & (O.close >= PX_MIN) & (O.volume > 0) & (O.z60 == 0)
              & O.park60.notna()].copy()
        rec = {"month": str(m), "t": str(pd.Timestamp(t).date()),
               "entry": str(pd.Timestamp(e).date()), "exit": str(pd.Timestamp(e2).date()),
               "univ_at_t": int(len(U))}
        if len(U) == 0:
            rec.update(valid=False, reason="empty universe"); rows.append(rec); continue
        U['sector'] = U.ticker.map(smap).fillna('UNLABELLED')
        U['held'] = True
        for s, gg in U.groupby('sector'):
            if len(gg) >= SECTOR_MIN:
                U.loc[gg.index, 'held'] = gg.park60 < gg.park60.quantile(EXCL_Q)
        # entry bar required -- removed from BOTH books
        ent = close_w.loc[e].reindex(U.ticker.values).values
        U['entry_px'] = ent
        U = U[~np.isnan(ent)]
        rec.update(univ=int(len(U)), held_n=int(U.held.sum()),
                   excluded_n=int((~U.held).sum()))
        if len(U) < UNIV_MIN or U.held.sum() < HELD_MIN:
            rec.update(valid=False, reason="below univ/held minimum"); rows.append(rec); continue
        tk = U.ticker.values
        stale = np.isnan(close_w.loc[e2, tk].values)   # no bar at exit: last traded close used
        window = ret_w.loc[(ret_w.index > e) & (ret_w.index <= e2), tk]
        big = (window.abs() > 0.35).any().values
        rec.update(valid=True, stale_exits=int(stale.sum()), big_moves=int(big.sum()))
        if keep_names:                               # selftest only
            rec.update(univ_names=list(tk), held_names=list(U[U.held].ticker))
        if returns:
            U['ret'] = (close_ff.loc[e2, tk].values / U.entry_px.values - 1) * 100
            inc = U[U.held].ret.mean() - U.ret.mean()
            w_h = pd.Series(1 / U.held.sum(), index=U[U.held].ticker)
            w_u = pd.Series(1 / len(U), index=U.ticker)
            if prev_w is None:
                to_h = to_u = 1.0
            else:
                to_h = 0.5 * w_h.sub(prev_w[0], fill_value=0).abs().sum()
                to_u = 0.5 * w_u.sub(prev_w[1], fill_value=0).abs().sum()
            prev_w = (w_h, w_u)
            U['terc'] = pd.qcut(U.adv60.rank(method='first'), 3, labels=[1, 2, 3])
            terc = {}
            for q, gq in U.groupby('terc'):
                if gq.held.sum() and len(gq):
                    terc[f"T{q}"] = float(gq[gq.held].ret.mean() - gq.ret.mean())
            rec.update(inc=float(inc),
                       inc_net=float(inc - COST_RT * (to_h - to_u)),
                       turn_held=float(to_h), turn_univ=float(to_u), terc=terc)
        rows.append(rec)
    return rows


# ------------------------------------------------------------------ stats
def nw_t(a, L=3):
    a = np.asarray(a, float); n = len(a); d = a - a.mean()
    v = d @ d / n
    for l in range(1, L + 1):
        v += 2 * (1 - l / (L + 1)) * (d[l:] @ d[:-l]) / n
    return a.mean() / np.sqrt(v / n)


def summarise(rows, lo, hi):
    v = [r for r in rows if r.get("valid") and lo <= r["month"] <= hi]
    out = {"window": f"{lo}..{hi}", "valid_months": len(v),
           "skipped_months": len([r for r in rows if not r.get("valid")
                                  and lo <= r["month"] <= hi])}
    if not v:
        return out
    out.update(median_univ=float(np.median([r["univ"] for r in v])),
               median_held=float(np.median([r["held_n"] for r in v])),
               stale_exits=int(sum(r["stale_exits"] for r in v)),
               big_moves=int(sum(r["big_moves"] for r in v)))
    if "inc" not in v[0] or len(v) < 3:
        return out
    a = np.array([r["inc"] for r in v]); n = len(a)
    out.update(mean=float(a.mean()), sd=float(a.std(ddof=1)),
               t=float(a.mean() / (a.std(ddof=1) / np.sqrt(n))),
               nw3_t=float(nw_t(a)), p_pos=float((a > 0).mean()),
               mean_net=float(np.mean([r["inc_net"] for r in v])))
    for q in ("T1", "T2", "T3"):
        b = np.array([r["terc"][q] for r in v if q in r["terc"]])
        if len(b) > 2:
            out[f"adv_{q}"] = {"mean": float(b.mean()),
                               "t": float(b.mean() / (b.std(ddof=1) / np.sqrt(len(b))))}
    return out


# ------------------------------------------------------------------ selftest
def synthetic(effect, seed=0, n=300, years=8):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2010-01-01", periods=252 * years)
    vol = rng.uniform(0.01, 0.05, n)                    # daily vol per name
    hi = vol > np.quantile(vol, 0.9)
    frames = []
    for i in range(n):
        drift = -effect / 21 / 100 if hi[i] else 0.0      # %/month -> daily
        # log-return drift net of -sigma^2/2 so the ARITHMETIC return carries the
        # planted effect; otherwise lognormal convexity hands high-vol names +s^2/2/day
        r = rng.normal(drift - vol[i] ** 2 / 2, vol[i], len(dates))
        c = 1e8 * np.exp(np.cumsum(r))      # high start: no name may hit the Rp50/ADV floors
        rngv = np.abs(rng.normal(0, vol[i], len(dates))) + vol[i] / 2
        frames.append(pd.DataFrame({"ticker": f"S{i:03d}", "date": dates,
            "open": c, "high": c * np.exp(rngv), "low": c * np.exp(-rngv),
            "close": c, "volume": 1e7}))
    O = pd.concat(frames, ignore_index=True)
    sec = pd.DataFrame({"ticker": [f"S{i:03d}" for i in range(n)],
                        "sector": [f"X{i % 12}" for i in range(n)]})
    O.attrs["hi"] = {f"S{i:03d}" for i in range(n) if hi[i]}
    return O, sec, pd.Timestamp(dates[-1]).to_period('M') - 1


def selftest():
    ok = True
    for eff, expect in ((4.0, "pos"), (0.0, "null")):
        O, sec, lf = synthetic(eff)
        rows = run_overlay(O, sec, lf, keep_names=True)
        s = summarise(rows, "0000", "9999")
        # oracle: the increment implied by the planted drift alone, per month
        # (share of planted names in the universe minus their share in the held book)
        hi = O.attrs["hi"]
        orc = np.mean([eff * (np.mean([x in hi for x in r["univ_names"]])
                              - np.mean([x in hi for x in r["held_names"]]))
                       for r in rows if r.get("valid")])
        se = s['sd'] / np.sqrt(s['valid_months'])
        print(f"  planted {eff:+.1f}%/mo: months {s['valid_months']}  mean {s['mean']:+.3f}"
              f"  oracle {orc:+.3f}  t {s['t']:+.2f}  held {s['median_held']:.0f}/{s['median_univ']:.0f}")
        ok &= abs(s['mean'] - orc) < 3 * se
        ok &= (s['t'] > 3) if expect == "pos" else (abs(s['t']) < 3)
        ok &= 0.85 < s['median_held'] / s['median_univ'] < 0.95
    # ex-ante check: zero volume AFTER formation must not change the universe
    O, sec, lf = synthetic(0.0, seed=1)
    base = run_overlay(O.copy(), sec, lf, returns=False)
    O2 = O.copy(); d = sorted(O2.date.unique())
    tgt = (O2.ticker == "S000") & (O2.date > d[400]) & (O2.date <= d[410])
    O2.loc[tgt, "volume"] = 0
    alt = run_overlay(O2, sec, lf, returns=False)
    t400 = pd.Timestamp(d[400])
    same = all(a["univ_at_t"] == b["univ_at_t"] for a, b in zip(base, alt)
               if pd.Timestamp(a["t"]) <= t400)
    print(f"  future zero-volume leaves past universes unchanged: {same}")
    ok &= same
    print("SELFTEST", "PASS" if ok else "FAIL")
    return ok


# ------------------------------------------------------------------ main
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    if not a.dry and os.path.exists(RESULT):
        sys.exit("RESULT.json exists: the D-053 re-measurement has been spent. Refusing to re-run.")
    O, sec, prov, lf = load_real()
    rows = run_overlay(O, sec, lf, returns=not a.dry)
    wins = {"PRE2021_GATING": PRE, "FULL": ("0000", "9999"),
            "2021_26_KNOWN": ("2021-01", "9999")}
    summ = {k: summarise(rows, *v) for k, v in wins.items()}
    if a.dry:
        print(json.dumps({"provenance": prov, "structure": summ}, indent=2))
        sys.exit(0)
    p = summ["PRE2021_GATING"]
    verdict = "CLEARS" if (p.get("t", -9) >= GATE_T and p.get("mean", -9) >= GATE_MEAN) else "FAILS"
    res = {"spec": "FWD-PM-VOLEX-SN-001 v2", "act": "D-053",
           "gate": {"window": PRE, "t_min": GATE_T, "mean_min": GATE_MEAN},
           "verdict": verdict, "script_sha256": sha256_file(os.path.abspath(__file__)),
           "generated_utc": datetime.now(timezone.utc).isoformat(),
           "provenance": prov, "summary": summ, "months": rows}
    json.dump(res, open(RESULT, "w"), indent=1)
    print(json.dumps({"verdict": verdict, "summary": summ}, indent=2))
