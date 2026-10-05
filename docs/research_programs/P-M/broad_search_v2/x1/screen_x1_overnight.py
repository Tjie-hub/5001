"""X1 overnight transmission screen -- FROZEN driver rev 4 (2026-10-05, REVIEW_R2bis re-freeze).

Committed FROZEN with PREDECLARATION_X1_OVERNIGHT.md rev 4 (+ .sha256) and
pit_tests_x1.py (T1-T3 + T1-SPY + T4). MUST NOT RUN until some line of some
REVIEW_R2*.md contains the exact hash-bound line (N3 guard, enforced in main()):
  R2-DECISION: X1 GO driver_sha256=<this file's sha> predeclaration_sha256=<pre sha>
One run after GO -> RESULT_X1_<utc>.json via research/tracking.py.

REV 4 changes (authority: REVIEW_R2bis_2026-10-05.md, "pre-run amendments"):
  N1  gap_tlkm built in books() (absorption loop no longer crashes after arms).
  N2  SPY arm = RAW compounded US-window return standardized (no beta, no hedge
      leg) -- code aligned to the spec; rev 3 wrongly residualized it.
  N3  guard scans ALL lines of ALL REVIEW_R2*.md; candidates without both 64-hex
      shas ignored; full match against disk required; otherwise refuse listing
      every candidate (fail-closed).
  EXTRA (disclosed in HANDOFF_R2ter + predeclaration rev 4): the rev-3
  build_signal regression target was y_map[p][1] (session count k) instead of
  y_map[p][0] (the US return) -- beta was garbage for EIDO/TLK. Fixed here; T1-T3
  could not catch it (invariance, not correctness).
  Cleanups: dead beta_cache deleted; empty_a computed; E4 disclosure carries both
  halves' boundary counts.
REV 3 corrections (REVIEW_R2) and rev 2 items: see the docstring history in git
and PREDECLARATION_X1_OVERNIGHT.md's amendments sections (B1-B5, E1-E5, minors).
"""
import hashlib
import importlib.util
import json
import sys
from bisect import bisect_right
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]                      # broad_search_v2/x1 -> repo root
sys.path.insert(0, str(ROOT))

DRIVER_SHA = hashlib.sha256((HERE / "screen_x1_overnight.py").read_bytes()).hexdigest()
PRE_SHA = hashlib.sha256((HERE / "PREDECLARATION_X1_OVERNIGHT.md").read_bytes()).hexdigest()

BAR = 3.2745                    # frozen: E[max|Z|] at N = 555 + 6 arms (bar_v2 integral)
TICK_MAX = 0.005
ADV_MIN = 5e9
SPLIT_DATE = pd.Timestamp("2021-07-05")
END_FROZEN = pd.Timestamp("2026-07-29")     # confirmation end frozen (REVIEW_R1 3)
K_MAX = 3
Q_POS = 100e6
RT_FLOOR = 0.006
CUT = 0.430727
PARAMS = {"issuance": True, "adv_min": ADV_MIN, "tick_max_frac": TICK_MAX,
          "beta_rolling": 250, "beta_min_pairs": 120, "sigma_rolling": 250,
          "sigma_min": 120, "nw_lags": 5, "tercile_cut": CUT, "k_max": K_MAX,
          "end_frozen": str(END_FROZEN),
          "db": "local walkforward.db (fingerprint + max date recorded by tracking)"}


def norm_cdf(x):
    from math import erf, sqrt
    return 0.5 * (1.0 + np.vectorize(erf)(np.clip(x, -30, 30) / sqrt(2.0)))


