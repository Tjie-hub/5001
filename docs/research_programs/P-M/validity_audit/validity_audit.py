"""Data- and result-validity audit, 2026-09-24. DESCRIPTIVE ONLY.

Answers, on the real DB, the questions the cloud-side audit could not
(`docs/research_programs/AUDIT_2026-09-24_RESULT_VALIDITY.md` §3):

  A  corpus    is_final share, weekend rows, partial sessions, IHSG gaps, non-session rows (ZV-2)
  B  survivor  does the corpus hold names that stopped trading, or only names listed today?
  C  big moves every single-session |ret| > 25%, classified against corporate_actions (split),
               corporate_action_events (by action_type) and suspension_events; DB split continuity
  D  DATA-3    ex-date returns per corporate_action_events.action_type (rightissue, bonus, ...)
               against ordinary sessions; raw_json key census for building adjustment factors
  E  guard     what the holding-window contamination guard (|ret| > 35% or a split inside the
               HOLDING window, i.e. future information) removed from FADE-001 and T1; the FADE
               EW-book with the same guard applied to the benchmark names; both with every
               corporate-action window removed
  F  arms      pattern-scan arms re-measured GROSS at next-open entry, vs IHSG and the EW-book,
               with the registered entry-date t next to month-cluster, Driscoll-Kraay and
               calendar-time t (estimators from ../overlap_audit/overlap_audit.py)

Nothing here changes a frozen protocol, ledger, registry or decision rule. The FADE and T1
reads use the registration-era corpus (data <= 2026-09-16, FADE signals <= 2026-07-29), which
ends before either forward test opened.

    venv/bin/python docs/research_programs/P-M/validity_audit/validity_audit.py
    venv/bin/python docs/research_programs/P-M/validity_audit/validity_audit.py --only A,B,C,D
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
OA_PATH = os.path.join(HERE, "..", "overlap_audit", "overlap_audit.py")

BIG = 0.25                 # classification threshold for section C
BAND = 0.35                # no IDX band allows a larger one-session move (engine.SPLIT_BAND)
MATCH_BARS = 3             # an event within +/- 3 of the ticker's own bars explains a move
CA_WINDOW_TYPES = ("rightissue", "bonus", "stocksplit", "warrant")
CLASS_ORDER = ("split", "stocksplit", "bonus", "rightissue", "warrant", "dividend", "rups",
               "suspension", "after_zero_volume", "after_calendar_gap", "unmatched")


def _oa():
    spec = importlib.util.spec_from_file_location("overlap_audit", OA_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------------ pure helpers (tested)
def rolling_slope(y: pd.Series, w: int = 20) -> pd.Series:
    """OLS slope of y on 0..w-1 over a trailing window of w bars (patterns.py `slope`),
    in closed form: cov(t, y) / var(t) with t the bar counter."""
    t = pd.Series(np.arange(len(y), dtype=float), index=y.index)
    m_ty = (t * y).rolling(w, min_periods=w).mean()
    m_y = y.rolling(w, min_periods=w).mean()
    m_t = t - (w - 1) / 2.0
    return (m_ty - m_t * m_y) / ((w * w - 1) / 12.0)


def event_positions(bar_dates: np.ndarray, event_dates: np.ndarray) -> np.ndarray:
    """Index of the first own bar on or after each event date (len(bar_dates) if none)."""
    return np.searchsorted(np.asarray(bar_dates, "datetime64[ns]"),
                           np.asarray(event_dates, "datetime64[ns]"), side="left")


def window_has_event(starts, ends, event_dates) -> np.ndarray:
    """For per-position windows (start, end] -- start EXCLUSIVE, end inclusive -- True if any
    event date falls inside. The entry price is already on the post-event basis when the
    event dates on the entry day itself (next-open entry) or on the entry bar (close entry),
    so only events strictly after the entry date can put a basis gap inside the return.
    event_dates: one ticker's events."""
    ev = np.sort(np.asarray(event_dates, "datetime64[ns]"))
    if ev.size == 0:
        return np.zeros(len(starts), bool)
    lo = np.searchsorted(ev, np.asarray(starts, "datetime64[ns]"), side="right")
    hi = np.searchsorted(ev, np.asarray(ends, "datetime64[ns]"), side="right")
    return hi > lo


