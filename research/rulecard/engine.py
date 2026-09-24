"""Monthly characteristic-sort engine for Rule Cards (D-055).

One engine for every month-end characteristic rule, so the conventions that past
incidents taught are implemented once and cannot drift per script:

- entry at the NEXT session's open, exit at the following formation's entry open
  (FILL-1: the pattern scan's close-fill inflated the one positive short-horizon arm);
- a name with no entry bar is removed from every bucket and the benchmark (not tradeable);
  a name with no exit bar exits at its last traded close and is flagged, never dropped
  (F-8 in remeasure_v2.py — dropping conditions on survival);
- the benchmark is the equal-weight rest of the SAME liquid universe on the SAME dates,
  never IHSG (BM-1: IHSG bias measured at +0.35%/20d, t 3.49);
- the universe is ex-ante only (LA-1: VOLEX's +/-20 suspension window and z_fwd both
  looked ahead) and requires traded days (ZV-1: zero-volume carry-forward bars scored as
  perfect trends in FWD-PM-REGIME-001);
- the session calendar excludes market-wide carry-forward rows (ZV-2: the pre-2021
  backfill prints IDX holidays as zero-volume rows for every ticker).

Returns are in percent. Rows are (ticker, date); the rule script's signal() must return
a Series on the same index, computed from rows dated <= each row's date only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from research.rulecard.card import BUCKETINGS

REQUIRED_COLS = ["ticker", "date", "open", "high", "low", "close", "volume"]
INDEX_TICKERS = {"IHSG", "^JKSE", "COMPOSITE"}

# liquid_idx_v1 — the pattern-scan / FADE-001 universe, plus the ex-ante split guard
MIN_PRIOR_SESSIONS = 25
ADV_WINDOW, ADV_MIN = 20, 1e9
PX_MIN = 50.0
TRADED_WINDOW, TRADED_MIN = 20, 18
# No IDX price band in any regime since 2000 allows a one-session move beyond 35%;
# a larger print is an unadjusted corporate action (SPL-1: FORU ~20:1 inside a gap).
SPLIT_BAND = 0.36
SPLIT_LOOKBACK = 21
STATE_LOOKBACK = 63                       # ~3 months, for the market_state fingerprint
MIN_UNIVERSE, MIN_BUCKET = 50, 5
# ZV-2 non-session detection (see non_session_dates)
NS_REF_WINDOW, NS_REF_MIN, NS_TRADED_FRAC, NS_MOVED_MAX = 60, 20, 0.50, 0.20
# IDX auto-rejection upper band by price tier (used only to flag unfillable long entries)
ARA_TIERS = ((200.0, 0.35), (5000.0, 0.25), (float("inf"), 0.20))


def prepare(panel: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in REQUIRED_COLS if c not in panel.columns]
    if missing:
        raise ValueError(f"panel missing columns: {missing}")
    P = panel[~panel["ticker"].isin(INDEX_TICKERS)].copy()
    P["date"] = pd.to_datetime(P["date"])
    dup = int(P.duplicated(["ticker", "date"]).sum())
    if dup:
        # fail closed: which duplicate wins is a data decision, not the engine's
        raise ValueError(f"panel has {dup} duplicate (ticker, date) rows — dedupe in load_panel()")
    for c in ("open", "high", "low", "close", "volume"):
        P[c] = P[c].astype("float64")
    P = P.sort_values(["ticker", "date"], kind="mergesort").reset_index(drop=True)
    drop = non_session_dates(P)
    if len(drop):
        P = P[~P["date"].isin(drop)].reset_index(drop=True)
    P.attrs["non_sessions_dropped"] = [str(pd.Timestamp(d).date()) for d in drop]
    return P


def non_session_dates(P: pd.DataFrame) -> pd.DatetimeIndex:
    """ZV-2. Dates that are not IDX sessions but carry a row for (almost) every ticker.

    Found by the RC-0001 dry run (2026-09-24): the pre-2021 yfinance backfill prints IDX
    holidays and vendor gaps as zero-volume, unchanged-price rows (Lebaran 2017-19,
    2017-06-01, 2018-03-30, 2018-12-31, 2019-01-01, 2016-04-13..19, ...: 197 of 5,332 dates).
    Treated as sessions they became month-end formations or entry days with no trading and
    filled every name's trailing 20-day window with "untraded" days, emptying the universe
    for weeks. A date is dropped only if BOTH hold (so a real session with a volume hole,
    where prices still moved, is kept):
      - traded names < 50% of the median traded count over the prior 60 dates, and
      - fewer than 20% of names changed their close.
    Uses the date itself and earlier dates only, so it is prefix-invariant."""
    traded = P.loc[P["volume"] > 0].groupby("date").size()
    dates = pd.DatetimeIndex(np.sort(P["date"].unique()))
    traded = traded.reindex(dates, fill_value=0).astype(float)
    ref = traded.rolling(NS_REF_WINDOW, min_periods=NS_REF_MIN).median().shift(1)
    moved = (P.groupby("ticker", sort=False)["close"].diff().abs() > 0).groupby(P["date"]).mean()
    moved = moved.reindex(dates, fill_value=0.0)
    bad = (traded < NS_TRADED_FRAC * ref) & (moved < NS_MOVED_MAX)
    return dates[bad.fillna(False).values]


def features(P: pd.DataFrame) -> pd.DataFrame:
    """Trailing-only features, one row per (ticker, date). Never reads a later row."""
    g = P.groupby("ticker", sort=False)
    F = pd.DataFrame(index=P.index)
    F["n_prior"] = g.cumcount()
    val = P["close"] * P["volume"]
    F["adv20"] = val.groupby(P["ticker"], sort=False).transform(
        lambda x: x.rolling(ADV_WINDOW, min_periods=ADV_WINDOW).mean())
    traded = (P["volume"] > 0).astype(float)
    F["traded20"] = traded.groupby(P["ticker"], sort=False).transform(
        lambda x: x.rolling(TRADED_WINDOW, min_periods=TRADED_WINDOW).sum())
    ret1 = g["close"].pct_change()
    F["ret1"] = ret1
    big = (ret1.abs() > SPLIT_BAND).astype(float)
    F["bigmove21"] = big.groupby(P["ticker"], sort=False).transform(
        lambda x: x.rolling(SPLIT_LOOKBACK, min_periods=1).max()) > 0
    F["ret63"] = g["close"].pct_change(STATE_LOOKBACK)
    return F


def liquid_idx_v1(P: pd.DataFrame, F: pd.DataFrame) -> pd.Series:
    return ((F["n_prior"] >= MIN_PRIOR_SESSIONS) & (F["adv20"] >= ADV_MIN)
            & (P["close"] >= PX_MIN) & (P["volume"] > 0)
            & (F["traded20"] >= TRADED_MIN) & ~F["bigmove21"])


def calendar(P: pd.DataFrame, start=None, end=None) -> pd.DataFrame:
    """Month-end formations, next-session entry, exit = next formation's entry."""
    cal = np.sort(P["date"].unique())
    s = pd.Series(cal)
    form = s.groupby(s.dt.to_period("M")).max()
    pos = np.searchsorted(cal, form.values, side="right")
    ok = pos < len(cal)
    form = form[ok]
    entry = pd.Series(cal[pos[ok]], index=form.index)
    C = pd.DataFrame({"formation": form.values, "entry": entry.values}, index=form.index)
    C["exit"] = C["entry"].shift(-1)
    C = C.dropna(subset=["exit"])
    if start is not None:
        C = C[C["formation"] >= pd.Timestamp(start)]
    if end is not None:
        C = C[C["formation"] <= pd.Timestamp(end)]
    C.index = C.index.astype(str)
    return C