def us_close_wib_ts(us_dates):
    """US close of session date t as WIB timestamp: 03:00 WIB t+1 (EDT) / 04:00 (EST)."""
    dt = pd.DatetimeIndex(us_dates)
    y, m, d = dt.year, dt.month, dt.day
    edt = ((m > 3) & (m < 11))
    for i in range(len(dt)):
        w = pd.Timestamp(year=y[i], month=3, day=1).weekday()
        edt[i] = edt[i] or (m[i] == 3 and d[i] >= 1 + ((6 - w) % 7) + 7)
        w = pd.Timestamp(year=y[i], month=11, day=1).weekday()
        edt[i] = edt[i] and not (m[i] == 11 and d[i] >= 1 + ((6 - w) % 7))
    return pd.DatetimeIndex(dt + pd.Timedelta(days=1)) + \
        np.where(edt, pd.Timedelta(hours=3), pd.Timedelta(hours=4))


def us_window_returns(us_close: pd.Series, cal, k_max=K_MAX):
    """For each session j (D=cal[j]): compounded US-session return closing inside
    (close(cal[j-1]), 08:45 WIB cal[j]).  Returns dict j -> (y or nan, k)."""
    s = us_close
    ud = pd.DatetimeIndex(s.index)
    out = {}
    for j in range(2, len(cal)):
        d, D = cal[j - 1], cal[j]
        idxs = ud[(ud >= d) & (ud < D)]
        k = len(idxs)
        if k == 0:
            out[j] = (np.nan, 0)
            continue
        if k > k_max:
            out[j] = (np.nan, k)                # B5: excluded upstream
            continue
        pos = s.index.get_indexer(idxs)
        if (pos < 1).any():
            out[j] = (np.nan, k)
            continue
        rets = s.values[pos] / s.values[pos - 1] - 1.0
        out[j] = (float(np.prod(1.0 + rets) - 1.0), k)
    return out


def fx_idr_usd_leg(cal, jk, fx, alt_close=None):
    """Hedge leg r over close(d-1)->close(d), values STAMPED d=cal[s-1],
    d-1=cal[s-2] (B1), FX direction IDR-per-USD (B2):
        (close_d / close_{d-1}) * (fx_{d-1} / fx_d) - 1
    alt_close: optional per-session close array (e.g. corpus TLKM) instead of jk.
    Returns dict s -> x."""
    x = {}
    for s in range(2, len(cal)):
        d, dm = cal[s - 1], cal[s - 2]
        fd, fdm = fx.get(d), fx.get(dm)
        if fd is None or fdm is None or not (fd > 0 and fdm > 0):
            continue
        if alt_close is not None:
            c_d, c_dm = float(alt_close[s - 1]), float(alt_close[s - 2])
        else:
            c_d = jk.get(d) if hasattr(jk, "get") else jk[d]
            c_dm = jk.get(dm) if hasattr(jk, "get") else jk[dm]
        if c_d is None or c_dm is None:
            continue
        if not (np.isfinite(c_d) and np.isfinite(c_dm) and c_d > 0 and c_dm > 0):
            continue
        x[s] = (c_d / c_dm) * (fdm / fd) - 1.0
    return x