def classify_big_moves(P: pd.DataFrame, events: dict, thr: float = BIG,
                       match: int = MATCH_BARS) -> pd.DataFrame:
    """Every bar with |close/prev_close - 1| > thr, labelled with the first explaining cause
    in CLASS_ORDER. `events` maps a class name to a frame [ticker, date]. P must hold
    ticker, date, close, volume, sorted by ticker then date."""
    P = P.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    g = P.groupby("ticker", sort=False)
    P["ret"] = g["close"].pct_change()
    P["prev_vol0"] = g["volume"].shift(1).fillna(1).le(0)
    P["gap_days"] = g["date"].diff().dt.days
    P["bar"] = g.cumcount()
    B = P[P["ret"].abs() > thr].copy()
    if B.empty:
        return B.assign(cls=pd.Series(dtype=str))
    bars = {tk: x["date"].values for tk, x in P.groupby("ticker", sort=False)}
    evpos = {}
    for name, E in events.items():
        if E is None or E.empty:
            continue
        d = {}
        for tk, x in E.groupby("ticker"):
            if tk in bars:
                d[tk] = event_positions(bars[tk], pd.to_datetime(x["date"]).values)
        evpos[name] = d
    cls = []
    for tk, bar, pv0, gap in zip(B["ticker"].values, B["bar"].values, B["prev_vol0"].values,
                                 B["gap_days"].values):
        label = None
        for name in CLASS_ORDER:
            if name in evpos and tk in evpos[name] and np.any(np.abs(evpos[name][tk] - bar) <= match):
                label = name
                break
        if label is None:
            label = ("after_zero_volume" if pv0 else
                     "after_calendar_gap" if (gap == gap and gap > 7) else "unmatched")
        cls.append(label)
    B["cls"] = cls
    return B


def calendar_time_vec(n_days, entry_pos, cols, h, CO, CC, bco, bcc):
    """Vectorised calendar-time portfolio: day e gets the entry-day open->close excess, days
    e+1..e+h-1 the close->close excess; equal weight over open positions; NW(5) t on the
    daily series. Same construction as overlap_audit.calendar_time."""
    num = np.zeros(n_days)
    cnt = np.zeros(n_days)
    entry_pos = np.asarray(entry_pos)
    cols = np.asarray(cols)
    for k in range(h):
        rows = entry_pos + k
        inb = rows < n_days
        r, c = rows[inb], cols[inb]
        if k == 0:
            ex = CO[r, c] - bco[r]
        else:
            ex = CC[r, c] - bcc[r]
        ok = ~np.isnan(ex)
        np.add.at(num, r[ok], ex[ok])
        np.add.at(cnt, r[ok], 1)
    daily = np.where(cnt > 0, num / np.where(cnt > 0, cnt, 1), np.nan)[cnt > 0]
    OA = _oa()
    return float(np.nanmean(daily)), float(OA.nw_t(daily, 5)), int(len(daily))


# ------------------------------------------------------------------ data
def load_all(cutoff):
    sys.path.insert(0, ROOT)
    from data.db import connect
    out = {}
    with connect(read_only=True) as c:
        D = pd.read_sql("SELECT ticker,date,open,high,low,close,volume FROM ohlcv "
                        "WHERE is_final=1 AND close>0 AND volume>=0 AND date<=?", c, params=(cutoff,))
        out["is_final"] = pd.read_sql("SELECT is_final, COUNT(*) AS n, MIN(date) AS first, "
                                      "MAX(date) AS last FROM ohlcv GROUP BY is_final", c)
        for name, q in (("ca", "SELECT ticker,date,action,value FROM corporate_actions"),
                        ("cae", "SELECT ticker,action_type,event_id,event_date,raw_json "
                                "FROM corporate_action_events"),
                        ("su", "SELECT ticker,last_normal_date,resume_date FROM suspension_events")):
            try:
                out[name] = pd.read_sql(q, c)
            except Exception as e:                      # table missing on this DB
                out[name] = pd.DataFrame()
                out[f"{name}_error"] = str(e)
    D["date"] = pd.to_datetime(D["date"])
    D = D.sort_values(["ticker", "date"]).reset_index(drop=True)
    return D, out


