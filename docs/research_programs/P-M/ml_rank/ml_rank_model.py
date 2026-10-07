"""HYP-PM-0015 (DRAFT) — price-learning cross-sectional ranking model. Driver.

G0 STATE (2026-10-06): machinery only. Nothing in this module fits a model on
returns unless run_g1() is invoked, and run_g1() refuses to run unless the
environment carries ML_RANK_G1_APPROVED=1 (set by the owner/planner after the
G0 freeze is approved). The PIT tests (test_pit_ml_rank.py) exercise every
causality claim below on synthetic panels; pit_check_real.py re-runs the
feature/universe/embargo checks on the real corpus reading no outcomes.

Everything numeric here is predeclared in PREDECLARATION.md (sha256-frozen at
G0). Constants marked FROZEN must not be edited after the freeze — a change is
a new, disclosed, re-frozen run (brief: any post-G1 fix counts as a new trial).

Research-side only: imports numpy/pandas/sklearn + research.rulecard.data +
research.statistics + research.tracking + the data layer's read-only connect.
No execution imports, no production writes; the only DB access is read-only.
"""
from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.rulecard.data import load_extended_ohlcv  # noqa: E402
from research.statistics import (  # noqa: E402
    deflated_sharpe_ratio, pbo_cscv, sharpe as _sharpe)
from research.tracking import dataset_fingerprint, git_commit, track_run  # noqa: E402
from data.db import connect as db_connect  # noqa: E402

# ── FROZEN predeclaration constants (PREDECLARATION.md §3–§9) ────────────────
SEED = 20261006
COST_RT = 0.006                 # 0.60% round trip × one-sided monthly turnover
ADV60_TOP = 150
ADV60_MIN_PERIODS = 40          # pattern-study parity
CLOSE_FLOOR = 50.0              # adjusted-panel close (pattern-study parity)
PRESENT_MIN = 18                # of last 20 sessions
QUINTILE = 5
TRAIN_FIRST_MONTH = "2001-01"   # first training label month
VAL_MONTHS = ("2016-01", "2021-09")
DEFLECTION_BAR = 3.06           # exact E[max|Z|] @ N=266 = 3.0558; brief/D-064 bar applied
CENSUS_N = 266
BEATS_M0_T = 2.0
PBO_MAX = 0.5
NW_LAG = 3
PBO_SPLITS = 16

FEATURES = (
    "ret5", "ret21", "ret63", "ret126", "mom12_1", "park60", "rv20", "maxret21",
    "dist52w", "log_adv20", "adv_ratio", "beta252", "idio_vol", "atr14_ratio",
)

# FROZEN grid: ≤ 6 configurations across M1 and M2
MODEL_GRID = (
    ("m1_ridge_a0.1",  "m1", {"alpha": 0.1}),
    ("m1_ridge_a1.0",  "m1", {"alpha": 1.0}),
    ("m1_ridge_a10.0", "m1", {"alpha": 10.0}),
    ("m2_hgbr_d2_lr0.05_i200", "m2", {"max_depth": 2, "learning_rate": 0.05, "max_iter": 200}),
    ("m2_hgbr_d3_lr0.05_i200", "m2", {"max_depth": 3, "learning_rate": 0.05, "max_iter": 200}),
    ("m2_hgbr_d3_lr0.10_i100", "m2", {"max_depth": 3, "learning_rate": 0.10, "max_iter": 100}),
)

# Env overrides so the driver can run from a code-only worktree while the data
# artifacts live in the main tree (both gitignored); defaults match the repo.
HIST_PKL = os.getenv("ML_RANK_HIST_PKL")
SPLITS_PKL = os.getenv("ML_RANK_SPLITS_PKL")


# ── Panel ─────────────────────────────────────────────────────────────────────

