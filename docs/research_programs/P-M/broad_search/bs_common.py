"""Shared driver for the broad-search screens (brief 2026-09-29, phase 1).

Everything here is committed before the frozen runs (D-063 F-1 rule). DB access goes
through the fingerprinted 2026-09-28 snapshot via data.db.connect; price loads use the
sanctioned research.rulecard.data merge; the wealth correction below is the brief rule-4
requirement that returns across rights/bonus/reverse ex-dates use each event's own terms.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))

SNAP = Path.home() / "wf_snapshot_20260929" / "walkforward-20260928-213012.db"
SNAP_SHA256 = "10f9c97fb20bf8e89b0688a4728bdae531dce9711f31ddd5270b414ea7946c13"
CUT = pd.Timestamp("2026-09-16")          # program data cutoff (last allowed entry)
SPLIT_DATE = pd.Timestamp("2021-07-05")   # brief's pre-declared halves
RT = 0.006                                # frozen program round trip (net lens only)
ADV_MIN_FLAG = 5e9                        # brief rule 5 primary universe at the flag row
FORU_CUTOFF = pd.Timestamp("2026-09-14")  # D-063: FORU excluded from this date onward

CORR_TYPES = ("rightissue", "bonus", "stock_reverse")   # splits are adjusted at source


def load_panel():
    """Backfill pkl + SNAPSHOT DB corpus through the sanctioned merge. FORU rows from
    2026-09-14 are dropped at the panel level (D-063)."""
    import research.rulecard.data as rcdata
    from data.adjustments import load_split_factors, read_raw_ohlcv
    from data.db import connect
    with connect(path=SNAP, read_only=True) as c:
        D = read_raw_ohlcv(c)
        factors = load_split_factors(c)
    foru = int(((D["ticker"] == "FORU") & (pd.to_datetime(D["date"]) >= FORU_CUTOFF)).sum())
    D = D[~((D["ticker"] == "FORU") & (pd.to_datetime(D["date"]) >= FORU_CUTOFF))]
    P = rcdata.merge_extended(pd.read_pickle(rcdata.DEFAULT_HIST), D,
                              pd.read_pickle(rcdata.DEFAULT_SPLITS), db_splits=factors)
    P = P[P["date"] <= CUT].reset_index(drop=True)
    return P, {"foru_rows_dropped": foru}


def load_ihsg(P):
    """IHSG daily close/ret1 from the same snapshot read (2021-07+ only; declared)."""
    import research.rulecard.data as rcdata
    from data.adjustments import read_raw_ohlcv
    from data.db import connect
    with connect(path=SNAP, read_only=True) as c:
        D = read_raw_ohlcv(c)
    ih = D[D["ticker"] == "IHSG"][["date", "close"]].copy()
    ih["date"] = pd.to_datetime(ih["date"])
    ih = ih.sort_values("date").reset_index(drop=True)
    # keep only dates inside the panel's session calendar
    cal = pd.DatetimeIndex(np.sort(pd.to_datetime(P["date"]).unique()))
    ih = ih[ih["date"].isin(set(cal))].reset_index(drop=True)
    ih["ret"] = ih["close"].pct_change()
    return ih


def parse_ca_events(types):
    """Corporate-action rows with per-event correction terms (m, c) and the announcement
    stamp. m = shares after per share before; c = IDR cash paid per share before."""
    con_con = __import__("sqlite3").connect(f"file:{SNAP}?mode=ro", uri=True)
    df = pd.read_sql("SELECT ticker, action_type, event_date, raw_json FROM "
                     "corporate_action_events", con_con)
    con_con.close()
    rows = []
    for _, r in df[df["action_type"].isin(types)].iterrows():
        j = json.loads(r["raw_json"])
        ak = r["action_type"]
        if ak == "rightissue":
            try:
                f = float(j["rightissue_new"]) / float(j["rightissue_old"])
                c = f * float(j["rightissue_price"])
                stamp = j.get("rightissue_created")
            except (KeyError, TypeError, ValueError, ZeroDivisionError):
                continue
        elif ak == "bonus":
            try:
                f = float(j["stocksplit_factor"])
                c = 0.0
                stamp = j.get("stocksplit_created")
            except (KeyError, TypeError, ValueError):
                continue
        else:  # stock_reverse
            try:
                f = float(j["stocksplit_factor"])
                c = 0.0
                stamp = j.get("stocksplit_created")
            except (KeyError, TypeError, ValueError):
                continue
        ex = j.get(f"{ak}_exdate") or j.get("stocksplit_exdate")
        rows.append({"ticker": r["ticker"], "type": ak, "m": 1.0 + f if ak == "rightissue" else f,
                     "c": c, "stamp": pd.to_datetime(stamp, errors="coerce", format="mixed"),
                     "exdate": pd.to_datetime(ex, errors="coerce", format="mixed")})
    return pd.DataFrame(rows)


def wealth_correct(P: pd.DataFrame, ev: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Gap-verified wealth correction at rights/bonus/reverse ex-dates (brief rule 4).

    For each event with usable terms: mechanical ex-day holder return
    M = (m*P_ex - c)/P_prev - 1; the correction phi = P_ex/(m*P_ex - c) is applied to all
    rows strictly before the ex-date (open/high/low/close), only when the raw series shows
    a jump the correction brings closer to zero — the same gap-verified discipline as
    adjust_unadjusted_splits / repair_db_splits. FORU events carry no terms (D-063).
    """
    P = P.copy()
    P["d"] = pd.to_datetime(P["date"])
    fac = np.ones(len(P))
    audit = {"applied": [], "already_adjusted": 0, "no_data": 0, "out_of_window": 0,
             "invalid_terms": 0, "below_band": 0}
    idx = P.groupby("ticker", sort=False).indices
    dts_all = P["d"].values
    for t, g in ev.dropna(subset=["exdate"]).groupby("ticker", sort=False):
        ii = idx.get(t)
        if ii is None:
            audit["no_data"] += len(g)
            continue
        dts = dts_all[ii]
        for _, r in g.iterrows():
            ex = np.datetime64(pd.Timestamp(r["exdate"]))
            if not (pd.Timestamp("2013-01-01") <= pd.Timestamp(r["exdate"]) <= CUT):
                audit["out_of_window"] += 1
                continue
            pos = np.searchsorted(dts, ex)
            if pos == 0 or pos >= len(ii):
                audit["no_data"] += 1
                continue
            m, c = float(r["m"]), float(r["c"])
            if not (np.isfinite(m) and m > 0 and np.isfinite(c) and c >= 0):
                audit["invalid_terms"] += 1
                continue
            prev = P["close"].values[ii][pos - 1]
            pex = P["close"].values[ii][pos]
            if not (prev > 0 and pex > 0):
                audit["no_data"] += 1
                continue
            arg = m * pex - c
            if not np.isfinite(arg) or arg <= 0:
                audit["invalid_terms"] += 1
                continue
            obs = np.log(pex / prev)
            mech = np.log(arg / prev)
            if abs(mech) < np.log(1.05):
                # no mechanical drop of >=5% implied -> nothing material to correct
                # (the analogue of adjust_unadjusted_splits' MIN_SPLIT_RATIO)
                audit["below_band"] += 1
                continue
            if obs >= 0 or abs(obs - mech) >= abs(obs):
                # a non-drop print at ex cannot be told apart from a genuine rally, and a
                # correction that does not bring the ex-day move closer to zero means the
                # series is already adjusted -- either way, skip (counted)
                audit["already_adjusted"] += 1
                continue
            phi = pex / (m * pex - c)
            fac[ii[:pos]] *= phi
            audit["applied"].append(
                f"{t} {str(pd.Timestamp(r['exdate']).date())} {r['type']} m={m:.4g} "
                f"c={c:.4g} phi={phi:.6f}")
    for col in ("open", "high", "low", "close"):
        P[col] = P[col].values * fac
    P = P.drop(columns=["d"]).reset_index(drop=True)
    return P, audit


