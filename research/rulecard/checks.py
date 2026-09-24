"""Mandatory implementation checks for a Rule Card run (D-055).

Every check encodes a defect this repository has already shipped at least once.
The runner executes all of them on every dry and real run; any FAIL makes the run
INVALID (an implementation/data verdict, never a hypothesis failure).

Incident register — keep this table in sync with tests/test_rulecard_checks.py:

| code   | incident                                                                 | check                          |
|--------|--------------------------------------------------------------------------|--------------------------------|
| LA-1   | VOLEX-001 +/-20 suspension mask and VOLEX-SN z_fwd filter looked ahead    | prefix_invariance              |
|        | (REMEASUREMENT_RESULT_2026-09-23, SUSPENSION_LOOKAHEAD_AUDIT)             | (signal AND universe)          |
| ZV-1   | FWD-PM-REGIME-001 admitted zero-volume carry-forward bars; frozen price   | traded_days_guard              |
|        | drove Kaufman ER to ~1 (LIFE, 2026-09-17)                                  |                                |
| ZV-2   | pre-2021 backfill prints IDX holidays / vendor gaps as zero-volume rows   | engine.non_session_dates       |
|        | for every ticker (RC-0001 dry run, 2026-09-24: 197 of 5,332 dates)        | (rows dropped; count reported) |
| ID-1   | HYP-PM-0003 / BROKER-001 predictor SUM(lot) identically zero on 68% of     | predictor_nondegenerate        |
|        | ticker-days — an accounting identity, not a signal (2026-09-11)           |                                |
| EX-1   | EXP-PM-0009/R1 exit-index defect: fwd_return == 0 by construction          | forward_returns_nontrivial     |
|        | (2026-09-15)                                                              | + entry_exit_order             |
| FILL-1 | pattern scan filled at the signal bar's close (2026-09-17 self-audit)      | entry_exit_order               |
| BM-1   | IHSG benchmark bias +0.35%/20d vs the EW liquid book                      | placebo (EW-rest machinery)    |
| SPL-1  | FORU ~20:1 split inside a provisional gap (2026-09-23 repair)             | split_band                     |

Survivorship (corpus = names listed in 2026-09) cannot be checked in data; the card
declares its direction instead. Known limitation, not checked: back-adjusted price
LEVELS carry future split information, so the Rp 50 floor is evaluated on adjusted
prices (returns and Rupiah value traded are unaffected).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from research.rulecard import engine

MIN_SCORE_COVERAGE = 0.80
MAX_MODAL_SHARE = 0.50
MAX_ZERO_RETURN_SHARE = 0.25
MAX_BIG_MOVE_SHARE = 0.005
PLACEBO_MAX_ABS_T = 3.0
PREFIX_SAMPLE = 6


def _res(code, name, ok, detail):
    return {"code": code, "check": name, "status": "PASS" if ok else "FAIL", "detail": detail}


def prefix_invariance(pan: engine.Panel, signal_fn, scores: pd.Series, formations,
                      sample: int = PREFIX_SAMPLE, seed: int = 11) -> dict:
    """LA-1. Recompute signal and universe on the panel truncated at date d;
    values at d must be identical to the full-panel values. Catches centred or
    symmetric windows, forward-filled/back-filled joins, full-sample normalisation,
    and any filter that reads the holding period."""
    forms = list(pd.to_datetime(pd.Series(formations)).sort_values())
    if not forms:
        return _res("LA-1", "prefix_invariance", False, "no formations")
    rng = np.random.default_rng(seed)
    pick = sorted(set([forms[0], forms[-1]] + list(
        rng.choice(forms, size=min(sample, len(forms)), replace=False))))
    bad = []
    raw = pan.P
    for d in pick:
        cut = raw[raw["date"] <= d]
        s_cut = signal_fn(cut)
        if not isinstance(s_cut, pd.Series) or not s_cut.index.equals(cut.index):
            return _res("LA-1", "prefix_invariance", False,
                        "signal() must return a Series on the input panel's index")
        rows = cut.index[cut["date"] == d]
        a, b = scores.reindex(rows).values, s_cut.reindex(rows).values
        same = np.isclose(a, b, rtol=1e-9, atol=1e-12, equal_nan=True)
        F_cut = engine.features(cut)
        e_cut = engine.liquid_idx_v1(cut, F_cut).reindex(rows).values
        e_full = pan.eligible.reindex(rows).values
        if not same.all():
            bad.append(f"{pd.Timestamp(d).date()}: signal differs on {int((~same).sum())} rows")
        if not (e_cut == e_full).all():
            bad.append(f"{pd.Timestamp(d).date()}: universe differs on {int((e_cut != e_full).sum())} rows")
    return _res("LA-1", "prefix_invariance", not bad,
                {"dates_checked": [str(pd.Timestamp(d).date()) for d in pick], "violations": bad})


def traded_days_guard(pan: engine.Panel, formations, sample: int = 10, seed: int = 13) -> dict:
    """ZV-1. Independent re-derivation (wide table, not the engine's rolling code): every
    eligible formation row traded on the day and on >= 18 of its trailing 20 own sessions.
    Checked on a seeded sample of formations — the defect class is systematic, not rare."""
    forms = list(pd.to_datetime(pd.Series(formations)))
    rng = np.random.default_rng(seed)
    pick = sorted(set(rng.choice(forms, size=min(sample, len(forms)), replace=False))) if forms else []
    P, viol, checked = pan.P, [], 0
    for d in pick:
        ii = pan.by_date.get(pd.Timestamp(d))
        if ii is None:
            continue
        rows = P.index[ii][pan.eligible.values[ii]]
        tks = P.loc[rows, "ticker"].values
        hist = pan.vol_w.loc[:pd.Timestamp(d), tks]
        traded = hist.apply(lambda col: int((col.dropna().tail(engine.TRADED_WINDOW) > 0).sum()))
        today = pan.vol_w.loc[pd.Timestamp(d), tks]
        bad = (traded < engine.TRADED_MIN).values | ~(today.values > 0)
        checked += len(tks)
        viol += [f"{pd.Timestamp(d).date()} {t}" for t in tks[bad]]
    return _res("ZV-1", "traded_days_guard", checked > 0 and not viol,
                {"rows_checked": checked, "violations": viol[:20]})


def predictor_nondegenerate(months: list[dict], pan: engine.Panel, scores: pd.Series,
                            formations, bucketing: str) -> dict:
    """ID-1. The score must cover the eligible set and actually vary across names."""
    cov = [m["score_coverage"] for m in months if "score_coverage" in m
           and not np.isnan(m["score_coverage"])]
    modal, flat_dates = [], 0
    for d in formations:
        ii = pan.by_date.get(pd.Timestamp(d))
        if ii is None:
            continue
        s = scores.reindex(pan.P.index[ii][pan.eligible.values[ii]]).dropna()
        if len(s) < 2:
            continue
        if bucketing != "flag":
            modal.append(float(s.value_counts(normalize=True).iloc[0]))
            if float(s.std()) == 0.0:
                flat_dates += 1
    detail = {"median_coverage": float(np.median(cov)) if cov else float("nan"),
              "median_modal_share": float(np.median(modal)) if modal else float("nan"),
              "flat_dates": flat_dates}
    ok = bool(cov) and detail["median_coverage"] >= MIN_SCORE_COVERAGE and flat_dates == 0
    if bucketing != "flag":
        ok = ok and bool(modal) and detail["median_modal_share"] <= MAX_MODAL_SHARE
    return _res("ID-1", "predictor_nondegenerate", ok, detail)


def entry_exit_order(months: list[dict]) -> dict:
    """FILL-1 / EX-1. entry strictly after formation; exit strictly after entry."""
    bad = [m["month"] for m in months
           if not (m["formation"] < m["entry"] < m["exit"])]
    return _res("FILL-1", "entry_exit_order", not bad, {"violations": bad})


def forward_returns_nontrivial(months: list[dict]) -> dict:
    """EX-1. A defect that zeroes the outcome must not pass as a null result."""
    v = [m for m in months if m.get("valid") and "univ" in m and "zero_returns" in m]
    if not v:
        return _res("EX-1", "forward_returns_nontrivial", False, "no valid months with returns")
    zero = sum(m["zero_returns"] for m in v) / max(1, sum(m["univ"] for m in v))
    prim = np.array([m["primary"] for m in v], dtype=float)
    ok = zero <= MAX_ZERO_RETURN_SHARE and np.nanstd(prim) > 0
    return _res("EX-1", "forward_returns_nontrivial", ok,
                {"zero_return_share": float(zero), "primary_sd": float(np.nanstd(prim))})


def split_band(months: list[dict]) -> dict:
    """SPL-1. Moves beyond any IDX price band inside holding windows mean unadjusted
    corporate actions in the data. Reported per month; the run is INVALID if they are
    more than a trace. (Excluding them would condition on the holding period.)"""
    v = [m for m in months if m.get("valid") and "big_moves_in_hold" in m]
    n = sum(m["univ"] for m in v)
    big = sum(m["big_moves_in_hold"] for m in v)
    share = big / n if n else float("nan")
    return _res("SPL-1", "split_band", bool(n) and share <= MAX_BIG_MOVE_SHARE,
                {"holdings": n, "holdings_with_big_move": big, "share": share})


def placebo(primary_placebo: list[float], lag: int = 3) -> dict:
    """BM-1. Scores shuffled within date must give a primary spread indistinguishable
    from zero; a biased benchmark or bucket-return defect shows up here."""
    from research.rulecard.stats import nw_t
    t = nw_t(primary_placebo, lag)
    ok = not np.isnan(t) and abs(t) < PLACEBO_MAX_ABS_T
    return _res("BM-1", "placebo", ok, {"t": t, "months": len(primary_placebo)})
