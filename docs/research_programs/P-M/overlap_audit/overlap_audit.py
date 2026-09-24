"""Overlap-inference audit of two frozen registrations' in-sample reference t-statistics.

    FWD-PM-FADE-001   (HYP-PM-0012)  registered h=20: -1.46% t -5.64 (IHSG), -1.47% t -8.20 (EW-book),
                                     ex-2025 -1.88% t -6.80;  12-month decision t < -2.5 on both
    FWD-PM-REGIME-002 (HYP-PM-0010)  reference FULL +2.17% t 6.29, ex-2025 +0.928% t 2.83;
                                     36-month decision one-sided t > 1.65

Both use a ONE-WAY ENTRY-DATE-CLUSTERED t. An event entered on day d and one entered on d+1 are
different clusters, but with 20-session (FADE) or up-to-60-session (T1) holds their windows share
most of their days, so their residuals are correlated across clusters. One-way date clustering
then understates the standard error. This audit re-estimates the SAME means with estimators that
allow for that overlap and reports how much the registered t-statistics shrink.

Estimators (same trade-weighted mean in 1-3; 4 is the literature's standard remedy):
  1. registered — one-way entry-date cluster (`cluster_t` from the frozen FADE script).
  2. month      — one-way cluster on the entry's calendar month.
  3. dk(L)      — residual sums per trading day, Bartlett-weighted cross-day covariances up to
                  lag L (Driscoll-Kraay form). L = 0 reproduces estimator 1 up to G/(G-1).
                  L = holding length is the overlap-consistent choice.
  4. calendar   — calendar-time portfolio (Fama 1998; Mitchell & Stafford 2000): each day, the
                  equal-weight excess return of every open position; Newey-West t (lag 5) on the
                  daily series. Different weighting (per day, not per trade); same sign question.
                  Gross of cost by construction.

A second issue is reported alongside (FADE only): the registered FADE endpoint subtracts the
0.60% round trip from the signal leg but not from the gross benchmarks, so a signal carrying no
information at all scores -0.60% per event and its "null = 0" is not the null. Rows marked GROSS
give the cost-free contrast. (T1 is a long strategy; its net-of-cost endpoint is correct.)

DESCRIPTIVE ONLY. Nothing here changes a frozen protocol, ledger or decision rule: any change
to either test's inference is an Owner deviation decision. The audit reads only the
registration-era corpus (data <= 2026-09-16; FADE signals <= 2026-07-29 as registered), which
ends before either forward test opened (REGIME-002 2026-09-18, FADE-001 2026-09-22).

    venv/bin/python docs/research_programs/P-M/overlap_audit/overlap_audit.py --selftest
    venv/bin/python docs/research_programs/P-M/overlap_audit/overlap_audit.py
"""
import argparse
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
FADE_SCRIPT = os.path.join(HERE, "..", "forward_fade", "scripts", "fade_failed_breakdown.py")
DATA_CUTOFF = "2026-09-16"
FADE_SIGNAL_END = "2026-07-29"
T1_COST = 0.006
REGISTERED = {
    "FADE h20 IHSG": (-1.46, -5.64), "FADE h20 EW-book": (-1.47, -8.20),
    "FADE h20 IHSG ex-2025": (-1.88, -6.80),
    "T1 FULL": (2.17, 6.29), "T1 ex-2025": (0.928, 2.83),
}


# ------------------------------------------------------------------ estimators
def cluster_t(x, groups):
    """Verbatim copy of the frozen cluster_t (fade_failed_breakdown.py / panel.py)."""
    x = np.asarray(x, float)
    groups = np.asarray(groups)
    n = len(x)
    if n < 3:
        return np.nan, np.nan
    mu = x.mean()
    e = x - mu
    s = pd.Series(e).groupby(groups).sum().values
    G = len(s)
    if G < 3:
        return mu, np.nan
    var = (s ** 2).sum() * (G / (G - 1)) / n ** 2
    if var <= 0:
        return mu, np.nan
    return mu, mu / np.sqrt(var)


def dk_t(x, dates, cal, L):
    """Trade-weighted mean; residual sums per trading day; Bartlett covariances to lag L."""
    x = np.asarray(x, float)
    n = len(x)
    mu = x.mean()
    pos = pd.DatetimeIndex(cal).get_indexer(pd.DatetimeIndex(dates))
    if (pos < 0).any():
        raise ValueError("event date not on the trading calendar")
    S = np.bincount(pos, weights=x - mu, minlength=len(cal))
    v = S @ S
    for lag in range(1, L + 1):
        v += 2.0 * (1.0 - lag / (L + 1.0)) * (S[lag:] @ S[:-lag])
    return mu, (mu / np.sqrt(v / n ** 2)) if v > 0 else np.nan