def assign_buckets(scores: pd.Series, bucketing: str, seed_order=None) -> pd.Series:
    """1..K by ascending score (K = highest). flag: 1 = unflagged, 2 = flagged."""
    K = BUCKETINGS[bucketing]
    if bucketing == "flag":
        return (scores > 0).astype(int) + 1
    # rank(method='first') on a ticker-sorted frame is deterministic for ties
    pct = scores.rank(method="first") / len(scores)
    return np.ceil(pct * K).clip(1, K).astype(int)


def ara_open(prev_close, open_):
    band = np.select([prev_close < ARA_TIERS[0][0], prev_close < ARA_TIERS[1][0]],
                     [ARA_TIERS[0][1], ARA_TIERS[1][1]], ARA_TIERS[2][1])
    return open_ >= prev_close * (1 + band) - 1e-9


class Panel:
    """Prepared panel + wide price tables, built once per run."""

    def __init__(self, panel: pd.DataFrame):
        self.P = prepare(panel)
        self.non_sessions_dropped = list(self.P.attrs.get("non_sessions_dropped", []))
        self.F = features(self.P)
        self.eligible = liquid_idx_v1(self.P, self.F)
        self.open_w = self.P.pivot(index="date", columns="ticker", values="open")
        self.close_w = self.P.pivot(index="date", columns="ticker", values="close")
        self.vol_w = self.P.pivot(index="date", columns="ticker", values="volume")
        self.close_ff = self.close_w.ffill()
        self.ret_w = self.close_w.pct_change(fill_method=None)
        self.by_date = self.P.groupby("date").indices


