"""OHLCV input for month-end Rule Cards (D-055).

The extended panel = pre-2021 backfill (yfinance, regenerated 2026-09-23 under D-053,
1,414,611 bars) + the settled DB corpus (`ohlcv`, is_final=1, from 2021-07-05).

DATA-1 (found 2026-09-24 by the RC-0001 dry run): yfinance `history(auto_adjust=False)`
already split-adjusts OHLC — `auto_adjust` controls dividends only. 194 of the 197
pre-2021 events in `split_hist.pkl` are continuous in the raw backfill, so applying the
split table again (as remeasure_v2.py::split_adjust does) DOUBLE-adjusts: every pre-split
price is divided by the ratio a second time, and the split date shows a fake jump of
ratio x (HMSP 2016-06 +2,404%, ASII 2012-06 +989%). This loader therefore adjusts an event
only when the raw prices show the jump (`adjust_unadjusted_splits`) and reports the audit.
DATA-2 (same dry run): the backfill has isolated scale glitches — single bars printed at
~1/10 or ~10x their neighbours (MAPI and TOWR, 2018-03..05), which turned into +924% /
+322% "monthly returns". `drop_scale_glitches` removes a backfill bar only when it sits more than
GLITCH_FACTOR away from the median of its 5-bar neighbourhood (no IDX band allows a 3x
session move; a real re-pricing moves the median with it). This reads two bars ahead; it is vendor-error cleaning on the backfill only, never
applied to the DB corpus, and every dropped bar is listed in the audit.
On a duplicate (ticker, date) the DB row wins.
DB-SPLIT (validity audit, 2026-09-24): the DB corpus is split-adjusted at the source, but 3 of
81 verifiable `corporate_actions` splits were still gapped in it (a new-basis bar appended
after old-basis history, the case `data/adjustments.py` describes). `repair_db_splits` runs
the repository's own gap-verified adjustment (`data.adjustments.adjust_ohlcv`) over the DB
rows, so only a split whose jump is actually in the prices is applied, and lists each one.
SPL-1 cannot catch these: a forward split left unadjusted is a drop of less than 100%, and
three of them are far below the 0.1% share bar, yet each is a -50% or worse fake return.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
PM = REPO_ROOT / "docs" / "research_programs" / "P-M"
DEFAULT_HIST = PM / "forward_volex" / "remeasure" / "work" / "hist_pre2021.pkl"
DEFAULT_SPLITS = PM / "data_gaps" / "data" / "split_hist.pkl"
CUT = pd.Timestamp("2021-07-05")
COLS = ["ticker", "date", "open", "high", "low", "close", "volume"]


MIN_SPLIT_RATIO = 1.5          # below this a split jump is indistinguishable from a normal move
GLITCH_FACTOR = 3.0            # a bar 3x off both neighbours, reverting, is a vendor print error


def drop_scale_glitches(H: pd.DataFrame):
    H = H.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    c = H["close"].where(H["close"] > 0)
    # a bar far from its local median (2 bars each side) cannot be a real print: no IDX
    # price band allows a 3x move in one session, and glitches can alternate bar to bar
    med = c.groupby(H["ticker"], sort=False).transform(
        lambda x: x.rolling(5, center=True, min_periods=1).median())
    bad = (np.log(c / med).abs() > np.log(GLITCH_FACTOR)).fillna(False)
    dropped = [f"{t} {str(d)[:10]}" for t, d in zip(H.loc[bad, "ticker"], H.loc[bad, "date"])]
    return H[~bad].reset_index(drop=True), dropped


def adjust_unadjusted_splits(O: pd.DataFrame, SPL: pd.DataFrame, cut=CUT):
    """Back-adjust only the pre-cut split events whose jump is actually in the raw prices.

    For each event: jump = close(last bar before the split date) / close(first bar on or
    after it). Unadjusted raw data shows jump ~ ratio; already-adjusted data shows ~1.
    Events with ratio < MIN_SPLIT_RATIO are not adjusted (ambiguous) and counted."""
    SPL = SPL[SPL["ratio"] > 0].copy()
    SPL["date"] = pd.to_datetime(SPL["date"])
    SPL = SPL[SPL["date"] < cut].sort_values(["ticker", "date"])
    O = O.copy()
    fac = np.ones(len(O))
    idx = O.groupby("ticker", sort=False).indices
    dts_all, close = O["date"].values, O["close"].values
    audit = {"adjusted": [], "already_adjusted": 0, "ambiguous_small_ratio": 0, "no_data": 0}
    for t, ev in SPL.groupby("ticker", sort=False):
        ii = idx.get(t)
        if ii is None:
            audit["no_data"] += len(ev)
            continue
        dts = dts_all[ii]
        for sd, rt in zip(ev["date"].values.astype("datetime64[ns]"), ev["ratio"].values):
            pos = np.searchsorted(dts, sd)
            if pos == 0 or pos >= len(ii):
                audit["no_data"] += 1
                continue
            r = max(rt, 1.0 / rt)
            if r < MIN_SPLIT_RATIO:
                audit["ambiguous_small_ratio"] += 1
                continue
            jump = close[ii[pos - 1]] / close[ii[pos]]
            if abs(np.log(jump) - np.log(rt)) < abs(np.log(jump)):
                fac[ii[:pos]] *= rt
                audit["adjusted"].append(f"{t} {str(sd)[:10]} x{rt:g}")
            else:
                audit["already_adjusted"] += 1
    for c in ("open", "high", "low", "close"):
        O[c] = O[c].astype("float64") / fac
    O["volume"] = O["volume"].astype("float64") * fac
    return O, audit


def repair_db_splits(D: pd.DataFrame, factors: dict):
    """Gap-verified split repair of DB rows via data/adjustments.py (the single adjustment
    authority). factors: {ticker: [(ex_date 'YYYY-MM-DD', ratio), ...]} as returned by
    data.adjustments.load_split_factors. Returns (frame, list of applied 'TICKER date xR')."""
    from data.adjustments import adjust_ohlcv, _gap_is_real
    if not factors or D.empty:
        return D, []
    D = D.copy()
    D["date"] = pd.to_datetime(D["date"]).dt.strftime("%Y-%m-%d")
    D = D.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    parts, applied = [], []
    for tk, g in D.groupby("ticker", sort=False):
        sp = factors.get(tk)
        if sp:
            g = g.reset_index(drop=True)
            for ex, r in sp:
                if _gap_is_real(g["date"].astype(str), g["close"], str(ex)[:10], float(r)):
                    applied.append(f"{tk} {str(ex)[:10]} x{float(r):g}")
            g = adjust_ohlcv(g, sp)
        parts.append(g)
    O = pd.concat(parts, ignore_index=True)
    O["date"] = pd.to_datetime(O["date"])
    return O, applied


def merge_extended(H: pd.DataFrame, D: pd.DataFrame, SPL: pd.DataFrame, cut=CUT,
                   db_splits: dict | None = None) -> pd.DataFrame:
    H, D = H.copy(), D[D["ticker"] != "IHSG"].copy()
    D, db_applied = repair_db_splits(D, db_splits or {})
    H["date"], D["date"] = pd.to_datetime(H["date"]), pd.to_datetime(D["date"])
    H = H[H["date"] < cut]
    H, glitches = drop_scale_glitches(H[COLS])
    Hadj, audit = adjust_unadjusted_splits(H, SPL, cut)
    audit["scale_glitches_dropped"] = glitches
    audit["db_splits_repaired"] = db_applied
    O = pd.concat([Hadj, D[COLS]], ignore_index=True)
    O = O.drop_duplicates(["ticker", "date"], keep="last")
    O = O[(O["close"] > 0) & (O["low"] > 0) & (O["high"] >= O["low"])]
    O = O.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    O.attrs["split_audit"] = audit
    return O


def load_extended_ohlcv(hist=DEFAULT_HIST, splits=DEFAULT_SPLITS) -> pd.DataFrame:
    from data.db import connect          # lazy: keeps this module importable without a DB
    H = pd.read_pickle(hist)
    SPL = pd.read_pickle(splits)
    from data.adjustments import load_split_factors, read_raw_ohlcv
    with connect(read_only=True) as c:
        D = read_raw_ohlcv(c)
        factors = load_split_factors(c)
    return merge_extended(H, D, SPL, db_splits=factors)