def event_frames(x):
    ev = {}
    ca, cae, su = x.get("ca", pd.DataFrame()), x.get("cae", pd.DataFrame()), x.get("su", pd.DataFrame())
    if not ca.empty:
        ev["split"] = ca[ca.action == "split"][["ticker", "date"]]
    if not cae.empty:
        c2 = cae.dropna(subset=["event_date"])
        for t in c2.action_type.unique():
            ev[str(t)] = c2[c2.action_type == t][["ticker"]].assign(date=c2.loc[c2.action_type == t, "event_date"])
    if not su.empty:
        ev["suspension"] = su.dropna(subset=["resume_date"])[["ticker"]].assign(
            date=su.dropna(subset=["resume_date"])["resume_date"])
    for k in list(ev):
        ev[k] = ev[k].assign(date=pd.to_datetime(ev[k]["date"], errors="coerce")).dropna(subset=["date"])
    return ev


# ------------------------------------------------------------------ A, B
def section_a(D, x):
    from research.rulecard import engine
    P = D[D.ticker != "IHSG"]
    cnt = P.groupby("date").size()
    ref = cnt.rolling(20, min_periods=10).median().shift(1)
    partial = cnt[cnt < 0.95 * ref]
    ns = engine.non_session_dates(P[["ticker", "date", "close", "volume"]])
    ih = set(D.loc[D.ticker == "IHSG", "date"])
    dates = pd.DatetimeIndex(sorted(P.date.unique()))
    val = P.close * P.volume
    adv = val.groupby(P.ticker).transform(lambda s: s.rolling(20, min_periods=15).mean().shift(1))
    liq = adv >= 1e9
    yr = P.date.dt.year
    return {
        "is_final": x["is_final"].to_dict("records"),
        "rows_final": int(len(D)), "tickers": int(P.ticker.nunique()),
        "first": str(dates.min().date()), "last": str(dates.max().date()), "sessions": int(len(dates)),
        "weekend_dates": [str(d.date()) for d in dates[dates.dayofweek >= 5]][:30],
        "partial_sessions_lt95pct": {str(k.date()): int(v) for k, v in partial.items()},
        "non_session_dates_zv2": [str(pd.Timestamp(d).date()) for d in ns],
        "sessions_missing_ihsg": [str(d.date()) for d in dates if d not in ih][:50],
        "n_sessions_missing_ihsg": int(sum(d not in ih for d in dates)),
        "zero_volume_share_by_year": {int(k): round(float(v), 4) for k, v in
                                      (P.volume <= 0).groupby(yr).mean().items()},
        "zero_volume_share_liquid_by_year": {int(k): round(float(v), 4) for k, v in
                                             (P.volume[liq] <= 0).groupby(yr[liq]).mean().items()},
    }


def section_b(D):
    P = D[D.ticker != "IHSG"]
    dates = pd.DatetimeIndex(sorted(P.date.unique()))
    pos = {d: i for i, d in enumerate(dates)}
    fl = P.groupby("ticker")["date"].agg(["min", "max", "size"])
    fl["first_pos"] = fl["min"].map(pos)
    fl["last_pos"] = fl["max"].map(pos)
    end = len(dates) - 1
    stopped = fl[fl.last_pos < end - 60].sort_values("max")
    return {
        "tickers": int(len(fl)),
        "start_within_5_sessions_of_corpus_start": int((fl.first_pos <= 5).sum()),
        "started_later": int((fl.first_pos > 5).sum()),
        "stopped_more_than_60_sessions_before_end": int(len(stopped)),
        "stopped_examples": [(t, str(r["max"].date()), int(r["size"]))
                             for t, r in stopped.head(40).iterrows()],
        "reading": ("If almost no ticker stops before the end, the corpus holds only names that "
                    "still trade today: survivorship is present and unmeasurable from this table."),
    }


# ------------------------------------------------------------------ C, D
def section_c(D, x):
    P = D[D.ticker != "IHSG"][["ticker", "date", "close", "volume"]]
    ev = event_frames(x)
    B = classify_big_moves(P, ev, BIG)
    val = D.close * D.volume
    adv = val.groupby(D.ticker).transform(lambda s: s.rolling(20, min_periods=15).mean().shift(1))
    advs = pd.Series(adv.values, index=pd.MultiIndex.from_arrays([D.ticker.values, D.date.values]))
    B["liquid"] = advs.reindex(pd.MultiIndex.from_arrays([B.ticker.values, B.date.values])).values >= 1e9
    out = {"threshold": BIG, "n": int(len(B)), "rows": int(len(P))}
    for lbl, S in (("all", B), ("gt35", B[B.ret.abs() > BAND]), ("liquid", B[B.liquid]),
                   ("liquid_gt35", B[B.liquid & (B.ret.abs() > BAND)])):
        out[lbl] = {"n": int(len(S)), "up": int((S.ret > 0).sum()), "down": int((S.ret < 0).sum()),
                    "by_class": {k: int(v) for k, v in S.cls.value_counts().items()}}
    U = B[B.cls == "unmatched"].reindex(B[B.cls == "unmatched"].ret.abs().sort_values(ascending=False).index)
    out["unmatched_top"] = [(r.ticker, str(r.date.date()), round(float(r.ret), 3), bool(r.liquid))
                            for r in U.head(40).itertuples()]
    out["split_continuity"] = split_continuity(D, x.get("ca", pd.DataFrame()))
    return out


