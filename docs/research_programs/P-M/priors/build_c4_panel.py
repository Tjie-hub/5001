#!/usr/bin/env python3
"""Canonical C4 panel builder -- research consolidation 2026-09-30.

Rebuilds the top-200-by-ADV60 universe panel (VOLEX-001/XP-001 convention,
per UNIVERSE_BENCHMARK_MEMO) monthly, PIT, with:
  - true cap weights from factor_zoo/data/fund_shares.pkl (verified 778/780
    tickers show genuinely varying share counts over 2020-06..2026-09 --
    this is real point-in-time data, not another stale snapshot).
  - the C1 tradeability rule: entry needs a real print; a position
    untradeable at a month-end is carried (forward-filled close) to its next
    real print.

IMPORTANT DEVIATION FROM THE ORIGINAL INSTRUCTION: this panel is NOT
issuance-corrected per D-064. That mechanism (data/adjustments.py
load_issuance_events/correct_issuance) is fully coded, but its data table
(corporate_action_events, populated by stockbit_corporate_actions.py from a
live Stockbit endpoint) is empty on THE WINDOWS MACHINE'S DB COPY (data
ends 2026-07-29, pre-D-064) -- verified directly against
D:\\IDX\\data\\walkforward.db, read-only, 2026-09-30. This is a claim about
that copy specifically, NOT about the Dell/real production system, which
the Owner is checking separately. Attempting to populate it live against
the Windows copy failed: its cached Stockbit token is expired (401), and
that machine's auto_token.log shows auto-refresh failing since at least
2026-09-22 ("REFRESH_FAILED ... action=manual_intervention_required") -- a
pre-existing infra issue on that copy, outside this session's scope to fix,
and not necessarily true of the Dell.

Per Owner direction (2026-09-30), this panel therefore falls back to the
STANDING interim rule already adopted in D-065_PROPOSAL_v2 SS2: rows with a
single-period return below -95% (mechanical corporate-action-drop
artifacts, unadjusted) are excluded from EW/CW means and reported
separately -- NOT the "no crude drop" instruction, because the thing it was
meant to be replaced with (D-064 correction) is not currently computable.
Every output this script produces is labeled accordingly. Regular stock
splits ARE still applied (data/adjustments.adjust_ohlcv, via
data.loaders._load_ohlcv_bulk(adjusted=True) -- audit R-1's sanctioned
path, unaffected by the corporate_action_events gap).

Run: DB_PATH=data/walkforward_prod_snapshot.db python3 build_c4_panel.py
Read-only against the DB snapshot; writes only to stdout / a local json.
"""
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd

from data.loaders import _load_ohlcv_bulk

ADV_MIN_IDR = 1_000_000_000     # Rp 1bn ADV60 floor, UNIVERSE_BENCHMARK_MEMO
PRICE_MIN = 50                   # Rp 50 close floor
TOP_N = 200
DROP_SCREEN = -0.95              # standing interim rule, D-065 v2 SS2 (see module docstring)
FUND_SHARES_PATH = Path(__file__).resolve().parent.parent / "factor_zoo" / "data" / "fund_shares.pkl"


def build_wide(dfs: dict, col: str) -> pd.DataFrame:
    frames = []
    for t, df in dfs.items():
        if t == "IHSG":
            continue
        s = df[["date", col]].copy()
        s["date"] = pd.to_datetime(s["date"])
        s = s.drop_duplicates("date").set_index("date")[col]
        s.name = t
        frames.append(s)
    return pd.concat(frames, axis=1, sort=False).sort_index()