def load_panel(hist=None, splits=None):
    """The frozen dataset: load_extended_ohlcv(issuance=True) + IHSG (read-only).

    Returns (pivots dict of date×ticker DataFrames, ihsg DataFrame indexed by
    date with open/close columns). The loader's vendor-error cleaning (centered
    glitch median, backfill-only) and gap-verified split/issuance adjustments
    run once at dataset-build time — outside the per-rebalance decision path
    (PREDECLARATION.md §4)."""
    kw = {}
    if hist or HIST_PKL:
        kw["hist"] = hist or HIST_PKL
    if splits or SPLITS_PKL:
        kw["splits"] = splits or SPLITS_PKL
    X = load_extended_ohlcv(issuance=True, **kw)
    P = {k: X.pivot(index="date", columns="ticker", values=k).sort_index()
         for k in ("open", "high", "low", "close", "volume")}
    with db_connect(read_only=True) as c:
        ihsg = pd.read_sql("SELECT date, open, close FROM ohlcv WHERE ticker='IHSG' "
                           "ORDER BY date", c)
    ihsg["date"] = pd.to_datetime(ihsg["date"])
    ihsg = ihsg.set_index("date").sort_index()
    return P, ihsg


def ihsg_month_returns(ihsg, schedule) -> dict:
    """IHSG open-to-open returns over the books' own entry/exit dates.
    Requires an IHSG bar ON each date (no asof substitution — a missing bar
    excludes the month from the IHSG comparison, counted)."""
    out = {}
    opens = ihsg["open"]
    for rec in schedule:
        try:
            o_in = opens.loc[rec["entry_date"]]
            o_out = opens.loc[rec["exit_date"]]
        except KeyError:
            continue
        if np.isfinite(o_in) and np.isfinite(o_out) and o_in > 0:
            out[rec["month"]] = float(o_out) / float(o_in) - 1.0
    return out


# ── Features (all causal: every window ends at its own row) ──────────────────

def daily_returns(C: pd.DataFrame) -> pd.DataFrame:
    return C / C.shift(1) - 1.0


def market_daily_returns(C: pd.DataFrame) -> pd.Series:
    """Equal-weight mean daily simple return over ALL panel names with a finite
    return that session — the market proxy for beta252/idio_vol (deviation D-1:
    the corpus has no pre-2021-07 IHSG; PREDECLARATION.md §5)."""
    return daily_returns(C).mean(axis=1)


def true_range(H, L, C):
    tr = np.maximum.reduce([(H - L).abs().values,
                            (H - C.shift(1)).abs().values,
                            (L - C.shift(1)).abs().values])
    return pd.DataFrame(tr, index=C.index, columns=C.columns)


def beta_idio(r: pd.DataFrame, r_m: pd.Series, n: int = 252):
    """252-session rolling beta to r_m and idio vol = sqrt(max(var(r) − β²·var(r_m), 0)),
    via rolling moment sums (bit-stable under truncation, no deprecated APIs)."""
    rm = r_m.reindex(r.index)
    k = float(n)
    s_x = r.rolling(n, min_periods=n).sum()
    s_y = rm.rolling(n, min_periods=n).sum()
    s_xy = r.mul(rm, axis=0).rolling(n, min_periods=n).sum()
    s_x2 = (r * r).rolling(n, min_periods=n).sum()
    s_y2 = (rm * rm).rolling(n, min_periods=n).sum()
    cov = (s_xy - s_x.mul(s_y, axis=0) / k) / (k - 1.0)
    varx = (s_x2 - s_x * s_x / k) / (k - 1.0)
    vary = (s_y2 - s_y * s_y / k) / (k - 1.0)
    beta = cov.div(vary.where(vary > 0), axis=0)
    idio = np.sqrt((varx - beta.mul(beta, axis=0).mul(vary, axis=0)).clip(lower=0.0))
    return beta, idio


