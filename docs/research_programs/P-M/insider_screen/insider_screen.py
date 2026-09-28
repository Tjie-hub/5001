"""SCREEN-PM-INS-001 -- insider-event screen through the D-060 event-time engine.

Reads PREDECLARATION.md (sha256 in PREDECLARATION.sha256, frozen at 0d5f350 before
any outcome is computed). One run; every pre-declared cell reported; the verdict is
the primary cell only (E1 accumulation, h20, ex-2025, gross, |t| >= 3.0 at >=48
valid months). A screen, not a hypothesis: no family slot, no Rule Card.

PIT convention (pre-declared): a transaction at date d flags the ticker's FIRST own
session strictly after d; the engine enters at the NEXT own session's open -- entry
two own sessions after the transaction, defusing T+1 disclosure latency.
"""
import hashlib
import json
import sqlite3
import sys
from collections import deque
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))

from research.rulecard import engine, events                      # noqa: E402
from research.rulecard.data import load_extended_ohlcv            # noqa: E402

START = pd.Timestamp("2018-01-01")        # first allowed ENTRY (pre-declared)
CUT = pd.Timestamp("2026-09-16")          # program data cutoff: last allowed ENTRY (pre-declared)
EX25 = pd.Timestamp("2025-01-01")         # ex-2025 split: entries strictly before (pre-declared)
RT = 0.006                                # frozen program round trip (net lens only)
HOLDS = (5, 20)

defects = {"buy_sign": 0, "sell_prev": 0, "events_outside_panel": 0, "flags_out_of_window": 0}


def load_insider_events() -> dict[str, pd.DataFrame]:
    """BUY/SELL rows with the pre-declared defect drops -> per-definition event
    frames of (ticker, event_date[, holder_name])."""
    con = sqlite3.connect(DB := ROOT / "data" / "walkforward.db")
    df = pd.read_sql(
        "SELECT ticker, event_date, holder_name, action_type, previous_shares, "
        "changes_shares, badges FROM insider_transactions", con)
    con.close()
    df["event_date"] = pd.to_datetime(df["event_date"])

    buy = df[df["action_type"] == "ACTION_TYPE_BUY"].copy()
    defects["buy_sign"] = int((buy["changes_shares"] <= 0).sum())
    buy = buy[buy["changes_shares"] > 0]
    sell = df[df["action_type"] == "ACTION_TYPE_SELL"].copy()
    bad = (sell["changes_shares"] >= 0) | sell["previous_shares"].isna() | (sell["previous_shares"] <= 0)
    defects["sell_prev"] = int(bad.sum())
    sell = sell[~bad]

    prev = buy["previous_shares"]
    from_zero = prev.isna() | (prev <= 0)
    e1 = buy[((prev > 0) & (buy["changes_shares"] / prev.where(prev > 0) >= 0.01)) | from_zero]
    e1s = sell[sell["changes_shares"].abs() / sell["previous_shares"] >= 0.01]
    badges = buy["badges"].fillna("[]")

    return {"E1": e1[["ticker", "event_date"]],
            "E2": buy[["ticker", "event_date", "holder_name"]],
            "E3": buy[badges != "[]"][["ticker", "event_date"]],
            "E1s": e1s[["ticker", "event_date"]]}


def map_to_flag_rows(pan: engine.Panel, ev: pd.DataFrame) -> pd.DataFrame:
    """Transaction -> the ticker's FIRST own session strictly after event_date
    (the pre-declared flag row). Counts events that map outside the panel."""
    P = pan.P
    out = []
    for tk, g in ev.groupby("ticker", sort=False):
        sub = P[P["ticker"] == tk]
        if sub.empty:
            defects["events_outside_panel"] += len(g)
            continue
        sess = pd.DatetimeIndex(sub["date"].values)
        pos = sess.searchsorted(pd.DatetimeIndex(g["event_date"].values), side="right")
        ok = pos < len(sess)
        defects["events_outside_panel"] += int((~ok).sum())
        if ok.any():
            holders = (g["holder_name"].values[ok] if "holder_name" in g
                       else np.full(int(ok.sum()), "", dtype=object))
            out.append(pd.DataFrame({"ticker": tk, "row": sub.index.values[pos[ok]],
                                     "holder": holders}))
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame(
        columns=["ticker", "row", "holder"])