def split_continuity(D, ca):
    """Is the DB's split basis continuous (already adjusted) or gapped (raw) at each split?"""
    if ca.empty:
        return {"note": "corporate_actions empty or missing"}
    sys.path.insert(0, ROOT)
    from data.adjustments import _gap_is_real, MIN_VERIFIABLE_RATIO
    sp = ca[ca.action == "split"].copy()
    sp["ratio"] = pd.to_numeric(sp["value"], errors="coerce")
    sp = sp[(sp.ratio > 0) & (np.maximum(sp.ratio, 1 / sp.ratio) >= MIN_VERIFIABLE_RATIO)]
    by = {t: x for t, x in D.groupby("ticker")}
    gapped, cont, nodata = [], 0, 0
    for r in sp.itertuples():
        x = by.get(r.ticker)
        if x is None or not (x.date < pd.Timestamp(r.date)).any() or not (x.date >= pd.Timestamp(r.date)).any():
            nodata += 1
            continue
        dates = x.date.dt.strftime("%Y-%m-%d").reset_index(drop=True)
        closes = x.close.reset_index(drop=True)
        if _gap_is_real(dates, closes, str(r.date)[:10], float(r.ratio)):
            gapped.append((r.ticker, str(r.date)[:10], float(r.ratio)))
        else:
            cont += 1
    return {"verifiable_splits": int(len(sp)), "continuous_in_db": cont, "gapped_in_db": len(gapped),
            "outside_corpus": nodata, "gapped": gapped[:40]}


def section_d(D, x):
    cae = x.get("cae", pd.DataFrame())
    if cae.empty:
        return {"note": "corporate_action_events empty or missing"}
    P = D[D.ticker != "IHSG"].copy()
    g = P.groupby("ticker", sort=False)
    P["ret"] = g["close"].pct_change()
    base = P.ret.dropna()
    out = {"baseline": {"n": int(len(base)), "median": float(base.median()),
                        "share_lt_-10pct": float((base < -0.10).mean()),
                        "share_lt_-20pct": float((base < -0.20).mean()),
                        "share_gt_+50pct": float((base > 0.50).mean())}}
    bars = {tk: (x_.date.values, x_.ret.values) for tk, x_ in P.groupby("ticker", sort=False)}
    c2 = cae.dropna(subset=["event_date"]).copy()
    c2["event_date"] = pd.to_datetime(c2["event_date"], errors="coerce")
    c2 = c2.dropna(subset=["event_date"])
    lo, hi = P.date.min(), P.date.max()
    for t, E in c2.groupby("action_type"):
        E = E[(E.event_date > lo) & (E.event_date <= hi)]
        rets = []
        for r in E.itertuples():
            b = bars.get(r.ticker)
            if b is None:
                continue
            i = int(event_positions(b[0], np.array([r.event_date.to_datetime64()]))[0])
            if i < len(b[1]) and not np.isnan(b[1][i]):
                rets.append(b[1][i])
        rr = pd.Series(rets, dtype=float)
        keys = sorted({k for s in E.raw_json.head(200) for k in _json_keys(s)})
        out[str(t)] = {"events_in_corpus": int(len(E)), "matched_bars": int(len(rr)),
                       "median": float(rr.median()) if len(rr) else None,
                       "mean": float(rr.mean()) if len(rr) else None,
                       "share_lt_-10pct": float((rr < -0.10).mean()) if len(rr) else None,
                       "share_lt_-20pct": float((rr < -0.20).mean()) if len(rr) else None,
                       "share_gt_+50pct": float((rr > 0.50).mean()) if len(rr) else None,
                       "raw_json_keys": keys[:60],
                       "samples": [str(s)[:400] for s in E.raw_json.head(2)]}
    return out


def _json_keys(s):
    try:
        v = json.loads(s)
        return list(v.keys()) if isinstance(v, dict) else []
    except Exception:
        return []