def compute_features(P: dict) -> dict:
    """The 14 predeclared features as date×ticker frames. Every rolling window
    is backward-looking with min_periods = full window; NaN until it exists."""
    H, L, C, V = P["high"], P["low"], P["close"], P["volume"]
    r = daily_returns(C)
    r_m = market_daily_returns(C)
    logret = np.log(C / C.shift(1))
    turnover = C * V
    beta, idio = beta_idio(r, r_m)
    F = {
        "ret5":      C / C.shift(5) - 1.0,
        "ret21":     C / C.shift(21) - 1.0,
        "ret63":     C / C.shift(63) - 1.0,
        "ret126":    C / C.shift(126) - 1.0,
        "mom12_1":   C.shift(21) / C.shift(252) - 1.0,
        "park60":    np.sqrt((np.log(H / L) ** 2).rolling(60, min_periods=60).mean()
                             / (4.0 * math.log(2.0))),
        "rv20":      logret.rolling(20, min_periods=20).std(ddof=1),
        "maxret21":  r.rolling(21, min_periods=21).max(),
        "dist52w":   C / C.rolling(252, min_periods=252).max() - 1.0,
        "log_adv20": np.log(turnover.rolling(20, min_periods=20).mean()),
        "adv_ratio": (turnover.rolling(20, min_periods=20).mean()
                      / turnover.rolling(120, min_periods=120).mean()),
        "beta252":   beta,
        "idio_vol":  idio,
        "atr14_ratio": true_range(H, L, C).rolling(14, min_periods=14).mean() / C,
    }
    return F


# ── Universe (pattern-study parity, evaluated at the prior session) ──────────

def eligibility_mask(C: pd.DataFrame, V: pd.DataFrame) -> pd.DataFrame:
    """Top-150 by 60-session mean turnover (C*V, min_periods=40), close ≥ 50
    (adjusted panel, pattern-study parity), present ≥ 18 of 20 sessions."""
    present = C.notna().astype(float).rolling(20, min_periods=20).sum()
    to60 = (C * V).rolling(60, min_periods=ADV60_MIN_PERIODS).mean()
    to60_rank = to60.rank(axis=1, ascending=False, na_option="keep")
    return (to60_rank <= ADV60_TOP) & (C >= CLOSE_FLOOR) & (present >= PRESENT_MIN)


# ── Schedule ──────────────────────────────────────────────────────────────────

def month_key(ts) -> str:
    return f"{ts.year:04d}-{ts.month:02d}"


def month_key_next(m: str) -> str:
    y, mo = int(m[:4]), int(m[5:7])
    return f"{y + (mo == 12):04d}-{(mo % 12) + 1:02d}"


def build_schedule(P: dict) -> list[dict]:
    """One record per prediction month. entry = first panel session of the
    month; t = the prior panel row (feature cutoff — features use data through
    the prior session's close only); exit = first panel session of the next
    month. Months without a successor are not prediction months."""
    idx = P["close"].index
    firsts = {}
    for i, ts in enumerate(idx):
        firsts.setdefault(month_key(ts), i)
    months = sorted(firsts)
    out = []
    for j, m in enumerate(months[:-1]):
        e = firsts[m]
        if e == 0:
            continue  # the panel's first month has no prior session; iloc[-1]
                      # would silently wrap to the last row — never emit it
        out.append({"month": m, "entry": e, "t": e - 1, "exit": firsts[months[j + 1]],
                    "entry_date": idx[e], "exit_date": idx[firsts[months[j + 1]]],
                    "year": int(m[:4])})
    return out


def refit_split(schedule: list[dict], year: int) -> tuple[list[str], list[str]]:
    """(train_label_months, prediction_months) for the yearly refit of `year`.

    Embargo (predeclared): a training label month m's return window ends at the
    first session of month m+1, and the refit is computed before the year's
    first prediction month — so m+1 must fall strictly before it. December's
    return is never a training label; no label window overlaps a prediction
    month."""
    pred = [r["month"] for r in schedule if r["year"] == year]
    if not pred:
        return [], []
    first_pred = min(pred)
    train = [r["month"] for r in schedule
             if TRAIN_FIRST_MONTH <= r["month"] < first_pred
             and month_key_next(r["month"]) < first_pred]
    return train, pred


# ── Monthly tables ────────────────────────────────────────────────────────────