def build_signal(y_map, x_map, cal, beta_win=250, beta_min=120,
                 sigma_win=250, sigma_min=120, residualize=True):
    """EIDO/TLK (residualize=True): R_j = y_j - beta_{j-1} * x_j; beta from pairs with
    session <= j-1 (latest available window of exactly 250 points, expanding to a
    minimum of 120); standardized by the trailing sigma of the PIT R series (same
    windows). Uses the LATEST pair strictly before j (no silent drops, minor fix).

    SPY (residualize=False, N2): R_j = y_j raw (the compounded US-window return,
    k <= 3); standardized by the trailing sigma of the y series over sessions
    strictly before j -- NO beta, NO hedge leg (predeclaration: "raw r_SPY
    standardized identically").
    Returns dict j -> {R_std, k} plus exclusion counters."""
    excluded_k = sum(1 for _, (yv, k) in y_map.items() if k > K_MAX)

    if not residualize:
        sig = {}
        R_vals = []
        for p in sorted(y_map):
            yv, k = y_map[p]
            if not np.isfinite(yv) or k == 0 or k > K_MAX:
                continue
            if len(R_vals) >= sigma_min:
                lo = max(0, len(R_vals) - sigma_win)
                sd = float(np.std(R_vals[lo:], ddof=1))
                if sd > 0:
                    sig[p] = {"R_std": yv / sd, "k": k}
            R_vals.append(yv)
        return {"signal": sig, "excluded_k_gt_max": excluded_k}

    pair_sessions = sorted(x_map)
    xs_all = np.array([x_map[p] for p in pair_sessions])
    ys_all = np.array([y_map[p][0] for p in pair_sessions])

    def beta_at(j):
        """beta from the latest window of pairs with session <= j-1."""
        hi = bisect_right(pair_sessions, j - 1)          # pairs strictly before j
        if hi < beta_min:
            return None
        lo = max(0, hi - beta_win)
        xv, yv = xs_all[lo:hi], ys_all[lo:hi]
        m = np.isfinite(xv) & np.isfinite(yv)
        if m.sum() < beta_min or xv[m].std() == 0:
            return None
        return float(np.polyfit(xv[m], yv[m], 1)[0])

    sessions = sorted(set(pair_sessions) & set(y_map))
    R_sessions, R_vals = [], []
    sig = {}
    for p in sessions:
        b = beta_at(p)                                   # beta from pairs <= p-1
        if b is None:
            continue
        r = y_map[p][0] - b * x_map[p]
        if not np.isfinite(r):
            continue
        # sigma from R values with session <= p-1 (strictly before p)
        if len(R_vals) >= sigma_min:
            lo = max(0, len(R_vals) - sigma_win)
            sd = float(np.std(R_vals[lo:], ddof=1))
            if sd > 0:
                sig[p] = {"R_std": r / sd, "k": y_map[p][1]}
        R_sessions.append(p)
        R_vals.append(r)

    out = {}
    for j in sorted(y_map):
        yj, k = y_map[j]
        if k == 0 or k > K_MAX:
            continue
        b = beta_at(j)                                   # pairs <= j-1
        sd = None
        hi = bisect_right(R_sessions, j - 1)             # R values <= j-1
        if hi >= sigma_min:
            lo = max(0, hi - sigma_win)
            sd = float(np.std(R_vals[lo:hi], ddof=1))
        if b is None or not sd or sd <= 0 or j not in x_map:
            continue
        r = yj - b * x_map[j]
        if not np.isfinite(r):
            continue
        out[j] = {"R_std": r / sd, "k": k}
    return {"signal": out, "excluded_k_gt_max": excluded_k}


def nw_t(y, x, lags=5):
    """OLS slope of y on x with Newey-West (Bartlett, lags) standard error."""
    y = np.asarray(y, float); x = np.asarray(x, float)
    m = np.isfinite(y) & np.isfinite(x)
    y, x = y[m] - y[m].mean(), x[m] - x[m].mean()
    n = len(x)
    if n < 10 or x.std() == 0:
        return {"n": int(n), "slope": np.nan, "t": np.nan}
    denom = float((x * x).sum())
    beta = float((x * y).sum() / denom)
    u = y - beta * x
    acc = float((u * x).dot(u * x)) / denom ** 2 * n
    for l in range(1, lags + 1):
        w = 1.0 - l / (lags + 1.0)
        acc += 2.0 * w * float((u[l:] * x[l:]).dot(u[:-l] * x[:-l])) / denom ** 2 * n
    se = float(np.sqrt(max(acc, 0.0) / n))
    return {"n": int(n), "slope": beta, "t": (beta / se) if se > 0 else np.nan}