# ------------------------------------------------------------------ E, F (FADE build panel)
def fade_panel(D, x, OA):
    F = OA.fade_module()
    d = D[D.ticker != "IHSG"].copy().reset_index(drop=True)
    ihsg = D[D.ticker == "IHSG"].set_index("date")[["open", "close"]].sort_index()
    ca = x.get("ca", pd.DataFrame())
    sp = ca[ca.action == "split"][["ticker", "date"]].copy() if not ca.empty else pd.DataFrame(columns=["ticker", "date"])
    sp["date"] = pd.to_datetime(sp["date"])
    sp["is_split"] = 1
    d = F.build(d, sp)
    cal = pd.DatetimeIndex(np.sort(d.date.unique()))
    close_w = d.pivot(index="date", columns="ticker", values="close").reindex(cal)
    open_w = d.pivot(index="date", columns="ticker", values="open").reindex(cal)
    liqprev = d.pivot(index="date", columns="ticker", values="liq").reindex(cal).shift(1).fillna(False).astype(bool)
    CC = (close_w / close_w.shift(1) - 1)
    CO = (close_w / open_w - 1)
    ih = ihsg.reindex(cal)
    M = {"F": F, "d": d, "cal": cal, "cpos": {t: i for i, t in enumerate(cal)},
         "tcol": {t: j for j, t in enumerate(close_w.columns)},
         "CC": CC.values, "CO": CO.values,
         "ew_cc": CC.where(liqprev).mean(axis=1).values, "ew_co": CO.where(liqprev).mean(axis=1).values,
         "ih": ih, "ih_cc": (ih.close / ih.close.shift(1) - 1).values, "ih_co": (ih.close / ih.open - 1).values}
    return M


def _est(OA, x, dates, cal, h):
    r = OA.all_estimators(np.asarray(x, float), np.asarray(dates), cal, h)
    return {k: v for k, v in r.items()}


def _bench(M, s, h, kind, ewb):
    if kind == "IHSG":
        return s[f"exit_date_{h}"].map(M["ih"].close) / s.entry_date.map(M["ih"].open) - 1
    return s.date.map(ewb[h])


def _calendar(M, s, h, kind):
    e = s.entry_date.map(M["cpos"]).values.astype(int)
    c = s.ticker.map(M["tcol"]).values.astype(int)
    bco, bcc = (M["ih_co"], M["ih_cc"]) if kind == "IHSG" else (M["ew_co"], M["ew_cc"])
    m, t, nd = calendar_time_vec(len(M["cal"]), e, c, h, M["CO"], M["CC"], bco, bcc)
    return [100 * m * h, t, nd]


def ca_window_flags(tickers, starts, ends, ev, types=CA_WINDOW_TYPES):
    """True where the ticker has a corporate-action event (or a recorded split) in
    (start, end]. Uses the event date as recorded (ex-date when the source has one)."""
    tickers = np.asarray(tickers)
    starts, ends = np.asarray(starts, "datetime64[ns]"), np.asarray(ends, "datetime64[ns]")
    flags = np.zeros(len(tickers), bool)
    use = [t for t in list(types) + ["split"] if t in ev]
    if not use:
        return flags
    E = pd.concat([ev[t] for t in use], ignore_index=True)
    byt = {t: x_.date.values for t, x_ in E.groupby("ticker")}
    for tk in np.unique(tickers):
        if tk in byt:
            idx = np.where(tickers == tk)[0]
            flags[idx] = window_has_event(starts[idx], ends[idx], byt[tk])
    return flags