def monthly_returns(P: dict, schedule: list[dict]) -> pd.DataFrame:
    """Open-to-open monthly returns with the predeclared exit fallback:
    suspended-at-exit names exit at their last finite close on/before the exit
    session; names with no bar at all after entry book a −100% month (audit
    counts in attrs). NaN = could not enter (no positive open at entry)."""
    O, C = P["open"], P["close"]
    ffC = C.ffill()
    cum = C.notna().cumsum()
    rows, audits = [], {"fallback_exit": 0, "full_loss": 0, "no_entry": 0}
    for rec in schedule:
        e, x = rec["entry"], rec["exit"]
        o_in, o_out, f_out = O.iloc[e], O.iloc[x], ffC.iloc[x]
        base = o_in.notna() & (o_in > 0)
        naive = (o_out / o_in - 1.0)
        traded_after = (cum.iloc[x] - cum.iloc[e]) > 0
        fb = (f_out / o_in - 1.0).where(traded_after)
        ret = pd.Series(
            np.where(naive.notna(), naive,
                     np.where(fb.notna(), fb, -1.0)),
            index=o_in.index)
        ret = ret.where(base)
        audits["fallback_exit"] += int((base & naive.isna() & fb.notna()).sum())
        audits["full_loss"] += int((base & naive.isna() & fb.isna()).sum())
        audits["no_entry"] += int((~base & elig_any(rec, C)).sum())
        rows.append(pd.DataFrame({"ret": ret, "organic": naive.notna() & base}))
    out = pd.concat(rows, axis=1, keys=[r["month"] for r in schedule])
    out.attrs["audit"] = audits
    return out


def elig_any(rec, C):
    """Defensive helper: names present at the cutoff row (used only for the
    no-entry audit count)."""
    return C.iloc[rec["t"]].notna()


def month_cross_section(rec, F, elig, ret_m, fcomplete):
    """Feature ranks + label rank for one prediction month, on the feature-
    complete eligible set. Returns None when the set is degenerate."""
    t = rec["t"]
    mask = elig.iloc[t] & fcomplete.iloc[t]
    names = mask.index[mask.values]
    if len(names) < QUINTILE:
        return None
    X = pd.DataFrame({f: F[f].iloc[t].loc[names].rank(pct=True, na_option="keep")
                      for f in FEATURES})
    r = ret_m[rec["month"]]["ret"].loc[names]
    org = ret_m[rec["month"]]["organic"].loc[names]
    lab = r.where(org).rank(pct=True, na_option="keep")
    return {"names": names, "X": X, "label": lab, "ret": r, "organic": org,
            "entry_date": rec["entry_date"], "exit_date": rec["exit_date"]}


def rank_ic(pred: pd.Series, realized: pd.Series) -> float:
    """Spearman rank IC by hand (average ties): Pearson of the two average-rank
    vectors over the finite overlap. Deterministic, no scipy."""
    df = pd.concat([pred, realized], axis=1, join="inner").dropna()
    if len(df) < 3:
        return float("nan")
    a = df.iloc[:, 0].rank(pct=True).values
    b = df.iloc[:, 1].rank(pct=True).values
    a = a - a.mean()
    b = b - b.mean()
    den = math.sqrt(float((a * a).sum()) * float((b * b).sum()))
    return float((a * b).sum() / den) if den > 0 else float("nan")


# ── Models ────────────────────────────────────────────────────────────────────

def make_model(family: str, params: dict):
    if family == "m1":
        from sklearn.linear_model import Ridge
        return Ridge(alpha=params["alpha"], fit_intercept=True)
    from sklearn.ensemble import HistGradientBoostingRegressor
    return HistGradientBoostingRegressor(
        max_depth=params["max_depth"], learning_rate=params["learning_rate"],
        max_iter=params["max_iter"], early_stopping=False, random_state=SEED)


def m0_scores(cs) -> pd.Series:
    """FROZEN M0 baseline: equal-weight average of (1 − rank(park60)) and
    rank(mom12_1) — long low Parkinson-60 volatility, long 12-1 momentum."""
    return 0.5 * (1.0 - cs["X"]["park60"]) + 0.5 * cs["X"]["mom12_1"]