def nw_t(a, lag=5):
    a = np.asarray(a, float)
    a = a[~np.isnan(a)]
    n = len(a)
    d = a - a.mean()
    v = d @ d / n
    for k in range(1, lag + 1):
        v += 2 * (1 - k / (lag + 1)) * (d[k:] @ d[:-k]) / n
    return a.mean() / np.sqrt(v / n)


def calendar_time(cal, positions, n_days):
    """positions: iterable of (start_idx, stock_returns[array], bench_returns[array])."""
    num = np.zeros(n_days)
    cnt = np.zeros(n_days)
    for s, r, b in positions:
        ex = r - b
        ok = ~np.isnan(ex)
        idx = np.arange(s, s + len(r))[ok]
        np.add.at(num, idx, ex[ok])
        np.add.at(cnt, idx, 1)
    daily = np.where(cnt > 0, num / np.where(cnt > 0, cnt, 1), np.nan)
    daily = daily[cnt > 0]
    return float(np.nanmean(daily)), float(nw_t(daily, 5)), int(len(daily))


def all_estimators(x, dates, cal, hold):
    months = pd.DatetimeIndex(dates).to_period("M").astype(str)
    out = {"N": int(len(x)), "clusters": int(pd.Series(dates).nunique())}
    mu, t = cluster_t(x, dates)
    out["registered"] = [100 * mu, t]
    out["month"] = [100 * cluster_t(x, months)[0], cluster_t(x, months)[1]]
    for L in sorted({hold, 2 * hold}):
        m, tt = dk_t(x, dates, cal, L)
        out[f"dk_L{L}"] = [100 * m, tt]
    return out


# ------------------------------------------------------------------ data
def load(cutoff):
    sys.path.insert(0, ROOT)
    from data.db import connect
    with connect(read_only=True) as c:
        D = pd.read_sql("SELECT ticker,date,open,high,low,close,volume FROM ohlcv "
                        "WHERE is_final=1 AND close>0 AND volume>=0 AND date<=?", c, params=(cutoff,))
        ca = pd.read_sql("SELECT ticker,date,action FROM corporate_actions", c)
    D["date"] = pd.to_datetime(D["date"])
    D = D.sort_values(["ticker", "date"]).reset_index(drop=True)
    return D, ca