def entry_split_flags(pan, flags: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Pre-declared halves by the flagged row's engine ENTRY date (next own session)."""
    from research.rulecard import events
    P = pan.P
    f = events._flag_array(pan, flags)
    s = np.flatnonzero(f)
    rem = P.groupby("ticker", sort=False).cumcount(ascending=False).values
    e = np.where(rem[s] >= 1, s + 1, s)
    ent = pd.DatetimeIndex(P["date"].values[e])
    pre = pd.Series(0.0, index=P.index)
    pre.iloc[s[ent < SPLIT_DATE]] = 1.0
    post = pd.Series(0.0, index=P.index)
    post.iloc[s[ent >= SPLIT_DATE]] = 1.0
    return pre, post


def ihsg_monthly_excess(pan, T, ih: pd.DataFrame) -> list[dict]:
    """Sleeve monthly return minus IHSG monthly return over the same months
    (observability only; the sleeve uses the SAME positions frame as the engine)."""
    from research.rulecard import events
    if len(T) == 0:
        return []
    Pos = events._positions(pan, T)
    leg = Pos.groupby("date")["ret"].mean()
    legs = {str(m): v for m, v in leg.groupby(pd.DatetimeIndex(leg.index).to_period("M"))}
    ihm = {str(m): v for m, v in ih.set_index("date")["ret"]
           .groupby(pd.DatetimeIndex(ih["date"]).to_period("M"))}
    cal = pd.DatetimeIndex(np.sort(pan.P["date"].unique()))
    n_sess = pd.Series(1, index=cal).groupby(cal.to_period("M").astype(str)).sum()
    out = []
    for m, s in sorted(legs.items()):
        if m not in ihm or m not in n_sess.index:
            continue
        ns = int(n_sess[m])
        out.append({"month": m,
                    "sleeve_pct": float(s.mean() * ns * 100.0),
                    "ihsg_pct": float(ihm[m].mean() * ns * 100.0),
                    "excess_pct": float((s.mean() - ihm[m].mean()) * ns * 100.0)})
    return out


def run_cell(pan, flags, hold, ih=None):
    """One arm: engine months (gross + net observability) + checks + vs-IHSG lens."""
    from research.rulecard import events
    card = {"signal": {"hold_sessions": hold}, "costs": {"round_trip_pct": RT}}
    rows, E = events.run_event_months(pan, flags, card)
    val = [r for r in rows if r.get("valid") and np.isfinite(r.get("primary", np.nan))]
    out = {"events": int(events._flag_array(pan, flags).sum()),
           "months_valid": len(val),
           "checks": {"FILL-1": events.event_order_check(E),
                      "ID-1": events.event_nondegenerate(pan, flags)}}
    if len(val) >= 3:
        t = lambda x: float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x))))
        prim = np.array([r["primary"] for r in val])
        out.update(primary_mean=float(prim.mean()), primary_t=t(prim),
                   net_mean=float(np.mean([r["uplift_net"] for r in val])),
                   frac_months_pos=float((prim > 0).mean()))
        # per-date headline (brief rule 7): mean DAILY excess over position-days
        Tt = E[E["tradeable"]]
        if len(Tt):
            Pos = events._positions(pan, Tt)
            book, _ = events._book(pan)
            ex = (Pos.groupby("date")["ret"].mean() - book.reindex(Pos.groupby("date").size().index)).dropna()
            out["perdate_mean_daily_excess_pct"] = float(ex.mean() * 100.0)
        if ih is not None:
            out["ihsg_months"] = ihsg_monthly_excess(pan, Tt, ih)
            if out["ihsg_months"]:
                xs = np.array([r["excess_pct"] for r in out["ihsg_months"]])
                out["ihsg_excess_mean"] = float(xs.mean())
                out["ihsg_excess_t"] = t(xs)
    return out