def main():
    dfs = _load_ohlcv_bulk(final_only=True, adjusted=True)
    ihsg = dfs["IHSG"][["date", "close"]].copy()
    ihsg["date"] = pd.to_datetime(ihsg["date"])
    ihsg = ihsg.sort_values("date").set_index("date")["close"]

    close_w = build_wide(dfs, "close")
    vol_w = build_wide(dfs, "volume").reindex(close_w.index)
    # real-print mask BEFORE any forward-fill (audit: a stock only "prints"
    # when it actually trades; volume>0 and close>0 on that exact date)
    real_print = (vol_w > 0) & (close_w > 0) & close_w.notna()

    # month-end = last trading session per calendar month, from IHSG's own
    # calendar (matches POWER_BENCHMARK_MEMO's "last complete session")
    ym = pd.Series(ihsg.index, index=ihsg.index).dt.to_period("M")
    month_ends = ihsg.groupby(ym).apply(lambda s: s.index.max())
    month_ends = pd.DatetimeIndex(sorted(month_ends.values))

    # C1 carry-forward: last known (real) close per ticker, forward-filled
    # across ALL trading days, then sampled at month-end -- a month where a
    # ticker didn't print keeps its last real price (0% return that month;
    # the full move lands whenever the next real print occurs).
    close_ff = close_w.where(real_print).ffill()
    close_me = close_ff.reindex(month_ends)
    vol60 = vol_w.fillna(0)
    value_traded = (close_w.where(real_print, 0) * vol60.where(real_print, 0)).fillna(0)
    adv60 = value_traded.rolling(60, min_periods=20).mean()
    adv60_me = adv60.reindex(month_ends)

    # ---- fund_shares.pkl -> PIT shares, forward-filled per ticker ----
    shares_long = pd.read_pickle(FUND_SHARES_PATH)
    shares_long["date"] = pd.to_datetime(shares_long["date"])
    shares_w = shares_long.pivot_table(index="date", columns="ticker", values="shares", aggfunc="last")
    shares_w = shares_w.reindex(shares_w.index.union(month_ends)).ffill().reindex(month_ends)
    shares_coverage_me = shares_w.notna().sum(axis=1)

    # ---- universe selection per month-end: top-200 by ADV60, PIT ----
    eligible = (adv60_me >= ADV_MIN_IDR) & (close_me >= PRICE_MIN) & close_me.notna()
    universe_size = {}
    universe_members = {}
    for dt in month_ends:
        cand = adv60_me.loc[dt][eligible.loc[dt]].sort_values(ascending=False)
        top = cand.index[:TOP_N]
        universe_members[dt] = list(top)
        universe_size[dt] = len(top)

    # ---- monthly returns per ticker (C1 carry-forward already baked into close_ff) ----
    ret = close_me.pct_change()
    ihsg_me = ihsg.reindex(month_ends).ffill()
    ihsg_ret = ihsg_me.pct_change()

    # ---- yearly EW / CW / IHSG, with the standing -95% screen (flagged, see docstring) ----
    caps_me = close_me * shares_w
    rows = []
    dropped_rows = []
    # Universe + weights are FORMED at month-end t (using data through t only);
    # the return attributed to that formation is the FORWARD period t -> t+1.
    # Measuring the same-t return the universe was selected with is a
    # look-ahead/return-chasing bias -- exactly the class of bug this whole
    # audit exists to catch (v1 of this script had it; caught on first run
    # when EW/CW came out strongly positive against a strongly negative
    # IHSG-validated baseline -- see commit message).
    for i in range(len(month_ends) - 1):
        dt = month_ends[i]
        dt_next = month_ends[i + 1]
        members = universe_members[dt]
        r = ret.loc[dt_next, members]
        bad = r < DROP_SCREEN
        if bad.any():
            for tk in r.index[bad]:
                dropped_rows.append({"date": str(dt_next.date()), "ticker": tk, "ret": float(r[tk])})
        r_clean = r[~bad]
        w_cap = caps_me.loc[dt, r_clean.index]     # weights known AT FORMATION (no look-ahead)
        w_cap = w_cap[w_cap > 0]
        common = r_clean.index.intersection(w_cap.index)
        ew = r_clean.mean()
        cw = (r_clean[common] * w_cap[common] / w_cap[common].sum()).sum() if len(common) else np.nan
        rows.append({"date": dt_next, "year": dt_next.year, "n_universe": len(members),
                    "n_clean": len(r_clean), "n_capw": len(common),
                    "ew": ew, "cw": cw, "ihsg": ihsg_ret.loc[dt_next]})
    monthly = pd.DataFrame(rows).set_index("date")

    def compound(x):
        return float((1 + x.dropna()).prod() - 1)

    yearly = monthly.groupby("year").agg(
        ew=("ew", compound), cw=("cw", compound), ihsg=("ihsg", compound),
        months=("ew", "count"))

    total_months = len(monthly)
    full = {
        "ew_ann": float((1 + monthly["ew"]).prod() ** (12 / total_months) - 1),
        "cw_ann": float((1 + monthly["cw"].dropna()).prod() ** (12 / monthly["cw"].notna().sum()) - 1),
        "ihsg_ann": float((1 + monthly["ihsg"]).prod() ** (12 / total_months) - 1),
        "months": total_months,
    }

    out = {
        "window": {"first_month_end": str(month_ends[1].date()), "last_month_end": str(month_ends[-1].date()),
                   "n_month_ends": len(month_ends)},
        "shares_coverage_last": int(shares_coverage_me.iloc[-1]),
        "shares_coverage_first": int(shares_coverage_me[shares_coverage_me > 0].iloc[0]) if (shares_coverage_me > 0).any() else 0,
        "dropped_rows_n": len(dropped_rows),
        "dropped_rows_sample": dropped_rows[:15],
        "universe_size_mean": float(np.mean(list(universe_size.values()))),
        "yearly": yearly.reset_index().to_dict(orient="records"),
        "full_period": full,
    }
    print(json.dumps(out, indent=2, default=str))

    # stash heavier objects for the next script (contribution analysis) via pickle
    stash = {
        "close_me": close_me, "ret": ret, "caps_me": caps_me,
        "universe_members": universe_members, "month_ends": month_ends,
        "ihsg_ret": ihsg_ret, "dropped_rows": dropped_rows,
        "real_print": real_print,
    }
    pd.to_pickle(stash, "/tmp/c4_panel_stash.pkl")


if __name__ == "__main__":
    main()