def section_e(D, x, OA, M):
    F, d, cal = M["F"], M["d"], M["cal"]
    ev = event_frames(x)
    ewb = {h: d[d.liq].groupby("date")[f"fwd_open_{h}"].mean() for h in F.HORIZONS}
    # the same holding-window guard applied to the benchmark names (symmetric)
    ewb_sym = {h: d[d.liq & (d[f"bad_{h}"].fillna(1) == 0)].groupby("date")[f"fwd_open_{h}"].mean()
               for h in F.HORIZONS}
    sig = d[d.liq & (d.low < d.lo20) & (d.close > d.lo20) & d.entry_open.notna()
            & (d.date <= pd.Timestamp(OA.FADE_SIGNAL_END))].copy()
    out = {"fade": {}, "t1": {}}
    for h in (5, 20):
        s = sig[sig[f"exit_close_{h}"].notna()].copy().reset_index(drop=True)
        guard = s[f"bad_{h}"].fillna(1) > 0
        stock = s[f"exit_close_{h}"] / s.entry_open - 1
        caw = ca_window_flags(s.ticker.values, s.entry_date.values, s[f"exit_date_{h}"].values, ev)
        res = {"signals_with_exit": int(len(s)), "dropped_by_guard": int(guard.sum()),
               "ca_window_among_kept": int((caw & ~guard).sum())}
        for kind in ("IHSG", "EW-book"):
            b = _bench(M, s, h, kind, ewb)
            ex = stock - b
            ok = b.notna()
            k = ok & ~guard
            res[f"{kind} kept GROSS (registered set)"] = _est(OA, ex[k], s.date[k], cal, h)
            res[f"{kind} dropped-by-guard GROSS mean%"] = (float(100 * ex[ok & guard].mean())
                                                         if (ok & guard).any() else None)
            res[f"{kind} kept+dropped GROSS"] = _est(OA, ex[ok], s.date[ok], cal, h)
            k2 = k & ~caw
            res[f"{kind} kept, no CA window GROSS"] = _est(OA, ex[k2], s.date[k2], cal, h)
            if kind == "EW-book":
                bs = s.date.map(ewb_sym[h])
                k3 = k & bs.notna()
                res["EW-book(symmetric guard) kept GROSS"] = _est(OA, (stock - bs)[k3], s.date[k3], cal, h)
        dropped = s[guard]
        if len(dropped):
            # direction of the move that triggered the guard: min/max daily return in the window
            res["dropped_trigger_direction"] = _trigger_direction(d, dropped, h)
        out["fade"][f"h{h}"] = res
    out["t1"] = t1_guard(D, x, OA, ev)
    return out


def _trigger_direction(d, dropped, h):
    g = d.set_index(["ticker", "date"])["ret"]
    up = down = split_only = 0
    for r in dropped.itertuples():
        w = d[(d.ticker == r.ticker) & (d.date >= r.entry_date) & (d.date <= getattr(r, f"exit_date_{h}"))]["ret"]
        if (w > BAND).any():
            up += 1
        elif (w < -BAND).any():
            down += 1
        else:
            split_only += 1
        if up + down + split_only >= 400:          # cap the loop; enough for a direction read
            break
    return {"sampled": up + down + split_only, "up_gt35": up, "down_gt35": down, "split_flag_only": split_only}


def t1_guard(D, x, OA, ev):
    T, d, ihs = OA.t1_trades(D, x.get("ca", pd.DataFrame(columns=["ticker", "date", "action"])))
    cal = pd.DatetimeIndex(np.sort(d.date.unique()))
    kept, dropped = [], []
    for tk, xx in d.groupby("ticker", sort=False):
        up = xx.UP.values
        if not up.any():
            continue
        lq, nz, nz20 = xx.liq.values, xx.nz.values, xx.nz20.values
        cl, hi, at, dt, bad, rt = (xx.close.values, xx.high.values, xx.atr14.values, xx.date.values,
                                   xx.bad.values, xx.ret.values)
        N = len(xx)
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
            ie, ix = ihs.get(pd.Timestamp(dt[i])), ihs.get(pd.Timestamp(dt[j]))
            if ie is None or ix is None:
                continue
            row = (tk, pd.Timestamp(dt[i]), pd.Timestamp(dt[j]), cl[j] / cl[i] - 1 - OA.T1_COST, ix / ie - 1,
                   float(np.nanmax(rt[i + 1:j + 1])) if j > i else 0.0,
                   float(np.nanmin(rt[i + 1:j + 1])) if j > i else 0.0)
            (dropped if bad[i + 1:j + 1].sum() > 0 else kept).append(row)
    cols = ["ticker", "date", "exit", "net", "mkt", "maxret", "minret"]
    K, X = pd.DataFrame(kept, columns=cols), pd.DataFrame(dropped, columns=cols)
    K["exc"], X["exc"] = K.net - K.mkt, X.net - X.mkt
    assert len(K) == len(T) and abs(K.exc.sum() - T.exc.sum()) < 1e-6, "T1 replication drifted"
    caw = ca_window_flags(K.ticker.values, K.date.values, K.exit.values, ev)   # close entry at date
    out = {"kept": int(len(K)), "dropped_by_guard": int(len(X)),
           "dropped_mean_exc_pct": float(100 * X.exc.mean()) if len(X) else None,
           "dropped_up_gt35": int((X.maxret > BAND).sum()), "dropped_down_gt35": int((X.minret < -BAND).sum()),
           "kept_with_ca_window": int(caw.sum())}
    ex25 = pd.DatetimeIndex(K.date).year != 2025
    A = pd.concat([K, X], ignore_index=True)
    for lbl, S, m in (("FULL kept (registered)", K, None), ("ex-2025 kept (registered)", K, ex25),
                      ("ex-2025 kept+dropped", A, pd.DatetimeIndex(A.date).year != 2025),
                      ("ex-2025 kept, no CA window", K, ex25 & ~caw)):
        S2 = S if m is None else S[np.asarray(m)]
        r = OA.all_estimators(S2.exc.values, S2.date.values, cal, 60)
        m20 = OA.dk_t(S2.exc.values, S2.date.values, cal, 20)
        r["dk_L20"] = [100 * m20[0], m20[1]]
        out[lbl] = r
    return out