def run_walkforward(F, elig, ret_m, schedule, grid=MODEL_GRID):
    """Yearly refits on the expanding window; frozen grid. Returns
    (cs_by_month, scores) with scores[name][month] = Series of predicted scores
    over that month's feature-complete eligible set."""
    fc = None
    for f in FEATURES:
        m = F[f].notna()
        fc = m if fc is None else (fc & m)
    cs_by_month = {}
    for rec in schedule:
        cs = month_cross_section(rec, F, elig, ret_m, fc)
        if cs is not None:
            cs_by_month[rec["month"]] = cs
    scores = {name: {} for name, _, _ in grid}
    for year in sorted({r["year"] for r in schedule}):
        train_months, pred_months = refit_split(schedule, year)
        train_months = [m for m in train_months if m in cs_by_month
                        and cs_by_month[m]["label"].notna().sum() >= QUINTILE]
        if not train_months:
            continue
        Xtr = pd.concat([cs_by_month[m]["X"] for m in train_months])
        ytr = pd.concat([cs_by_month[m]["label"] for m in train_months])
        keep = ytr.notna()
        Xtr, ytr = Xtr[keep], ytr[keep]
        for name, family, params in grid:
            model = make_model(family, params)
            model.fit(Xtr.values, ytr.values)
            for m in pred_months:
                if m in cs_by_month:
                    scores[name][m] = pd.Series(
                        model.predict(cs_by_month[m]["X"].values),
                        index=cs_by_month[m]["X"].index)
    return cs_by_month, scores


# ── Portfolio accounting ──────────────────────────────────────────────────────

def month_book(scored: pd.Series, ret: pd.Series, entry_open: pd.Series,
               prev_w: pd.Series) -> dict:
    """Top-quintile book from scores among can-enter names + turnover + cost.

    k = max(1, floor(n_fc / 5)) where n_fc = len(scored) (the feature-complete
    eligible set); members skip names that cannot enter (no positive open at
    entry) until k is filled. Cost = 0.60% RT × one-sided turnover
    τ = 0.5·Σ|w_new − w_old|; the first month carries τ = 1 (0.60%, a disclosed
    slight overcharge vs buy-only)."""
    can = entry_open.index[entry_open.notna() & (entry_open.values > 0)]
    s = scored.reindex(can).dropna().sort_values(ascending=False, kind="mergesort")
    k = max(1, int(math.floor(len(scored) / QUINTILE)))
    members = list(s.index[:k])
    w = pd.Series(0.0, index=entry_open.index)
    if members:
        w.loc[members] = 1.0 / len(members)
    tau = 0.5 * float((w - prev_w.reindex(w.index).fillna(0.0)).abs().sum())
    gross = float(w.mul(ret.reindex(w.index)).sum())
    return {"members": members, "k": k, "turnover": tau,
            "gross": gross, "net": gross - COST_RT * tau}


def base_book(ret: pd.Series, entry_open: pd.Series, elig_row: pd.Series) -> dict:
    """The benchmark: every universe-eligible name that can enter, equal weight,
    GROSS of costs (conservative for the excess gate; the net variant is
    reported as observability)."""
    can = elig_row.index[elig_row.values & entry_open.notna().values
                         & (entry_open.values > 0)]
    r = ret.loc[can].dropna()
    gross = float(r.mean()) if len(r) else float("nan")
    tau = 1.0 if not can.empty else 0.0  # monthly EW rebalance of the full set
    return {"n": int(len(r)), "gross": gross, "net": gross - COST_RT * tau,
            "members": list(can)}


# ── Statistics ────────────────────────────────────────────────────────────────

def newey_west_t(x, lag: int = NW_LAG) -> float:
    """Newey–West t of the mean, Bartlett weights, lag `lag` (statsmodels is
    not installed; predeclared hand implementation, biased autocovariances)."""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = x.size
    if n < 2:
        return float("nan")
    d = x - x.mean()
    s = float(d @ d) / n
    for l in range(1, lag + 1):
        s += 2.0 * (1.0 - l / (lag + 1.0)) * (float(d[l:] @ d[:-l]) / n)
    return float(x.mean() / math.sqrt(max(s, 1e-300) / n))


def one_sided_t(x) -> float:
    """One-sided t of the mean > 0 (normal approximation, repo convention)."""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if x.size < 2:
        return float("nan")
    se = x.std(ddof=1) / math.sqrt(x.size)
    if se == 0:
        return float("inf") if x.mean() > 0 else float("-inf")
    return float(x.mean() / se)


def leave_one_year_out(months, values) -> dict:
    rows = [(m, v) for m, v in zip(months, values) if np.isfinite(v)]
    years = sorted({m[:4] for m, _ in rows})
    return {y: float(np.mean([v for m, v in rows if m[:4] != y])) for y in years}