def load_corpus():
    """Extended panel (issuance=True) -> calendar + matrices (read-only)."""
    import data.db as _ddb
    _orig = _ddb.connect
    def _c(*a, **k):
        c = _orig(*a, **k)
        try:
            c.execute("PRAGMA mmap_size=0")
        except Exception:
            pass
        return c
    _ddb.connect = _c
    import research.rulecard.data as rcdata
    from data.adjustments import read_raw_ohlcv
    from data.db import connect
    with connect(read_only=True) as c:
        ihsg = (read_raw_ohlcv(c).loc[lambda x: x["ticker"] == "IHSG",
                                      ["date", "open", "close"]]
                .assign(date=lambda x: pd.to_datetime(x["date"]))
                .sort_values("date").reset_index(drop=True))
    P = rcdata.load_extended_ohlcv(issuance=True)
    P["date"] = pd.to_datetime(P["date"])
    P = P.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    val = P["close"] * P["volume"]
    tv = val.groupby(P["ticker"], sort=False)
    P["adv20"] = tv.transform(lambda x: x.rolling(20, min_periods=20).mean())
    P["med60"] = tv.transform(lambda x: x.rolling(60, min_periods=60).median())
    P["prev_close"] = P.groupby("ticker", sort=False)["close"].shift(1)
    P["adv20_d"] = P.groupby("ticker", sort=False)["adv20"].shift(1)
    P["med60_d"] = P.groupby("ticker", sort=False)["med60"].shift(1)
    dates = np.sort(P["date"].unique())
    didx = {d: i for i, d in enumerate(dates)}
    tickers = np.sort(P["ticker"].unique())
    tix = {t: i for i, t in enumerate(tickers)}
    cal = pd.DatetimeIndex(dates)

    def mat(col):
        M = np.full((len(dates), len(tickers)), np.nan)
        M[P["date"].map(didx).values, P["ticker"].map(tix).values] = P[col].values
        return M

    return {"cal": cal, "tix": tix, "ihsg": ihsg,
            "O": mat("open"), "C": mat("close"), "H": mat("high"), "L": mat("low"),
            "V": mat("volume"), "A20": mat("adv20_d"), "W60": mat("med60_d"),
            "PC": mat("prev_close")}


def books(CP):
    """Primary (tick-eligible) and co-equal all-rows books; empty days = NaN (B4)."""
    O, C, V, A20, W60 = CP["O"], CP["C"], CP["V"], CP["A20"], CP["W60"]
    liquid = (A20 >= ADV_MIN) & (V > 0) & (O > 0) & (C > 0)
    tickv = np.select([CP["PC"] < 200, CP["PC"] < 500, CP["PC"] < 2000, CP["PC"] < 5000],
                      [1.0, 2.0, 5.0, 10.0], 25.0)
    tick_frac = np.divide(tickv, np.where(CP["PC"] > 0, CP["PC"], np.nan),
                          out=np.full_like(C, np.nan))
    eligible = liquid & (tick_frac <= TICK_MAX)

    def one(keep):
        r = np.where(keep, C / O - 1.0, np.nan)
        Cprev = np.vstack([np.full((1, C.shape[1]), np.nan), C[:-1]])
        g = np.where(keep, O / Cprev - 1.0, np.nan)
        ws = np.nansum(np.where(keep, W60, 0.0), axis=1)
        with np.errstate(divide="ignore", invalid="ignore"):
            w = np.where(keep & (ws[:, None] > 0),
                         np.divide(W60, np.where(ws[:, None] > 0, ws[:, None], 1.0)), 0.0)
        oc = np.nansum(w * r, axis=1)
        gp = np.nansum(w * g, axis=1)
        empty = ~(ws > 0)
        oc[empty] = np.nan                            # B4
        gp[empty] = np.nan
        return (pd.Series(oc, index=CP["cal"]), pd.Series(gp, index=CP["cal"]),
                pd.Series(ws, index=CP["cal"]))

    oc_e, gap_e, wsum_e = one(eligible)
    oc_a, gap_a, wsum_a = one(liquid)
    tl = CP["tix"].get("TLKM")
    Cprev = np.vstack([np.full((1, C.shape[1]), np.nan), C[:-1]])
    oc_tlkm = pd.Series(np.where(eligible[:, tl], CP["C"][:, tl] / CP["O"][:, tl] - 1.0, np.nan),
                        index=CP["cal"])
    gap_tlkm = pd.Series(np.where(eligible[:, tl], CP["O"][:, tl] / Cprev[:, tl] - 1.0, np.nan),
                         index=CP["cal"])                        # N1 (REVIEW_R2bis)
    return {"oc_e": oc_e, "gap_e": gap_e, "wsum_e": wsum_e, "oc_a": oc_a, "gap_a": gap_a,
            "wsum_a": wsum_a, "oc_tlkm": oc_tlkm, "gap_tlkm": gap_tlkm,
            "eligible": eligible, "tick_frac": tick_frac,
            "empty_e": int((wsum_e <= 0).sum()), "empty_a": int((wsum_a <= 0).sum()),
            "tl": tl}