def _spread(ret: pd.Series, mask: pd.Series) -> float:
    a, b = ret[mask], ret[~mask]
    if len(a) == 0 or len(b) == 0:
        return float("nan")
    return float(a.mean() - b.mean())


def run_months(pan: Panel, scores: pd.Series, card: dict, calendar_df: pd.DataFrame,
               control: pd.Series | None = None, with_returns: bool = True) -> list[dict]:
    bucketing = card["portfolio"]["bucketing"]
    K = BUCKETINGS[bucketing]
    use_high = card["portfolio"]["use_end"] == "high"
    use_long = card["portfolio"]["use"] == "long"
    kind = card["estimand"]["primary_kind"]
    used_b = K if use_high else 1
    rt = float(card["costs"]["round_trip_pct"])

    P, F = pan.P, pan.F
    rows, prev_w = [], None
    for m, c in calendar_df.iterrows():
        t, E, X = c["formation"], c["entry"], c["exit"]
        rec = {"month": m, "formation": str(pd.Timestamp(t).date()),
               "entry": str(pd.Timestamp(E).date()), "exit": str(pd.Timestamp(X).date())}
        ii = pan.by_date.get(t)
        if ii is None:
            rec.update(valid=False, reason="no rows at formation"); rows.append(rec); continue
        idx = P.index[ii]
        idx = idx[pan.eligible.loc[idx].values]
        rec["eligible"] = int(len(idx))
        sc = scores.reindex(idx)
        rec["score_coverage"] = float(sc.notna().mean()) if len(idx) else float("nan")
        idx = idx[sc.notna().values]
        tk = P.loc[idx, "ticker"].values
        # tradeable at entry: a bar with volume on the entry session
        e_open = pan.open_w.loc[E].reindex(tk).values
        e_vol = pan.vol_w.loc[E].reindex(tk).values
        ok = ~np.isnan(e_open) & (np.nan_to_num(e_vol) > 0)
        idx, tk, e_open = idx[ok], tk[ok], e_open[ok]
        rec["not_tradeable_at_entry"] = int((~ok).sum())
        n = len(idx)
        rec["univ"] = n
        if n < MIN_UNIVERSE:
            rec.update(valid=False, reason="universe below minimum"); rows.append(rec); continue
        s = scores.loc[idx].reset_index(drop=True)
        b = assign_buckets(s, bucketing)
        sizes = b.value_counts()
        rec["bucket_sizes"] = {int(k): int(v) for k, v in sizes.sort_index().items()}
        if sizes.reindex(range(1, K + 1)).fillna(0).min() < MIN_BUCKET:
            rec.update(valid=False, reason="bucket below minimum"); rows.append(rec); continue
        rec["valid"] = True
        if not with_returns:
            rows.append(rec); continue

        x_open = pan.open_w.loc[X].reindex(tk).values
        prevX = pan.close_ff.index[pan.close_ff.index.get_loc(X) - 1]
        stale = np.isnan(x_open)
        x_px = np.where(stale, pan.close_ff.loc[prevX].reindex(tk).values, x_open)
        ret = pd.Series((x_px / e_open - 1.0) * 100.0)
        win = pan.ret_w.loc[(pan.ret_w.index > E) & (pan.ret_w.index <= X), tk]
        big_hold = (win.abs() > SPLIT_BAND).any().values
        rec.update(stale_exits=int(stale.sum()), big_moves_in_hold=int(big_hold.sum()),
                   zero_returns=int((ret == 0).sum()))
        if use_long and used_b is not None:
            prev_close = pan.close_ff.loc[pan.close_ff.index[pan.close_ff.index.get_loc(E) - 1]].reindex(tk).values
            unfill = ara_open(prev_close, e_open) & (b.values == used_b)
            rec["ara_unfillable"] = int(unfill.sum())
            keep = ~unfill
            ret, b, s = ret[keep].reset_index(drop=True), b[keep].reset_index(drop=True), s[keep].reset_index(drop=True)
            idx, tk = idx[keep], tk[keep]

        bm = ret.groupby(b).mean().reindex(range(1, K + 1))
        if control is not None:
            # conditional sort: buckets within control terciles, averaged across terciles
            cv = control.reindex(idx).reset_index(drop=True)
            terc = np.ceil(cv.rank(method="first") / len(cv) * 3).clip(1, 3)
            parts = []
            for _, gi in ret.groupby(terc):
                bb = assign_buckets(s.loc[gi.index].reset_index(drop=True), bucketing)
                parts.append(gi.reset_index(drop=True).groupby(bb).mean().reindex(range(1, K + 1)))
            bm = pd.concat(parts, axis=1).mean(axis=1)
        rec["bucket_means"] = [float(v) for v in bm.values]
        used = (b == used_b)
        if kind == "top_minus_bottom":
            rec["primary"] = float(bm.iloc[-1] - bm.iloc[0])
        else:
            rec["primary"] = float(bm.iloc[used_b - 1] - ret[~used].mean())
        rec["deployment"] = _spread(ret, used)
        univ_mean = float(ret.mean())
        book = used if use_long else ~used
        book_mean = float(ret[book].mean())
        w_b = pd.Series(1.0 / book.sum(), index=tk[book.values])
        w_u = pd.Series(1.0 / len(tk), index=tk)
        if prev_w is None:
            to_b = to_u = 1.0
        else:
            to_b = 0.5 * w_b.sub(prev_w[0], fill_value=0).abs().sum()
            to_u = 0.5 * w_u.sub(prev_w[1], fill_value=0).abs().sum()
        prev_w = (w_b, w_u)
        rec.update(univ_mean=univ_mean, book_mean=book_mean, turn_book=float(to_b),
                   turn_univ=float(to_u),
                   uplift_net=float((book_mean - univ_mean) - rt * (to_b - to_u)))
        # fingerprints: used-bucket-minus-rest inside subgroups (full-universe breakpoints)
        adv = F.loc[idx, "adv20"].reset_index(drop=True)
        px = P.loc[idx, "close"].reset_index(drop=True)
        for name, v in (("adv", adv), ("price", px)):
            tq = np.ceil(v.rank(method="first") / len(v) * 3).clip(1, 3)
            rec[f"fp_{name}_low"] = _spread(ret[tq == 1], used[tq == 1])
            rec[f"fp_{name}_high"] = _spread(ret[tq == 3], used[tq == 3])
        rec["state"] = float(F.loc[idx, "ret63"].mean())
        rows.append(rec)
    return rows


def placebo_scores(pan: Panel, scores: pd.Series, calendar_df, seed: int = 7) -> pd.Series:
    """Scores shuffled across names within each formation date (fixed seed)."""
    rng = np.random.default_rng(seed)
    out = scores.copy()
    for t in calendar_df["formation"]:
        ii = pan.by_date.get(t)
        if ii is None:
            continue
        idx = pan.P.index[ii]
        v = out.loc[idx].values.copy()
        rng.shuffle(v)
        out.loc[idx] = v
    return out