def worst_months(months, values, n=12) -> list:
    rows = sorted([(m, v) for m, v in zip(months, values) if np.isfinite(v)],
                  key=lambda p: p[1])
    return rows[:n]


# ── Evaluation (report + verdict, PREDECLARATION.md §8–§9) ───────────────────

def evaluate(P, ihsg, elig, ret_m, schedule, cs_by_month, scores,
             fingerprint: dict | None = None) -> dict:
    val_lo, val_hi = VAL_MONTHS
    months = [r["month"] for r in schedule if r["month"] in cs_by_month]
    val_months = [m for m in months if val_lo <= m <= val_hi]
    test_months = [m for m in months if m > val_hi]

    # config selection: validation mean monthly rank IC (tie → earlier grid slot)
    def mean_ic(name, ms):
        v = [rank_ic(scores[name][m], cs_by_month[m]["ret"])
             for m in ms if m in scores[name]]
        return float(np.nanmean(v)) if v else float("nan")

    ics_val = {name: {m: rank_ic(scores[name][m], cs_by_month[m]["ret"])
                      for m in val_months if m in scores[name]}
               for name, _, _ in MODEL_GRID}
    chosen = {}
    for fam in ("m1", "m2"):
        fams = [n for n, f, _ in MODEL_GRID if f == fam]
        chosen[fam] = max(fams, key=lambda n: (mean_ic(n, val_months),
                                               -fams.index(n)))

    ihsg_ret = ihsg_month_returns(ihsg, schedule)

    # monthly books for M0 + the two chosen configs + the base book
    series = {k: {"net_excess": {}, "turnover": {}, "ic": {}, "gross": {},
                  "k": {}, "n_members": {}}
              for k in ["m0", "m1", "m2"]}
    base = {"gross": {}, "net": {}, "n": {}}
    prev_w = {k: pd.Series(dtype=float) for k in series}
    for rec in schedule:
        m = rec["month"]
        if m not in cs_by_month or m not in val_months + test_months:
            continue
        cs = cs_by_month[m]
        entry_open = P["open"].iloc[rec["entry"]]
        bb = base_book(ret_m[m]["ret"], entry_open, elig.iloc[rec["t"]])
        base["gross"][m], base["net"][m], base["n"][m] = bb["gross"], bb["net"], bb["n"]
        books = {"m0": m0_scores(cs)}
        for fam in ("m1", "m2"):
            if m in scores[chosen[fam]]:
                books[fam] = scores[chosen[fam]][m]
        for key, sc in books.items():
            bk = month_book(sc, ret_m[m]["ret"], entry_open, prev_w[key])
            prev_w[key] = pd.Series(1.0 / max(len(bk["members"]), 1),
                                    index=bk["members"])
            series[key]["net_excess"][m] = bk["net"] - bb["gross"]
            series[key]["turnover"][m] = bk["turnover"]
            series[key]["gross"][m] = bk["gross"]
            series[key]["k"][m] = bk["k"]
            series[key]["n_members"][m] = len(bk["members"])
            series[key]["ic"][m] = (rank_ic(sc, cs["ret"])
                                    if key != "m0" else rank_ic(m0_scores(cs), cs["ret"]))

    def block(key, ms):
        ne = [series[key]["net_excess"].get(m, np.nan) for m in ms]
        ic = [series[key]["ic"].get(m, np.nan) for m in ms]
        to = [series[key]["turnover"].get(m, np.nan) for m in ms]
        ic_arr = np.asarray(ic, float)
        return {
            "mean_rank_ic": float(np.nanmean(ic_arr)) if np.isfinite(ic_arr).any() else None,
            "rank_ic_t": one_sided_t(ic_arr),
            "mean_net_excess": float(np.nanmean(ne)) if np.isfinite(ne).any() else None,
            "nw_t": newey_west_t(ne),
            "hit_rate": float(np.mean([v > 0 for v in ne if np.isfinite(v)]))
            if any(np.isfinite(v) for v in ne) else None,
            "mean_turnover": float(np.nanmean(to)) if np.isfinite(to).any() else None,
            "worst_12": worst_months(ms, ne),
            "by_year": {y: float(np.nanmean([v for m, v in zip(ms, ne) if m[:4] == y
                                              and np.isfinite(v)]))
                        for y in sorted({m[:4] for m in ms})},
        }

    stats = {k: {"validation": block(k, val_months), "test": block(k, test_months)}
             for k in series}

    # PBO over the full grid's monthly validation NET returns (T × 6); the same
    # sequential books feed each configuration's own validation Sharpe for DSR
    grid_names = [n for n, _, _ in MODEL_GRID]
    pbo_matrix_rows = [m for m in val_months
                       if all(m in scores[n] for n in grid_names)]
    grid_net = {n: {} for n in grid_names}
    grid_prev_w = {n: pd.Series(dtype=float) for n in grid_names}
    for rec in schedule:
        m = rec["month"]
        if m not in pbo_matrix_rows:
            continue
        entry_open = P["open"].iloc[rec["entry"]]
        for n in grid_names:
            bk = month_book(scores[n][m], ret_m[m]["ret"], entry_open,
                            grid_prev_w[n])
            grid_prev_w[n] = pd.Series(1.0 / max(len(bk["members"]), 1),
                                       index=bk["members"])
            grid_net[n][m] = bk["net"]
    pbo = None
    if len(pbo_matrix_rows) >= PBO_SPLITS * 2:
        mat = np.array([[grid_net[n][m] for n in grid_names]
                        for m in pbo_matrix_rows])
        pbo = pbo_cscv(mat, n_splits=PBO_SPLITS)

    # DSR on test net excess of the chosen models; sr_trials_std = cross-config
    # std of each grid configuration's own validation Sharpe (monthly net)
    grid_val_net = {n: _sharpe([grid_net[n].get(m, np.nan) for m in pbo_matrix_rows])
                    for n in grid_names}
    sr_std = float(np.std([v for v in grid_val_net.values() if np.isfinite(v)], ddof=1))
    dsr = {}
    for fam in ("m1", "m2"):
        ne = [series[fam]["net_excess"].get(m, np.nan) for m in test_months]
        dsr[fam] = deflated_sharpe_ratio(ne, n_trials=CENSUS_N,
                                         sr_trials_std=max(sr_std, 1e-12))

    # paired comparison vs M0 + leave-one-year-out + IHSG (reported, not gating)
    paired = {}
    for fam in ("m1", "m2"):
        d = [series[fam]["net_excess"].get(m, np.nan) - series["m0"]["net_excess"].get(m, np.nan)
             for m in test_months]
        paired[fam] = {"mean_diff": float(np.nanmean(d)) if np.isfinite(d).any() else None,
                       "t": one_sided_t(d)}
    loyo = {k: leave_one_year_out(test_months,
                                  [series[k]["net_excess"].get(m, np.nan)
                                   for m in test_months])
            for k in series}
    vs_ihsg = {}
    for k in series:
        d = [series[k]["net_excess"].get(m, np.nan) + base["gross"].get(m, np.nan)
             - ihsg_ret.get(m, np.nan) for m in test_months if m in ihsg_ret]
        vs_ihsg[k] = {"n_months": len(d), "mean": float(np.nanmean(d)) if d else None}

    # verdicts (PREDECLARATION.md §9)
    verdict = {}
    for key in ("m0", "m1", "m2"):
        st = stats[key]["test"]
        cond1 = (st["mean_net_excess"] is not None and st["mean_net_excess"] > 0
                 and np.isfinite(st["nw_t"]) and st["nw_t"] >= DEFLECTION_BAR)
        cond4 = all(v > 0 for v in loyo[key].values()) if loyo[key] else False
        v = {"1_net_excess_nw_t": bool(cond1), "4_loyo_positive": bool(cond4),
             "loyo_min": min(loyo[key].values()) if loyo[key] else None}
        if key != "m0":
            v["2_beats_m0_t>=2"] = bool(paired[key]["t"] is not None
                                        and np.isfinite(paired[key]["t"])
                                        and paired[key]["t"] >= BEATS_M0_T)
            v["3_pbo<0.5"] = bool(pbo is not None and pbo["pbo"] < PBO_MAX)
            v["pass"] = all(v[c] for c in ("1_net_excess_nw_t", "2_beats_m0_t>=2",
                                           "3_pbo<0.5", "4_loyo_positive"))
        else:
            v["pass"] = bool(cond1 and cond4)
        verdict[key] = v

    last_month = test_months[-1] if test_months else None
    top30 = {}
    if last_month is not None:
        cs = cs_by_month[last_month]
        rec = next(r for r in schedule if r["month"] == last_month)
        entry_open = P["open"].iloc[rec["entry"]]
        for key, sc in [("m0", m0_scores(cs))] + \
                       [(f, scores[chosen[f]][last_month]) for f in ("m1", "m2")
                        if last_month in scores[chosen[f]]]:
            can = entry_open.index[entry_open.notna() & (entry_open.values > 0)]
            s = sc.reindex(can).dropna().sort_values(ascending=False, kind="mergesort")
            top30[key] = [str(x) for x in s.index[:30]]

    return {
        "hypothesis": "HYP-PM-0015 (draft)", "seed": SEED,
        "deflation_bar": DEFLECTION_BAR, "census_n": CENSUS_N,
        "chosen": chosen, "ics_val_grid": {n: mean_ic(n, val_months)
                                           for n, _, _ in MODEL_GRID},
        "months_val": val_months, "months_test": test_months,
        "stats": stats, "pbo": pbo, "dsr": dsr, "paired_vs_m0": paired,
        "loyo": loyo, "vs_ihsg": vs_ihsg, "verdict": verdict,
        "top30_last_month": top30, "last_month": last_month,
        "base_n_min": min(base["n"].values()) if base["n"] else None,
        "audit_monthly_returns": ret_m.attrs.get("audit"),
        "dataset_fingerprint": fingerprint,
        "sklearn_grid_val_sharpe": grid_val_net, "sr_trials_std": sr_std,
    }


