"""Sniper setup filter (HYP-PM-0016 draft) — frozen driver, G0.

Everything numeric is fixed by PREDECLARATION.md. The population and the
outcome come ONLY from the frozen exit_study functions at this tree
(`E.entry_population`, `E.simulate_trade`) — no copies, no edits. G0 reads NO
outcomes (census counts only); `run_g1` refuses without
SNIPER_FILTER_G1_APPROVED=1.

Branch: research/sniper-filter-2026-10 (post-Task-0 hardening tip a28ec7e).
Admitted by D-070 §Decision 2 as the LAST price-feature study.
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "exit_study"))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import exit_study as E  # noqa: E402  (the FROZEN exit-study driver — called, never copied)
from data.db import connect as db_connect  # noqa: E402

# ── FROZEN constants (PREDECLARATION.md §2–§7) ───────────────────────────────
SEED = 20261007
G1_ENV = "SNIPER_FILTER_G1_APPROVED"
PANEL_PIN = "2026-10-06"
G1_FINGERPRINT = "f42275e34cb4525d3101fdf3effb14674b7192627db7b6a77a2bac9c5da5e73e"
RANK_WINDOW = 250            # sessions, positional, strictly before s
SELECT_QUANTILE = 0.60       # top 40% selected
SELECT_MIN_PRIOR = 5
TRAIN_END = "2015-12"        # train months <= TRAIN_END
VAL_START, VAL_END = "2016-01", "2021-09"
TEST_START = "2021-10"
EMBARGO = 20                 # sessions between a training label's exit and the refit year's first prediction
M1_C_VALUES = (0.1, 10.0)
M2_PARAMS = dict(max_depth=3, learning_rate=0.1, max_iter=200,
                 early_stopping=False, random_state=SEED)
FEATURES = ("zone_touches", "planned_rr", "zone_width_atr", "zone_stop_atr",
            "close_ma20_atr", "close_ma50_atr", "ma200_slope", "park60",
            "ret126", "mkt_above_ma200")
# R8 (Revision 1): the census depth is UNRESOLVED — hardening carries 276
# (~3.06), the unratified recount (broad_search_v2 RECOUNT_W0 + CENSUS_NOTE)
# carries 561 (bar 3.2745). The PRIMARY pass bar freezes at the stricter count:
CENSUS_BASE_PRIMARY = 561            # unratified recount (RECOUNT_W0/CENSUS_NOTE)
CENSUS_N_PRIMARY = CENSUS_BASE_PRIMARY + 4   # 565; exact E[max|Z|] = BAR_PRIMARY
BAR_PRIMARY = 3.2765                 # frozen; exact emax_abs_z(565) = 3.2765 (561 -> 3.2745 reproduced)
CENSUS_N_SECONDARY = 280             # hardening count (D-070 context)
BAR_SECONDARY = 3.07                 # exact E[max|Z|] @ 280 = 3.0713 (secondary line)
# R6 (Revision 1): the G1 fingerprint gate runs against this READ-ONLY SNAPSHOT
# of the production DB (SQLite backup API, 2026-10-07), because the live DB
# gains final rows daily and a whole-DB fingerprint would drift.
SNAPSHOT_PATH = "/home/tjiesar/scratch/sniper_filter_g1/walkforward_snapshot_2026-10-07.db"
SNAPSHOT_SHA256 = "c42c151e4a825f622349e42891b0083c5579f6816228e1452d9c5869de68d177"
SNAPSHOT_FINGERPRINT = "f42275e34cb4525d3101fdf3effb14674b7192627db7b6a77a2bac9c5da5e73e"
# (the snapshot's dataset fingerprint EQUALS G1FIX's: max_date 2026-10-06,
#  1,101,826 rows — the backup captured the identical data state; both hashes
#  are frozen in PREDECLARATION §11 and verified at G1)
PARK_N = 60
MOM_N = 126
MA200_SLOPE_N = 20


def emax_abs_z(n_trials: int, hi: float = 40.0, steps: int = 400_000) -> float:
    """The repo's deflation-bar method: exact E[max|Z_1..Z_N|] over N iid
    standard normals, int_0^inf [1 - (2 Phi(x)-1)^N] dx (ml-rank HANDOFF_G0 §2,
    the D-062/CHECKER_REVIEW/D-064 two-sided convention)."""
    h = hi / steps
    s = 0.0
    for i in range(steps):
        x = (i + 0.5) * h
        p = 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))
        s += 1.0 - (2.0 * p - 1.0) ** n_trials
    return s * h


def load_dataset():
    """The pinned panel via the FROZEN exit_study loader (R7: the IHSG series is
    dropped — no IHSG bar exists before 2021-07, which made the old feature 10
    constant for most of the sample)."""
    P = E.load_panel()
    for k in list(P):
        P[k] = P[k].loc[:PANEL_PIN]
    return P


def market_index(P, owner) -> pd.Series:
    """R7: the equal-weight market index — the daily mean close-to-close return
    of the owner-screen-eligible universe (adv20 mask at that day, causal),
    cumulated from 1.0. Point in time and with full history (the IHSG
    replacement; feature count stays 10)."""
    C = P["close"]
    r = (C / C.shift(1) - 1.0).where(owner)
    mean_r = r.mean(axis=1, skipna=True)
    return (1.0 + mean_r.fillna(0.0)).cumprod()


def build_population(P):
    """The frozen E-SN population, built exactly as G1FIX builds it."""
    C = P["close"]
    adv20 = (C * P["volume"]).rolling(20, min_periods=20).mean()
    owner = adv20 >= E.ADV20_MIN
    I_by_stock = {}
    for tk in C.columns:
        if C[tk].notna().sum() >= E.PIVOT_WINDOW + 2 * E.PIVOT_HALF + 2:
            I_by_stock[tk] = E.stock_indicators(
                P["open"][tk].values.astype(float), P["high"][tk].values.astype(float),
                P["low"][tk].values.astype(float), C[tk].values.astype(float),
                P["volume"][tk].values.astype(float))
    pop = E.entry_population(P, I_by_stock, owner)
    return owner, I_by_stock, pop


def zone_group_at(tr, P, I_by_stock) -> dict:
    """The support zone group the frozen signal picked — by calling the frozen
    E.zone_context and re-selecting the highest-mean group below the close
    (sniper_signal_at's rule). Consistency-checked against the trade's own
    zone_low."""
    tk, s = tr["ticker"], tr["s"]
    O = P["open"][tk].values.astype(float)
    H = P["high"][tk].values.astype(float)
    L = P["low"][tk].values.astype(float)
    C = P["close"][tk].values.astype(float)
    groups = E.zone_context(L, H, I_by_stock[tk], s)
    below = [g for g in groups if g["mean"] < C[s]]
    if not below:
        raise ValueError(f"no below group at {tk} s={s}")
    z = max(below, key=lambda g: g["mean"])
    if abs(z["min"] - tr["zone_low"]) > 1e-9:
        raise ValueError(f"zone group mismatch at {tk} s={s}")
    return z


def parkinson60(H, L, s: int) -> float:
    """VOLEX measure: sqrt( mean_60( ln(H/L)^2 ) / (4 ln 2) ), window ending s."""
    lo = max(0, s - PARK_N + 1)
    h = H[lo:s + 1]
    l = L[lo:s + 1]
    if len(h) < PARK_N or not (np.all(np.isfinite(h)) and np.all(np.isfinite(l))
                               and np.all(h > 0) and np.all(l > 0)):
        return float("nan")
    return float(np.sqrt(np.mean(np.log(h / l) ** 2) / (4.0 * math.log(2.0))))


def raw_features(tr, P, I_by_stock, mkt_idx, mkt_ma200) -> dict:
    """The 10 raw feature values at the setup day s (PREDECLARATION §3, as
    amended by Revision 1 R7: feature 10 is mkt_above_ma200 — the equal-weight
    market index built from the panel, replacing the constant-for-most-of-sample
    IHSG series)."""
    tk, s = tr["ticker"], tr["s"]
    H = P["high"][tk].values.astype(float)
    L = P["low"][tk].values.astype(float)
    C = P["close"][tk].values.astype(float)
    I = I_by_stock[tk]
    atr = tr["atr"]
    grp = zone_group_at(tr, P, I_by_stock)
    zmid = (tr["zone_low"] + tr["zone_top"]) / 2.0
    risk = zmid - tr["stop"]
    mkt_here = 0.0
    im = mkt_ma200.iloc[s] if s < len(mkt_ma200) else float("nan")
    ic = mkt_idx.iloc[s] if s < len(mkt_idx) else float("nan")
    if np.isfinite(im) and np.isfinite(ic):
        mkt_here = 1.0 if ic > im else 0.0
    return {
        "zone_touches": float(grp["count"]),
        "planned_rr": (tr["target"] - zmid) / risk if risk > 0 else float("nan"),
        "zone_width_atr": (tr["zone_top"] - tr["zone_low"]) / atr,
        "zone_stop_atr": (tr["zone_top"] - tr["stop"]) / atr,
        "close_ma20_atr": (C[s] - I["ma20"][s]) / atr,
        "close_ma50_atr": (C[s] - I["ma50"][s]) / atr,
        "ma200_slope": ((I["ma200"][s] - I["ma200"][s - MA200_SLOPE_N]) / atr
                        if s >= MA200_SLOPE_N and np.isfinite(I["ma200"][s - MA200_SLOPE_N])
                        else float("nan")),
        "park60": parkinson60(H, L, s),
        "ret126": (C[s] / C[s - MOM_N] - 1.0
                   if s >= MOM_N and C[s - MOM_N] > 0 else float("nan")),
        "mkt_above_ma200": mkt_here,
        "fill_pos": int(tr["t1"]),   # R5: the fill bar index (known by close of s-1 at the latest... it IS the fill day)
    }


def feature_table(P, I_by_stock, pop, mkt_idx, mkt_ma200) -> pd.DataFrame:
    """One row per filled E-SN setup: raw features (no outcomes)."""
    rows = {}
    for tr in pop["sniper"]:
        rows[(tr["ticker"], tr["s"])] = {
            **raw_features(tr, P, I_by_stock, mkt_idx, mkt_ma200),
            "month": tr["month"], "pos": tr["s"],
        }
    return pd.DataFrame.from_dict(rows, orient="index")


def add_ranks(ft: pd.DataFrame) -> pd.DataFrame:
    """Cross-sectional percentile rank among the filled setups in the trailing
    RANK_WINDOW sessions before s. Reference set (Revision 1 R5): setups with
    setup pos in [p(s)-250, p(s)-1] — strictly EARLIER DAYS, never the same
    day — whose FILL bar index is also < p(s) (a fill watched for 20 sessions
    is not known at s until it happens). Fallback to the raw value where the
    rank is undefined; NaN stays NaN (C-1/C-2)."""
    out = ft.copy()
    pos_vals = ft["pos"].values.astype(np.int64)
    fill_vals = ft["fill_pos"].values.astype(np.int64)
    for f in FEATURES:
        if f not in ft.columns:
            raise KeyError(f)
        vals = ft[f].values.astype(float)
        ranked = np.empty(len(vals), dtype=float)
        for i in range(len(vals)):
            p = pos_vals[i]
            m = (pos_vals >= p - RANK_WINDOW) & (pos_vals < p) & (fill_vals < p)
            prior = vals[m]
            prior = prior[np.isfinite(prior)]
            x = vals[i]
            if not np.isfinite(x) or len(prior) == 0:
                ranked[i] = x            # C-2 fallback (NaN stays NaN)
            else:
                ranked[i] = (np.sum(prior < x) + 0.5 * np.sum(prior == x)) / len(prior)
        out[f + "_r"] = ranked
    out["ranked"] = True
    return out        # original row order preserved (no re-sorting anywhere)


def m0_score(ft: pd.DataFrame) -> pd.Series:
    """M0: equal-weight mean of 1 - rank(park60) and rank(ret126); a setup with
    either component undefined is not scored (C-3)."""
    a = 1.0 - ft["park60_r"]
    b = ft["ret126_r"]
    s = pd.Series(np.nan, index=ft.index)
    ok = np.isfinite(a) & np.isfinite(b)
    s[ok] = 0.5 * (a[ok] + b[ok])
    return s


def select_mask(score: pd.Series, pos: pd.Series, fill_pos: pd.Series) -> pd.Series:
    """The frozen selection rule: score >= the 60th percentile of the scores of
    the setups in the trailing RANK_WINDOW sessions strictly before s whose
    fill was already known (fill bar index < p(s) — Revision 1 R5); < 5 prior
    scored setups -> the percentile over ALL known prior scored setups; none ->
    not selected (PREDECLARATION §5). Call ONCE per configuration on the FULL
    score series (every scored setup, 2016 onward) and index into val/test/PBO
    afterwards — never on a split subset (Revision 1 R1: subset windows start
    cold and violate §5)."""
    order = pd.DataFrame({"score": score, "pos": pos, "fill": fill_pos}) \
        .dropna(subset=["score"])
    order = order.sort_values("pos", kind="mergesort")
    arr = order["score"].values.astype(float)
    posv = order["pos"].values.astype(np.int64)
    fillv = order["fill"].values.astype(np.int64)
    out = pd.Series(False, index=score.index)
    for i in range(len(order)):
        p = posv[i]
        m = (posv >= p - RANK_WINDOW) & (posv < p) & (fillv < p)
        prior = arr[m]
        if len(prior) < SELECT_MIN_PRIOR:
            mk = posv < p
            prior = arr[mk & (fillv < p)]
            if len(prior) < SELECT_MIN_PRIOR:
                prior = arr[mk]          # declared fallback: all prior scored
        if len(prior) == 0:
            continue
        out[order.index[i]] = arr[i] >= np.quantile(prior, SELECT_QUANTILE)
    return out


def era_of(month: str) -> str:
    return "E1" if month < "2021-10" else "E2"


def first_pos_of_year(index: pd.DatetimeIndex, year: int) -> int:
    """Panel position of the first session of `year` (len(index) if none)."""
    d0 = pd.Timestamp(f"{year}-01-01")
    pos = index.searchsorted(d0, side="left")
    return int(pos) if pos < len(index) else len(index)


def train_mask_for(frame: pd.DataFrame, year: int, first_pos: int) -> pd.Series:
    """The frozen embargo rule: a training setup's month is <= Y-1 AND its trade
    has EXITED at least EMBARGO sessions before the refit year's first session
    (exit_pos <= first_pos - EMBARGO). PIT-tested (test b)."""
    m = frame["month"] <= f"{year - 1}-12"
    m &= frame["exit_pos"] <= first_pos - EMBARGO
    return m


def fingerprint_from_snapshot() -> dict:
    """R6: the dataset fingerprint computed against the FROZEN READ-ONLY
    SNAPSHOT (scratch, outside the repo) — the live DB gains final rows daily,
    so a whole-DB fingerprint would drift between freeze and G1. Verifies the
    snapshot file's sha256 AND its dataset fingerprint against the frozen
    values; SystemExit on either mismatch (checked BEFORE any outcome)."""
    import hashlib
    h = hashlib.sha256()
    with open(SNAPSHOT_PATH, "rb") as fh:                 # streamed: 14.7 GB file
        for chunk in iter(lambda: fh.read(1 << 24), b""):
            h.update(chunk)
    got = h.hexdigest()
    if got != SNAPSHOT_SHA256:
        raise SystemExit(f"STOP: snapshot sha256 mismatch: {got[:16]}… != "
                         f"{SNAPSHOT_SHA256[:16]}…")
    with db_connect(path=SNAPSHOT_PATH, read_only=True) as conn:
        fp = E.dataset_fingerprint(conn)
    if fp["sha256"] != SNAPSHOT_FINGERPRINT:
        raise SystemExit(f"STOP: snapshot dataset fingerprint mismatch: "
                         f"{fp['sha256'][:16]}… != {SNAPSHOT_FINGERPRINT[:16]}…")
    return fp


def census_g0() -> dict:
    """G0 census — COUNTS ONLY. No outcome, no R, no return of any kind."""
    P = load_dataset()
    owner, I_by_stock, pop = build_population(P)
    mkt = market_index(P, owner)
    mkt_ma200 = mkt.rolling(200, min_periods=200).mean()
    fp = fingerprint_from_snapshot()
    events = pop["events"]
    kinds = {}
    for ev in events:
        kinds[ev["kind"]] = kinds.get(ev["kind"], 0) + 1
    ft = feature_table(P, I_by_stock, pop, mkt, mkt_ma200)
    ft = add_ranks(ft)
    # rank-fallback counts: the raw value is used where the rank would be
    # undefined (no prior KNOWN setup in the window, or a NaN own value) — C-2
    fb = {}
    pos_vals = ft["pos"].values.astype(np.int64)
    fill_vals = ft["fill_pos"].values.astype(np.int64)
    for f in FEATURES:
        vals = ft[f].values.astype(float)
        n_fallback = 0
        for i, x in enumerate(vals):
            p = pos_vals[i]
            m = (pos_vals >= p - RANK_WINDOW) & (pos_vals < p) & (fill_vals < p)
            prior = vals[m]
            if not np.isfinite(x) or not any(np.isfinite(prior)):
                n_fallback += 1
        fb[f] = n_fallback
    by_era = {"E1": 0, "E2": 0}
    by_year = {}
    for tr in pop["sniper"]:
        by_era[era_of(tr["month"])] += 1
        y = tr["month"][:4]
        by_year[y] = by_year.get(y, 0) + 1
    out = {
        "dataset_fingerprint": fp,
        "g1_fingerprint": G1_FINGERPRINT,
        "fingerprint_matches_g1fix": fp["sha256"] == G1_FINGERPRINT,
        "snapshot_path": SNAPSHOT_PATH,
        "panel_pin": PANEL_PIN,
        "n_filled_setups": len(pop["sniper"]),
        "n_filled_by_era": by_era,
        "n_filled_by_year": dict(sorted(by_year.items())),
        "events": kinds,
        "n_setups_total_events": kinds.get("setup", 0) + kinds.get("setup_while_locked", 0),
        "feature_nan_counts": {f: int(ft[f].isna().sum()) for f in FEATURES},
        "rank_fallback_counts": fb,
        "census_n_primary": CENSUS_N_PRIMARY,
        "census_n_secondary": CENSUS_N_SECONDARY,
        "configurations": 4,
        "bar_primary_exact": round(emax_abs_z(CENSUS_N_PRIMARY), 4),
        "bar_primary_frozen": BAR_PRIMARY,
        "bar_secondary_exact": round(emax_abs_z(CENSUS_N_SECONDARY), 4),
        "bar_secondary_frozen": BAR_SECONDARY,
        "gates": {"g0": "counts only; no outcome computed",
                  "g1": f"{G1_ENV}=1 required"},
        "seed": SEED,
    }
    return out


def run_g1() -> dict:
    """THE single run (gated). Refuses without SNIPER_FILTER_G1_APPROVED=1."""
    if os.environ.get(G1_ENV) != "1":
        raise SystemExit("G1 is gated: set SNIPER_FILTER_G1_APPROVED=1 only after "
                         "owner/planner approval of the frozen G0.")
    raise NotImplementedError("G1 orchestration (RESULT/VERDICT writers) is wired "
                              "at the G1 gate; the G0 freeze is exercised by the "
                              "PIT tests and the counts-only census.")


if __name__ == "__main__":
    print(__doc__)