def run_arm(sig_map, oc, sp, cal, k1_only=False):
    lo_s, hi_s = ((SPLIT_DATE, None) if sp == "confirmation" else (None, SPLIT_DATE))
    ys, xs, ds = [], [], []
    for j, v in sig_map.items():
        D = cal[j]
        if (lo_s and D < lo_s) or (hi_s and D >= hi_s) or D > END_FROZEN:
            continue
        if k1_only and v["k"] != 1:
            continue
        o = oc.iloc[j]
        if not np.isfinite(o):
            continue
        ys.append(o); xs.append(v["R_std"]); ds.append(D)
    ys, xs = np.array(ys), np.array(xs)
    prim = nw_t(ys, xs)
    tb = ys[xs <= -CUT]; tt = ys[xs >= CUT]
    n_out_missing = 0
    for j, v in sig_map.items():
        D = cal[j]
        if (lo_s and D < lo_s) or (hi_s and D >= hi_s) or D > END_FROZEN:
            continue
        if k1_only and v["k"] != 1:
            continue
        if not np.isfinite(oc.iloc[j]):
            n_out_missing += 1
    yrs = {}
    for yy in sorted({d.year for d in ds}):
        m = np.array([d.year == yy for d in ds])
        yrs[str(yy)] = {"n": int(m.sum()), "slope": nw_t(ys[m], xs[m])["slope"],
                        "mean_oc_pct": round(100 * float(ys[m].mean()), 3)}
    return {"split": sp, "n": prim["n"],
            "slope_bp_per_1sigma": round(1e4 * prim["slope"], 2) if np.isfinite(prim["slope"]) else None,
            "t": round(prim["t"], 3) if np.isfinite(prim["t"]) else None,
            "tercile_bottom_mean_bp": round(1e4 * tb.mean(), 2) if len(tb) else None,
            "tercile_top_mean_bp": round(1e4 * tt.mean(), 2) if len(tt) else None,
            "n_bottom": int(len(tb)), "n_top": int(len(tt)),
            "empty_outcome_days_dropped": n_out_missing,
            "year_by_year": yrs, "_ys": ys, "_xs": xs}


def check_guard(directory=None, driver_sha=None, pre_sha=None):
    """B3 guard, N3 revision (REVIEW_R2bis): scan ALL lines of ALL REVIEW_R2*.md;
    ignore candidate lines without both 64-hex shas; accept only if some line's
    two shas both equal the files on disk; otherwise refuse, listing every
    candidate line and why it failed. Fail-closed."""
    import re
    directory = Path(directory) if directory else HERE.parent
    driver_sha = driver_sha or DRIVER_SHA
    pre_sha = pre_sha or PRE_SHA
    candidates = []
    for p in sorted(directory.glob("REVIEW_R2*.md")):
        for ln, line in enumerate(p.read_text(errors="ignore").splitlines(), 1):
            if "R2-DECISION: X1 GO" not in line:
                continue
            m = dict(re.findall(r"(driver_sha256|predeclaration_sha256)=([0-9a-f]{64})", line))
            if len(m) != 2:
                candidates.append(f"{p.name}:{ln} missing 64-hex shas :: {line.strip()[:140]}")
                continue
            okd = m.get("driver_sha256") == driver_sha
            okp = m.get("predeclaration_sha256") == pre_sha
            if okd and okp:
                return (f"{p.name}:{ln}", line.strip())
            candidates.append(f"{p.name}:{ln} driver_sha match={okd}, "
                              f"predeclaration_sha match={okp} :: {line.strip()[:140]}")
    reason = "; ".join(candidates) or "no R2-DECISION: X1 GO candidate line in any REVIEW_R2*.md"
    return None, reason