def flags_from_events(pan: engine.Panel, ev: pd.DataFrame, name: str) -> pd.Series:
    P = pan.P
    flags = pd.Series(0.0, index=P.index)
    rows = map_to_flag_rows(pan, ev)
    if rows.empty:
        return flags
    if name == "E2":
        # a ticker-day state: >=2 distinct holders buying within the trailing 5 OWN
        # sessions inclusive; walk each ticker's mapped (session, holder) days.
        for tk, g in rows.groupby("ticker", sort=False):
            sub = P[P["ticker"] == tk]
            sess = pd.DatetimeIndex(sub["date"].values)
            lab = sub.index.values
            day_holders = g.groupby("row")["holder"].apply(set)
            days = pd.DatetimeIndex(P.loc[day_holders.index, "date"].values)
            pos = sess.searchsorted(days)
            buf = deque()                     # (session pos, holders) within trailing 5 sessions
            for i, p in enumerate(pos):
                buf.append((p, day_holders.iloc[i]))
                while buf and buf[0][0] < p - 4:
                    buf.popleft()
                holders = set()
                for _, hs in buf:
                    holders |= hs
                if len(holders) >= 2:
                    flags.loc[lab[p]] = 1.0
    else:
        flags.loc[rows["row"].unique()] = 1.0
    return flags


def split_masks(pan: engine.Panel, flags: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Full-window and ex-2025 masks over P.index, splitting on the flagged row's
    engine ENTRY date (next own session) -- the pre-declared split convention."""
    P = pan.P
    f = events._flag_array(pan, flags)
    s = np.flatnonzero(f)
    rem = P.groupby("ticker", sort=False).cumcount(ascending=False).values
    e = np.where(rem[s] >= 1, s + 1, s)
    ent = pd.DatetimeIndex(P["date"].values[e])
    in_win = (ent >= START) & (ent <= CUT)
    full = pd.Series(0.0, index=P.index)
    full.iloc[s[in_win]] = 1.0
    ex25 = pd.Series(0.0, index=P.index)
    ex25.iloc[s[in_win & (ent < EX25)]] = 1.0
    defects["flags_out_of_window"] = int((~in_win).sum())
    return full, ex25


def run_cell(pan, flags, hold) -> dict:
    card = {"signal": {"hold_sessions": hold}, "costs": {"round_trip_pct": RT}}
    rows, _ = events.run_event_months(pan, flags, card)
    val = [r for r in rows if r.get("valid") and np.isfinite(r.get("primary", np.nan))]
    out = {"events": int(events._flag_array(pan, flags).sum()), "months_valid": len(val)}
    if len(val) >= 3:
        t = lambda x: float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x))))
        prim = np.array([r["primary"] for r in val])
        net = np.array([r["uplift_net"] for r in val])
        out.update(primary_mean=float(prim.mean()), primary_t=t(prim),
                   net_mean=float(net.mean()), net_t=t(net),
                   frac_months_pos=float((prim > 0).mean()))
    return out


def main():
    sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    ev_all = load_insider_events()
    P = load_extended_ohlcv()
    P = P[P["date"] >= pd.Timestamp("2017-01-01")].reset_index(drop=True)
    pan = engine.Panel(P)

    results = {}
    split_cache = {}
    for name, ev in ev_all.items():
        flags = flags_from_events(pan, ev, name)
        full, ex25 = split_masks(pan, flags)
        split_cache[name] = (full, ex25)
        for hold in HOLDS:
            results[f"{name}|h{hold}|full"] = run_cell(pan, full, hold)
            results[f"{name}|h{hold}|ex2025"] = run_cell(pan, ex25, hold)

    primary = results["E1|h20|ex2025"]
    placebo = None
    if primary.get("months_valid", 0) >= 48 and abs(primary.get("primary_t", 0.0)) >= 3.0:
        full, _ = split_cache["E1"]
        pl = events.placebo_flags(pan, full)
        card = {"signal": {"hold_sessions": 20}, "costs": {"round_trip_pct": RT}}
        rows, _ = events.run_event_months(pan, pl, card)
        val = [r for r in rows if r.get("valid") and np.isfinite(r.get("primary", np.nan))]
        prim = np.array([r["primary"] for r in val])
        placebo = {"months_valid": len(val),
                   "primary_t": float(prim.mean() / (prim.std(ddof=1) / np.sqrt(len(prim))))}

    stamp = pd.Timestamp.now(tz="UTC").strftime("%Y%m%dT%H%M%SZ")
    result = {
        "record_type": "exploratory_screen",
        "canonical_id": "SCREEN-PM-INS-001",
        "predeclaration_sha256": (HERE / "PREDECLARATION.sha256").read_text().split()[0],
        "script_sha256": sha,
        "run_utc": stamp,
        "panel_rows": int(len(pan.P)),
        "panel_last_date": str(pd.Timestamp(pan.P["date"].max()).date()),
        "defects": defects,
        "events_per_def": {k: int(len(v)) for k, v in ev_all.items()},
        "cells": results,
        "primary_placebo": placebo,
    }
    (HERE / f"RESULT_{stamp}.json").write_text(json.dumps(result, indent=1))
    print(json.dumps(result["cells"], indent=1, default=float))
    print("PRIMARY:", json.dumps(primary, default=float))
    print("defects:", defects)


if __name__ == "__main__":
    main()