def section_f(D, x, OA, M):
    F, d, cal = M["F"], M["d"], M["cal"]
    g = d.groupby("ticker", sort=False)
    d["hi20"] = g["high"].transform(lambda s: s.rolling(20, min_periods=20).max()).groupby(d.ticker).shift(1)
    d["rng20"] = (d.hi20 - d.lo20) / d.close
    rng40 = (g["high"].transform(lambda s: s.rolling(40, min_periods=40).max())
             - g["low"].transform(lambda s: s.rolling(40, min_periods=40).min())) / d.close
    d["rng40"] = rng40.groupby(d.ticker).shift(1)
    d["sh"] = (g["high"].transform(rolling_slope) / d.close).groupby(d.ticker).shift(1)
    d["slo"] = (g["low"].transform(rolling_slope) / d.close).groupby(d.ticker).shift(1)
    conv = (d.sh < 0) & (d.slo < 0) & (d.sh < d.slo) & (d.rng20 < 0.8 * d.rng40)
    base = d.liq & d.entry_open.notna() & (d.date <= pd.Timestamp(OA.FADE_SIGNAL_END))
    arms = {
        "P2 resistance breakout": base & (d.close > d.hi20),
        "P3a failed breakdown": base & (d.low < d.lo20) & (d.close > d.lo20),
        "P3b failed breakout": base & (d.high > d.hi20) & (d.close < d.hi20),
        "P4 falling wedge + break": base & conv & (d.close > g["high"].shift(1)),
        "P4b falling wedge": base & conv,
    }
    ewb = {h: d[d.liq].groupby("date")[f"fwd_open_{h}"].mean() for h in F.HORIZONS}
    rows = []
    for name, m in arms.items():
        for h in (5, 20):
            s = d[m & d[f"exit_close_{h}"].notna() & (d[f"bad_{h}"].fillna(1) == 0)].copy()
            stock = s[f"exit_close_{h}"] / s.entry_open - 1
            for kind in ("IHSG", "EW-book"):
                b = _bench(M, s, h, kind, ewb)
                ok = b.notna()
                ss, xg = s[ok], (stock - b)[ok]
                r = _est(OA, xg, ss.date, cal, h)
                net_t = OA.cluster_t((xg - F.COST).values, ss.date.values)[1]
                r["calendar"] = _calendar(M, ss, h, kind)
                rows.append({"arm": name, "h": h, "bench": kind, "N": r["N"],
                             "net%_registered_endpoint": round(100 * (xg.mean() - F.COST), 3),
                             "net_t_registered": round(float(net_t), 2),
                             "gross%": round(r["registered"][0], 3),
                             "t_entry_date": round(r["registered"][1], 2),
                             "t_month": round(r["month"][1], 2),
                             "t_dk_Lh": round(r[f"dk_L{h}"][1], 2),
                             "t_calendar": round(r["calendar"][1], 2)})
    return rows


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cutoff", default="2026-09-16")
    ap.add_argument("--only", default="A,B,C,D,E,F")
    a = ap.parse_args()
    want = set(a.only.upper().split(","))
    OA = _oa()
    D, x = load_all(a.cutoff)
    out = {"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "data_cutoff": a.cutoff, "descriptive_only": True,
           "load_errors": {k: v for k, v in x.items() if k.endswith("_error")}}
    if "A" in want:
        out["A_corpus"] = section_a(D, x)
        print("A done")
    if "B" in want:
        out["B_survivorship"] = section_b(D)
        print("B done")
    if "C" in want:
        out["C_big_moves"] = section_c(D, x)
        print("C done")
    if "D" in want:
        out["D_ca_ex_dates"] = section_d(D, x)
        print("D done")
    if want & {"E", "F"}:
        M = fade_panel(D, x, OA)
        if "E" in want:
            out["E_guard"] = section_e(D, x, OA, M)
            print("E done")
        if "F" in want:
            out["F_arms"] = section_f(D, x, OA, M)
            print("F done")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = os.path.join(HERE, f"RESULT_{stamp}.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=1, default=str)
    print_summary(out)
    print(f"\nwritten: {path}")


def print_summary(out):
    A = out.get("A_corpus")
    if A:
        print(f"\n[A] {A['tickers']} tickers, {A['sessions']} sessions {A['first']}..{A['last']}; "
              f"is_final {A['is_final']}")
        print(f"    weekend dates {len(A['weekend_dates'])}, partial sessions {len(A['partial_sessions_lt95pct'])}, "
              f"ZV-2 non-sessions {len(A['non_session_dates_zv2'])}, sessions missing IHSG {A['n_sessions_missing_ihsg']}")
        print(f"    zero-volume share (liquid) by year {A['zero_volume_share_liquid_by_year']}")
    B = out.get("B_survivorship")
    if B:
        print(f"[B] {B['tickers']} tickers; start at corpus start {B['start_within_5_sessions_of_corpus_start']}; "
              f"stopped >60 sessions before end {B['stopped_more_than_60_sessions_before_end']}")
    C = out.get("C_big_moves")
    if C:
        for k in ("all", "gt35", "liquid", "liquid_gt35"):
            print(f"[C] |ret|>{'35%' if 'gt35' in k else '25%'} {k:12s} n={C[k]['n']:6d} up={C[k]['up']:5d} "
                  f"down={C[k]['down']:5d} {C[k]['by_class']}")
        print(f"[C] split continuity {({k: v for k, v in C['split_continuity'].items() if k != 'gapped'})}")
    Dd = out.get("D_ca_ex_dates")
    if Dd and "baseline" in Dd:
        print(f"[D] baseline P(ret<-10%)={Dd['baseline']['share_lt_-10pct']:.4f}")
        for k, v in Dd.items():
            if k != "baseline" and isinstance(v, dict) and v.get("matched_bars"):
                print(f"[D] {k:12s} n={v['matched_bars']:5d} median={v['median']:+.4f} "
                      f"P(<-10%)={v['share_lt_-10pct']:.3f} P(<-20%)={v['share_lt_-20pct']:.3f} "
                      f"P(>+50%)={v['share_gt_+50pct']:.3f}")
    E = out.get("E_guard")
    if E:
        for h, r in E["fade"].items():
            print(f"[E] FADE {h}: signals {r['signals_with_exit']}, guard dropped {r['dropped_by_guard']}, "
                  f"CA-window kept {r['ca_window_among_kept']}, trigger {r.get('dropped_trigger_direction')}")
            for k, v in r.items():
                if isinstance(v, dict) and "registered" in v:
                    print(f"      {k:40s} N={v['N']:6d} {v['registered'][0]:+.3f}%  t_reg {v['registered'][1]:+.2f}"
                          f"  t_month {v['month'][1]:+.2f}  " +
                          "  ".join(f"t_{kk} {vv[1]:+.2f}" for kk, vv in v.items() if kk.startswith("dk")))
                elif "mean%" in k:
                    print(f"      {k:40s} {v}")
        t = E["t1"]
        print(f"[E] T1: kept {t['kept']}, guard dropped {t['dropped_by_guard']} (mean exc "
              f"{t['dropped_mean_exc_pct']}%, up>35 {t['dropped_up_gt35']}, down>35 {t['dropped_down_gt35']}), "
              f"kept with CA window {t['kept_with_ca_window']}")
        for k, v in t.items():
            if isinstance(v, dict) and "registered" in v:
                print(f"      {k:30s} N={v['N']:6d} {v['registered'][0]:+.3f}%  t_reg {v['registered'][1]:+.2f}"
                      f"  t_month {v['month'][1]:+.2f}  t_dk60 {v['dk_L60'][1]:+.2f}  t_dk20 {v['dk_L20'][1]:+.2f}")
    Fr = out.get("F_arms")
    if Fr:
        print("\n[F] pattern-scan arms, next-open entry, GROSS (registered endpoint shown for reference)")
        print(pd.DataFrame(Fr).to_string(index=False))


if __name__ == "__main__":
    main()