# ── G1 entrypoint (gated) ─────────────────────────────────────────────────────

def run_g1(hist=None, splits=None) -> dict:
    """THE single run. Refuses without ML_RANK_G1_APPROVED=1; records the run in
    research_runs via research.tracking (append-only) and writes
    RESULT_<utc>.json next to this file. One run, one RESULT, one VERDICT."""
    if os.environ.get("ML_RANK_G1_APPROVED") != "1":
        raise SystemExit("G1 is gated: set ML_RANK_G1_APPROVED=1 only after the "
                         "owner/planner approves the frozen G0 (PREDECLARATION.sha256).")
    params = {
        "features": list(FEATURES), "grid": [n for n, _, _ in MODEL_GRID],
        "seed": SEED, "cost_rt": COST_RT, "adv60_top": ADV60_TOP,
        "close_floor": CLOSE_FLOOR, "present_min": PRESENT_MIN,
        "val": list(VAL_MONTHS), "deflation_bar": DEFLECTION_BAR,
        "census_n": CENSUS_N, "pbo_splits": PBO_SPLITS,
    }
    with track_run("HYP-PM-0015-G1", params=params) as run:
        P, ihsg = load_panel(hist=hist, splits=splits)
        with db_connect(read_only=True) as c:
            fp = dataset_fingerprint(c)
        F = compute_features(P)
        elig = eligibility_mask(P["close"], P["volume"])
        schedule = build_schedule(P)
        ret_m = monthly_returns(P, schedule)
        cs_by_month, scores = run_walkforward(F, elig, ret_m, schedule)
        result = evaluate(P, ihsg, elig, ret_m, schedule, cs_by_month, scores,
                          fingerprint=fp)
        result["run_id"] = run.run_id
        result["git_commit"] = git_commit()
        run.metrics["n_test_months"] = len(result["months_test"])
        run.metrics["verdict_m1"] = result["verdict"]["m1"]["pass"]
        run.metrics["verdict_m2"] = result["verdict"]["m2"]["pass"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (HERE / f"RESULT_{stamp}.json").write_text(json.dumps(result, indent=1, default=str))
    return result


if __name__ == "__main__":
    print(__doc__)
    print("G0 state: machinery only. run_g1() is gated on ML_RANK_G1_APPROVED=1.")