def main():
    ok, msg = check_guard()
    if not ok:
        sys.exit(f"REFUSING TO RUN (B3 guard): {msg}")
    print(f"R2 GO verified: {msg}")
    out = {"predeclaration_sha256": PRE_SHA, "driver_sha256": DRIVER_SHA,
           "bar_frozen": BAR, "params": PARAMS, "go_line": msg}
    with _tracking() as run:
        CP = load_corpus()
        cal = CP["cal"]
        B = books(CP)
        out["empty_book_days"] = {"tick_eligible": B["empty_e"]}          # B4 disclosure
        DATA = HERE / "data"
        fx = pd.read_csv(DATA / "usdidr.csv", parse_dates=["date"]).set_index("date")["close"]
        jk = pd.read_csv(DATA / "jkse.csv", parse_dates=["date"]).set_index("date")["close"]

        tl = B["tl"]
        tlkm_close = CP["C"][:, tl] if tl is not None else None
        legs = {"EIDO": (pd.read_csv(DATA / "eido.csv", parse_dates=["date"])
                         .set_index("date")["close"], None),
                "TLK": (pd.read_csv(DATA / "tlk.csv", parse_dates=["date"])
                        .set_index("date")["close"], tlkm_close),
                "SPY": (pd.read_csv(DATA / "spy.csv", parse_dates=["date"])
                        .set_index("date")["close"], None)}
        sigmaps, excl = {}, {}
        for nm, (us, alt) in legs.items():
            ymap = us_window_returns(us, cal)
            if nm == "SPY":
                built = build_signal(ymap, {}, cal, residualize=False)    # N2: raw r_SPY
            else:
                xmap = fx_idr_usd_leg(cal, jk, fx, alt_close=alt)          # B1/B2
                built = build_signal(ymap, xmap, cal)
            sigmaps[nm] = built["signal"]
            excl[nm] = built["excluded_k_gt_max"]
        out["excluded_k_gt_max_per_signal"] = excl                        # B5 disclosure

        res = {}
        for nm in legs:
            key_c = f"{nm}-C" if nm != "TLK" else "TLK-C_tlkm"
            res[key_c] = run_arm(sigmaps[nm], B["oc_tlkm"] if nm == "TLK" else B["oc_e"],
                                 "confirmation", cal)
            res[f"{nm}-D" if nm != "TLK" else "TLK-D_tlkm"] = run_arm(
                sigmaps[nm], B["oc_tlkm"] if nm == "TLK" else B["oc_e"], "discovery", cal)
            res[f"{nm}-C_allrows"] = run_arm(sigmaps[nm], B["oc_a"], "confirmation", cal)
            res[f"{nm}-D_allrows"] = run_arm(sigmaps[nm], B["oc_a"], "discovery", cal)

        # absorption share + k=1-only sensitivity (primary, confirmation)
        for nm in legs:
            key = f"{nm}-C" if nm != "TLK" else "TLK-C_tlkm"
            gap = B["gap_tlkm"] if nm == "TLK" else B["gap_e"]
            oc = B["oc_tlkm"] if nm == "TLK" else B["oc_e"]
            g = run_arm(sigmaps[nm], gap, "confirmation", cal)
            so, sg = res[key]["slope_bp_per_1sigma"], g["slope_bp_per_1sigma"]
            res[key]["absorption_share"] = (round(sg / (sg + so), 3)
                                            if so is not None and sg is not None and (sg + so) != 0
                                            else None)
            k1 = run_arm(sigmaps[nm], oc, "confirmation", cal, k1_only=True)
            res[key]["k1_only_t"] = k1["t"]

        # ------------------------------------------------------------ economics
        econ = {}
        for nm in legs:
            key = f"{nm}-C" if nm != "TLK" else "TLK-C_tlkm"
            a = res[key]
            ys, xs = a.pop("_ys"), a.pop("_xs")
            tb, tt = ys[xs <= -CUT], ys[xs >= CUT]
            econ[nm] = {
                "overlay_bottom_buy_bp": round(1e4 * -tb.mean(), 2) if len(tb) else None,
                "overlay_top_sell_bp": round(1e4 * tt.mean(), 2) if len(tt) else None,
                "affected_share_bottom": round(len(tb) / len(ys), 3) if len(ys) else None,
                "affected_share_top": round(len(tt) / len(ys), 3) if len(ys) else None,
                "standalone_top_net_060_bp": round(1e4 * tt.mean() - 1e4 * RT_FLOOR, 2) if len(tt) else None,
            }
        for k in res:
            if isinstance(res[k], dict):
                res[k].pop("_ys", None); res[k].pop("_xs", None)

        # D-059 modeled cost (E1-E3) inside ONE guarded block
        try:
            spec = importlib.util.spec_from_file_location(
                "cost_by_adv", ROOT / "docs/research_programs/P-M/cost_liquidity/cost_by_adv.py")
            cb = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cb)
            O, C, H, L, A20 = CP["O"], CP["C"], CP["H"], CP["L"], CP["A20"]
            terms = np.full_like(C, np.nan)
            for i in range(C.shape[1]):
                c_col = C[:, i]; h_col = H[:, i]; l_col = L[:, i]
                m = np.isfinite(c_col) & np.isfinite(h_col) & np.isfinite(l_col)
                if m.sum() < 25:
                    continue
                cc = np.where(m, c_col, np.nan)
                terms[:, i] = cb.ar_terms(cc, np.where(m, h_col, np.nan),
                                          np.where(m, l_col, np.nan))
            # rolling 21-term spread, then shift 2: a day-D cost uses terms ending <= d-1 (E1)
            ar_frac = np.sqrt(np.maximum(
                pd.DataFrame(terms, index=cal).rolling(21, min_periods=10).mean().shift(2).values, 0.0))
            tick_frac = B["tick_frac"]
            s_spread = np.maximum(np.nan_to_num(ar_frac, nan=0.0),
                                  np.nan_to_num(tick_frac, nan=0.0))     # E2: fraction floor
            sig_d = pd.DataFrame(np.log(C), index=cal).diff().rolling(21, min_periods=10).std().values
            impact = 2.0 * sig_d * np.sqrt(Q_POS / np.maximum(A20, 1.0))
            cost_rt = cb.FEES + s_spread + impact                        # round trip, fraction
            ws = np.nansum(np.where(B["eligible"], CP["W60"], 0.0), axis=1)
            with np.errstate(divide="ignore", invalid="ignore"):
                w = np.where(B["eligible"] & (ws[:, None] > 0),
                             np.divide(CP["W60"], np.where(ws[:, None] > 0, ws[:, None], 1.0)), 0.0)
            cost_book = np.nansum(w * np.where(B["eligible"], cost_rt, np.nan), axis=1)
            for nm in ("EIDO", "SPY"):
                tt_days = [j for j, v in sigmaps[nm].items()
                           if v["R_std"] >= CUT and SPLIT_DATE <= cal[j] <= END_FROZEN
                           and np.isfinite(B["oc_e"].iloc[j])]
                tt = np.array([B["oc_e"].iloc[j] for j in tt_days])
                mc = float(np.mean([cost_book[j] for j in tt_days])) if tt_days else np.nan
                econ[nm]["standalone_top_net_D059_bp"] = (
                    round(1e4 * tt.mean() - 1e4 * mc, 2) if len(tt) else None)
                econ[nm]["D059_book_cost_bp"] = round(1e4 * mc, 2) if np.isfinite(mc) else None
            if tl is not None:                                           # E3: inside try
                tt_days = [j for j, v in sigmaps["TLK"].items()
                           if v["R_std"] >= CUT and SPLIT_DATE <= cal[j] <= END_FROZEN
                           and np.isfinite(B["oc_tlkm"].iloc[j])]
                tt = np.array([B["oc_tlkm"].iloc[j] for j in tt_days])
                mc = float(np.nanmean([cost_rt[j, tl] for j in tt_days]))
                econ["TLK"]["standalone_top_net_D059_bp"] = round(1e4 * tt.mean() - 1e4 * mc, 2)
                econ["TLK"]["D059_cost_bp"] = round(1e4 * mc, 2)
        except Exception as e:  # noqa: BLE001
            econ["D059_error"] = f"{type(e).__name__}: {e}"[:200]
        out["economics"] = econ

        # E4 disclosure: boundary sensitivity of the tick-eligibility cut
        el = B["eligible"]
        disc = np.isfinite(B["tick_frac"]) & (B["tick_frac"] > 0.004) & (B["tick_frac"] < 0.0065)
        near = np.isfinite(B["tick_frac"]) & (B["tick_frac"] > 0.004) & (B["tick_frac"] < 0.0065) & el
        out["tick_schedule_disclosure"] = {
            "assumed": "current IDX schedule (<200:1; 200-500:2; 500-2000:5; 2000-5000:10; >=5000:25) applied to ALL dates; historical schedules not verifiable from this host (idx.co.id blocked)",
            "discovery_liquid_name_days_near_boundary_0.004_0.0065": int(
                sum(int(near[j].sum()) for j in range(len(cal)) if cal[j] < SPLIT_DATE)),
            "confirmation_liquid_name_days_near_boundary_0.004_0.0065": int(
                sum(int(near[j].sum()) for j in range(len(cal)) if cal[j] >= SPLIT_DATE)),
        }

        # E5: recorder correlation with explicit schema check
        corr = {}
        for name, p in (("FADE-001", ROOT / "docs/research_programs/P-M/forward_fade/ledger.json"),
                        ("REGIME-002", ROOT / "docs/research_programs/P-M/forward_regime/ledger.json"),
                        ("VOLEX-001", ROOT / "docs/research_programs/P-M/forward_exclusion/ledger.json")):
            try:
                data = json.loads(Path(p).read_text())
                tr = data.get("trades")
                if not isinstance(tr, list) or not all("entry_date" in t for t in tr):
                    corr[name] = {"error": "ledger trades[] missing entry_date key"}
                    continue
                cnt = pd.Series([str(t["entry_date"]) for t in tr]).value_counts()
                pairs = [(sigmaps["EIDO"][j]["R_std"], float(cnt.get(str(cal[j].date()), 0.0)))
                         for j in sigmaps["EIDO"] if str(cal[j].date()) in set(cnt.index)]
                corr[name] = ({"n_days": len(pairs),
                               "corr": round(float(np.corrcoef([a_ for a_, _ in pairs],
                                                              [b_ for _, b_ in pairs])[0, 1]), 3)}
                              if len(pairs) > 10 else
                              {"n_days": len(pairs), "error": "insufficient overlap"})
            except Exception as e:  # noqa: BLE001
                corr[name] = {"error": f"{type(e).__name__}: {e}"[:120]}
        out["recorder_corr"] = corr
        out["arms"] = res
        out["ihsg_oc_confirmation_sigma_pct"] = round(
            100 * float(CP["ihsg"].assign(oc=lambda x: x["close"] / x["open"] - 1.0)
                        .set_index("date")["oc"][lambda s: s.index >= SPLIT_DATE].std()), 3)

        run.metrics = {"arms_n": {k: v.get("n") for k, v in res.items() if isinstance(v, dict)}}
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        (HERE / f"RESULT_X1_{stamp}.json").write_text(json.dumps(out, indent=1, default=str))
        print("WROTE", HERE / f"RESULT_X1_{stamp}.json")
        for k in ("EIDO-C", "TLK-C_tlkm", "SPY-C"):
            a = res[k]
            print(k, "n", a["n"], "slope", a["slope_bp_per_1sigma"], "t", a["t"],
                  "absorb", a.get("absorption_share"))


def _tracking():
    from research.tracking import track_run
    return track_run(kind="x1_screen", params=PARAMS)


if __name__ == "__main__":
    main()