def fade_module():
    spec = importlib.util.spec_from_file_location("fade_frozen", FADE_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------------ FADE-001
def audit_fade(D, ca):
    F = fade_module()
    d = D[D.ticker != "IHSG"].copy().reset_index(drop=True)
    ihsg = D[D.ticker == "IHSG"].set_index("date")[["open", "close"]].sort_index()
    splits = ca[ca.action == "split"][["ticker", "date"]].copy()
    splits["date"] = pd.to_datetime(splits["date"])
    splits["is_split"] = 1
    d = F.build(d, splits)
    signal = d.liq & (d.low < d.lo20) & (d.close > d.lo20) & d.entry_open.notna()
    signal &= d.date <= pd.Timestamp(FADE_SIGNAL_END)
    sig = d[signal].copy()
    cal = pd.DatetimeIndex(np.sort(d.date.unique()))
    cpos = {t: i for i, t in enumerate(cal)}
    open_w = d.pivot(index="date", columns="ticker", values="open").reindex(cal)
    close_w = d.pivot(index="date", columns="ticker", values="close").reindex(cal)
    cc = close_w / close_w.shift(1) - 1
    co = close_w / open_w - 1
    liqprev = d.pivot(index="date", columns="ticker", values="liq").reindex(cal).shift(1).fillna(False).astype(bool)
    ew_cc = cc.where(liqprev).mean(axis=1).values
    ew_co = co.where(liqprev).mean(axis=1).values
    ih = ihsg.reindex(cal)
    ih_cc = (ih.close / ih.close.shift(1) - 1).values
    ih_co = (ih.close / ih.open - 1).values
    tcol = {t: j for j, t in enumerate(close_w.columns)}
    CC, CO = cc.values, co.values

    res = {"signals_total": int(len(sig)), "signal_dates": int(sig.date.nunique())}
    ewb = {h: d[d.liq].groupby("date")[f"fwd_open_{h}"].mean() for h in F.HORIZONS}
    for h in F.HORIZONS:
        s = sig[sig[f"exit_close_{h}"].notna() & (sig[f"bad_{h}"].fillna(1) == 0)].copy()
        stock = s[f"exit_close_{h}"] / s.entry_open - 1
        ihr = s[f"exit_date_{h}"].map(ih.close) / s.entry_date.map(ih.open) - 1
        ewr = s.date.map(ewb[h])
        for bname, bench, bcc, bco in (("IHSG", ihr, ih_cc, ih_co), ("EW-book", ewr, ew_cc, ew_co)):
            ok = bench.notna()
            x = (stock - F.COST - bench)[ok].values
            key = f"FADE h{h} {bname}"
            res[key] = all_estimators(x, s.date.values[ok], cal, h)
            # GROSS: the registered endpoint subtracts the 0.60% round trip from the signal leg
            # only (benchmarks are gross), so a signal with NO information scores -0.60%. For an
            # avoidance claim ("these names underperform") the cost-free contrast is the one
            # whose null is zero.
            xg = (stock - bench)[ok].values
            res[f"{key} GROSS"] = all_estimators(xg, s.date.values[ok], cal, h)
            pos = []
            for _, r in s[ok].iterrows():
                e = cpos[r.entry_date]
                j = tcol[r.ticker]
                sr = np.r_[CO[e, j], CC[e + 1:e + h, j]]
                br = np.r_[bco[e], bcc[e + 1:e + h]]
                pos.append((e, sr, br))
            m, t, nd = calendar_time(cal, pos, len(cal))
            res[key]["calendar"] = [100 * m * h, t, nd]          # gross by construction
            res[f"{key} GROSS"]["calendar"] = [100 * m * h, t, nd]
            if h == 20 and bname == "IHSG":
                yr = pd.DatetimeIndex(s.date).year != 2025
                ok2 = ok & yr
                x2 = (stock - F.COST - bench)[ok2].values
                res["FADE h20 IHSG ex-2025"] = all_estimators(x2, s.date.values[ok2], cal, h)
                res["FADE h20 IHSG ex-2025 GROSS"] = all_estimators(
                    (stock - bench)[ok2].values, s.date.values[ok2], cal, h)
    return res


# ------------------------------------------------------------------ REGIME-002 (T1)
def t1_trades(D, ca):
    """Replicates scripts/extract.py + panel.build + ma.py + ref002.py (spec 002 reference)."""
    df = D.copy()
    g = df.groupby("ticker", sort=False)
    df["ret"] = g["close"].pct_change()
    val = df.close * df.volume
    df["adv20"] = val.groupby(df.ticker).transform(lambda s: s.rolling(20, min_periods=15).mean())
    df["adv20"] = df.groupby("ticker", sort=False)["adv20"].shift(1)
    df["n"] = g.cumcount()
    sp = ca[ca.action == "split"][["ticker", "date"]].copy()
    sp["date"] = pd.to_datetime(sp["date"])
    sp["is_split"] = 1
    df = df.merge(sp, on=["ticker", "date"], how="left")
    df["is_split"] = df["is_split"].fillna(0)
    df["bad"] = ((df.ret.abs() > 0.35) | (df.is_split > 0)).astype(int)
    g = df.groupby("ticker", sort=False)
    df["ema20"] = g["close"].transform(lambda s: s.ewm(span=20, adjust=False, min_periods=20).mean())
    df["atr14"] = (df.high - df.low).groupby(df.ticker).transform(lambda s: s.rolling(14, min_periods=14).mean())
    df["slope"] = df.ema20 / df.groupby("ticker", sort=False)["ema20"].shift(10) - 1
    absmv = df.groupby("ticker", sort=False)["close"].transform(lambda s: s.diff().abs().rolling(20, min_periods=20).sum())
    df["ER"] = df.groupby("ticker", sort=False)["close"].transform(lambda s: (s - s.shift(20)).abs()) / absmv.replace(0, np.nan)
    above = (df.close > df.ema20).astype(float)
    df["pct_above"] = above.groupby(df.ticker).transform(lambda s: s.rolling(20, min_periods=20).mean())
    ihs = df[df.ticker == "IHSG"].set_index("date")["close"].sort_index().to_dict()
    d = df[df.ticker != "IHSG"].sort_values(["ticker", "date"]).reset_index(drop=True)
    g = d.groupby("ticker", sort=False)
    d["sl"] = g["slope"].shift(1)
    d["er"] = g["ER"].shift(1)
    d["pa"] = g["pct_above"].shift(1)
    d["UP"] = ((d.sl > 0.02) & (d.er >= 0.30) & (d.pa >= 0.70)).fillna(False).astype(bool)
    d["liq"] = ((d.adv20 >= 1e9) & (d.close >= 50) & (d.n >= 25)).fillna(False).astype(bool)
    d["nz"] = (d.volume > 0).astype(int)
    d["nz20"] = d.groupby("ticker", sort=False)["nz"].transform(lambda s: s.shift(1).rolling(20, min_periods=20).sum())
    tr = []
    for tk, x in d.groupby("ticker", sort=False):
        up = x.UP.values
        if not up.any():
            continue
        lq, nz, nz20 = x.liq.values, x.nz.values, x.nz20.values
        cl, hi, at, dt, bad = x.close.values, x.high.values, x.atr14.values, x.date.values, x.bad.values
        N = len(x)
        st = np.where(up & ~np.r_[False, up[:-1]] & lq & ~np.isnan(at) & (nz == 1) & (nz20 >= 18))[0]
        for i in st:
            peak = hi[i]
            j = min(i + 60, N - 1)
            for k in range(1, min(60, N - 1 - i) + 1):
                p = i + k
                peak = max(peak, hi[p])
                if cl[p] < peak - 3 * at[p]:
                    j = p
                    break
            if bad[i + 1:j + 1].sum() > 0:
                continue
            ie, ix = ihs.get(pd.Timestamp(dt[i])), ihs.get(pd.Timestamp(dt[j]))
            if ie is None or ix is None:
                continue
            tr.append((tk, pd.Timestamp(dt[i]), pd.Timestamp(dt[j]), cl[j] / cl[i] - 1 - T1_COST, ix / ie - 1))
    T = pd.DataFrame(tr, columns=["ticker", "date", "exit", "net", "mkt"])
    T["exc"] = T.net - T.mkt
    return T, d, ihs


def audit_t1(D, ca):
    T, d, ihs = t1_trades(D, ca)
    cal = pd.DatetimeIndex(np.sort(d.date.unique()))
    cpos = {t: i for i, t in enumerate(cal)}
    close_w = d.pivot(index="date", columns="ticker", values="close").reindex(cal)
    CC = (close_w / close_w.shift(1) - 1).values
    tcol = {t: j for j, t in enumerate(close_w.columns)}
    ihc = pd.Series(ihs).reindex(cal)
    ih_cc = (ihc / ihc.shift(1) - 1).values
    res = {"trades": int(len(T)), "mean_hold_sessions": None}
    holds = []
    for name, S in (("T1 FULL", T), ("T1 ex-2025", T[pd.DatetimeIndex(T.date).year != 2025])):
        res[name] = all_estimators(S.exc.values, S.date.values, cal, 60)
        m20 = dk_t(S.exc.values, S.date.values, cal, 20)
        res[name]["dk_L20"] = [100 * m20[0], m20[1]]
        pos = []
        for _, r in S.iterrows():
            i, j, c = cpos[r.date], cpos[r.exit], tcol[r.ticker]
            if j > i:
                pos.append((i + 1, CC[i + 1:j + 1, c], ih_cc[i + 1:j + 1]))
                holds.append(j - i)
        m, t, nd = calendar_time(cal, pos, len(cal))
        res[name]["calendar"] = [100 * m * 21, t, nd]
    res["mean_hold_sessions"] = float(np.mean(holds)) if holds else None
    return res


# ------------------------------------------------------------------ self-test (synthetic)
def simulate_null(n_days=1000, n_names=150, per_day=10, hold=20, factor_sd=0.01,
                  idio_sd=0.02, beta_sd=0.5, tilt=1.5, repeat=0.3, seed=0):
    """Null world: events carry ZERO true excess. Two realistic overlap channels:
    - selection tilt: events are drawn preferentially from names with high exposure to a
      common daily factor the equal-weight benchmark does not remove (failed-breakdown
      names are not a random draw), so overlapping events share that factor;
    - repetition: a name that signalled yesterday signals again with probability `repeat`."""
    rng = np.random.default_rng(seed)
    f = rng.normal(0, factor_sd, n_days)
    beta = rng.normal(0, beta_sd, n_names)
    R = beta[None, :] * f[:, None] + rng.normal(0, idio_sd, (n_days, n_names))
    R = R - R.mean(axis=1, keepdims=True)                      # excess over the EW book
    p = np.exp(tilt * beta)
    p /= p.sum()
    cal = pd.bdate_range("2020-01-01", periods=n_days)
    x, dates, pos, prev = [], [], [], []
    for t in range(n_days - hold):
        keep = [k for k in prev if rng.random() < repeat]
        fresh = rng.choice(n_names, max(per_day - len(keep), 0), replace=False, p=p)
        today = list(dict.fromkeys(keep + list(fresh)))[:per_day]
        for k in today:
            r = R[t + 1:t + 1 + hold, k]
            x.append(np.prod(1 + r) - 1)
            dates.append(cal[t])
            pos.append((t + 1, r, np.zeros(hold)))
        prev = today
    x = np.array(x)
    return x - x.mean() * 0, np.array(dates), cal, pos


def selftest(reps=100):
    """Synthetic null (no true effect) with the two overlap channels. Also checks that dk with
    L = 0 is the registered estimator up to its G/(G-1) small-sample factor."""
    rej = {"registered": 0, "month": 0, "dk_L20": 0, "calendar": 0}
    for s in range(reps):
        x, dates, cal, pos = simulate_null(seed=s)
        months = pd.DatetimeIndex(dates).to_period("M").astype(str)
        rej["registered"] += abs(cluster_t(x, dates)[1]) > 1.96
        rej["month"] += abs(cluster_t(x, months)[1]) > 1.96
        rej["dk_L20"] += abs(dk_t(x, dates, cal, 20)[1]) > 1.96
        rej["calendar"] += abs(calendar_time(cal, pos, len(cal))[1]) > 1.96
    x, dates, cal, _ = simulate_null(seed=999)
    G = pd.Series(dates).nunique()
    ident = np.isclose(dk_t(x, dates, cal, 0)[1] / np.sqrt(G / (G - 1)), cluster_t(x, dates)[1])
    rates = {k: v / reps for k, v in rej.items()}
    print("null rejection rate at |t| > 1.96 (nominal 0.05):", rates)
    print("dk(L=0) == registered cluster_t up to G/(G-1):", bool(ident))
    return rates, bool(ident)


# ------------------------------------------------------------------ main
ORDER = ["FADE h20 IHSG", "FADE h20 IHSG GROSS", "FADE h20 EW-book", "FADE h20 EW-book GROSS",
         "FADE h20 IHSG ex-2025", "FADE h20 IHSG ex-2025 GROSS",
         "FADE h5 EW-book", "FADE h5 EW-book GROSS", "T1 FULL", "T1 ex-2025"]


def summarize(res):
    rows = []
    for key in ORDER:
        r = res.get(key)
        if not r:
            continue
        m_reg, t_reg = REGISTERED.get(key, (None, None))
        hold = 60 if key.startswith("T1") else int(key.split()[1][1:])
        dk1, dk2 = r.get(f"dk_L{hold}"), r.get(f"dk_L{2 * hold}")
        rows.append({
            "test": key,
            "registered": f"{m_reg:+.2f}% t {t_reg:+.2f}" if m_reg is not None else "-",
            "reproduced": f"{r['registered'][0]:+.2f}% t {r['registered'][1]:+.2f}",
            "N": r["N"], "dates": r["clusters"],
            "t_month": round(r["month"][1], 2),
            "t_dk_hold": round(dk1[1], 2) if dk1 else None,
            "t_dk_2hold": round(dk2[1], 2) if dk2 else None,
            "t_calendar": round(r["calendar"][1], 2) if "calendar" in r else None,
            "shrink": round(dk1[1] / r["registered"][1], 2) if dk1 else None})
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--cutoff", default=DATA_CUTOFF)
    a = ap.parse_args()
    if a.selftest:
        selftest()
        sys.exit(0)
    D, ca = load(a.cutoff)
    out = {"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "data_cutoff": a.cutoff, "fade_signal_end": FADE_SIGNAL_END,
           "rows": int(len(D)), "descriptive_only": True}
    out["fade"] = audit_fade(D, ca)
    out["t1"] = audit_t1(D, ca)
    out["summary"] = summarize({**out["fade"], **out["t1"]})
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    with open(os.path.join(HERE, f"RESULT_{stamp}.json"), "w") as f:
        json.dump(out, f, indent=1, default=str)
    print(pd.DataFrame(out["summary"]).to_string(index=False))
    print(f"\nT1 mean hold {out['t1']['mean_hold_sessions']:.1f} sessions; "
          f"FADE signals {out['fade']['signals_total']:,} on {out['fade']['signal_dates']:,} dates")
