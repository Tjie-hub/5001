"""SHOCK->ABSORPTION->CONTINUATION feasibility count (one pass, frozen spec).

Implements docs/research_programs/P-M/shock_absorption/FEASIBILITY_SPEC_2026-09-21.md
section 3 exactly (frozen c8d0270, anchor correction cd0cd0a). Conventions reused
verbatim from forward_fade/scripts/fade_failed_breakdown.py: full per-ticker
calendar frame, next-open entry, exit at close of entry+h-1, COST=0.006,
contamination guard (|ret|>35% or split), cluster_t on entry dates, dual
benchmarks (IHSG identical-window; equal-weight LIQUID book keyed at the marker
session, the decision point from which entry occurs at the next open).

All paths derive from this file's location (run_formation.py idiom). Read-only
against data/walkforward.db. Exploratory: registers nothing, consumes no family
slot, writes no ledger. One pass only.
"""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent          # .../shock_absorption/scripts
SA = HERE.parent                                # .../shock_absorption
REPO = HERE.parents[4]                          # repo root
DB = REPO / "data" / "walkforward.db"

# ---- frozen constants (spec s3 / fade conventions) ----
SHOCK_RET = 0.10        # single-session close-to-close up-shock
ADV_THRESH = 1e9        # FADE liquid gate (benchmark book only)
PRICE_FLOOR = 50
MIN_SESSIONS = 25
GUARD_WINDOW = 20
GUARD_MIN_TRADED = 18
ABS_WINDOW = 3          # sessions strictly after the shock to find the marker
PRE_WINDOW = 5          # sessions before the shock for the pre-shock flag
HORIZONS = (5, 10, 20)
COST = 0.006
CONTAM_MOVE = 0.35
WINDOW_START = pd.Timestamp("2025-01-02")   # shock window (bandar coverage)
ACCDIST_SCORE = {         # 7-level map (spec s3)
    "Big Acc": 3, "Normal Acc": 2, "Small Acc": 1, "Neutral": 0,
    "Small Dist": -1, "Normal Dist": -2, "Big Dist": -3,
}
MARKER_MIN_SCORE = 2      # top1 in {Normal Acc, Big Acc}
VPIN_FROM = pd.Timestamp("2026-06-05")


def load():
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    d = pd.read_sql(
        "SELECT ticker,date,open,close,volume FROM ohlcv "
        "WHERE is_final=1 AND close>0 AND volume>=0 AND ticker!='IHSG'", con)
    ihsg = pd.read_sql(
        "SELECT date,open,close FROM ohlcv WHERE ticker='IHSG' AND is_final=1", con)
    bd = pd.read_sql(
        "SELECT ticker,trade_date,top1_accdist,top3_accdist,net_broker_count,"
        "broker_accdist FROM bandar_detector", con)
    vp = pd.read_sql("SELECT ticker,date,vpin_label FROM vpin_scores", con)
    ca = pd.read_sql("SELECT ticker,date,action FROM corporate_actions", con)
    con.close()

    d["date"] = pd.to_datetime(d["date"])
    d = d.sort_values(["ticker", "date"]).reset_index(drop=True)
    ihsg["date"] = pd.to_datetime(ihsg["date"])
    ihsg = ihsg.sort_values("date").set_index("date")
    bd["trade_date"] = pd.to_datetime(bd["trade_date"])
    bd["top1_score"] = bd["top1_accdist"].map(ACCDIST_SCORE)
    bd["top3_score"] = bd["top3_accdist"].map(ACCDIST_SCORE)
    bd = bd.rename(columns={"trade_date": "date"})
    unmapped = int(bd["top1_accdist"].notna().sum() - bd["top1_score"].notna().sum())
    vp["date"] = pd.to_datetime(vp["date"])
    splits = ca[ca.action == "split"][["ticker", "date"]].copy()
    splits["date"] = pd.to_datetime(splits["date"])
    splits["is_split"] = 1
    return d, ihsg, bd, vp, splits, unmapped


def build(d, bd, splits):
    # per-ticker calendar frame; nothing dropped before rolling windows (fade build)
    g = d.groupby("ticker", sort=False)
    d["ret"] = g["close"].pct_change()
    d["n"] = g.cumcount()
    dval = d.close * d.volume
    d["adv20"] = dval.groupby(d.ticker).transform(
        lambda s: s.rolling(20, min_periods=15).mean())
    d["adv20"] = d.groupby("ticker", sort=False)["adv20"].shift(1)
    nz = (d.volume > 0).astype(int)
    d["nz20"] = nz.groupby(d.ticker).transform(
        lambda s: s.shift(1).rolling(GUARD_WINDOW, min_periods=GUARD_WINDOW).sum())
    d = d.merge(splits, on=["ticker", "date"], how="left")
    d["is_split"] = d["is_split"].fillna(0)
    d["bad"] = ((d.ret.abs() > CONTAM_MOVE) | (d.is_split > 0)).astype(int)
    d["liq"] = ((d.adv20 >= ADV_THRESH) & (d.close >= PRICE_FLOOR) &
                (d.n >= MIN_SESSIONS) & (d.volume > 0) &
                (d.nz20 >= GUARD_MIN_TRADED)).fillna(False).astype(bool)
    g = d.groupby("ticker", sort=False)
    d["entry_open"] = g["open"].shift(-1)      # next session's open
    for h in HORIZONS:
        d[f"exit_close_{h}"] = g["close"].shift(-h)   # close of entry+h-1
        d[f"exit_date_{h}"] = g["date"].shift(-h)
        d[f"bad_{h}"] = g["bad"].transform(
            lambda s: s.shift(-1).rolling(h, min_periods=1).sum())
        # EW liquid book forward return, same convention (next-open in, h-close out)
        d[f"fwd_open_{h}"] = np.where(
            d.liq, d[f"exit_close_{h}"] / d.entry_open - 1, np.nan)
    # broker attributes joined per row (missing bandar row = data-limited, NaN)
    d = d.merge(
        bd[["ticker", "date", "top1_score", "top3_score", "net_broker_count",
            "broker_accdist"]], on=["ticker", "date"], how="left")
    return d


def cluster_t(x, groups):
    """one-way cluster-robust t of the mean (verbatim fade/panel.py formula),
    clustered on entry dates per spec s3."""
    x = np.asarray(x, float)
    groups = np.asarray(groups)
    n = len(x)
    if n < 3:
        return np.nan, np.nan
    mu = x.mean()
    e = x - mu
    s = pd.Series(e).groupby(groups).sum().values
    G = len(s)
    if G < 3:
        return mu, np.nan
    var = (s ** 2).sum() * (G / (G - 1)) / n ** 2
    if var <= 0:
        return mu, np.nan
    return mu, mu / np.sqrt(var)


def find_events(d):
    """(ticker, shock_idx, marker_idx, frame) per spec s3: first session within
    ABS_WINDOW strictly after the shock whose top1_score >= MARKER_MIN_SCORE."""
    ev, no_marker, no_entry = [], 0, 0
    for tk, x in d.groupby("ticker", sort=False):
        cl, op, dt, ret, vol = (x.close.values, x.open.values, x.date.values,
                                x.ret.values, x.volume.values)
        n, t1 = x.n.values, x.top1_score.values
        N = len(x)
        shocks = np.where((ret >= SHOCK_RET) & (vol > 0) & (cl >= PRICE_FLOOR)
                          & (n >= MIN_SESSIONS) & (dt >= np.datetime64(WINDOW_START)))[0]
        for i in shocks:
            mk = None
            for k in range(1, ABS_WINDOW + 1):
                if i + k >= N:
                    break
                if not np.isnan(t1[i + k]) and t1[i + k] >= MARKER_MIN_SCORE:
                    mk = i + k
                    break
            if mk is None:
                no_marker += 1
                continue
            if mk + 1 >= N or np.isnan(op[mk + 1]):
                no_entry += 1          # data tail: entry not yet printed
                continue
            ev.append((tk, i, mk, x))
    return ev, no_marker, no_entry


def main():
    d, ihsg, bd, vp, splits, unmapped = load()
    if unmapped:
        print(f"NOTE: {unmapped} bandar top1 labels unmapped by the 7-level table")
    d = build(d, bd, splits)
    ewb = {h: d[d.liq].groupby("date")[f"fwd_open_{h}"].mean() for h in HORIZONS}
    ih_o, ih_c = ihsg["open"], ihsg["close"]
    vp_map = vp.set_index(["ticker", "date"])["vpin_label"].to_dict()

    ev, no_marker, no_entry = find_events(d)
    rows, tail_pending_h, voided_h20 = [], 0, 0
    for tk, i, mk, x in ev:
        m_date = pd.Timestamp(x.date.values[mk])
        e_date = pd.Timestamp(x.date.values[mk + 1])
        pre = x.top1_score.values[max(0, i - PRE_WINDOW):i]
        hz = {}
        for h in HORIZONS:
            ec, ed = x[f"exit_close_{h}"].values[mk], x[f"exit_date_{h}"].values[mk]
            bh = x[f"bad_{h}"].values[mk]
            if np.isnan(ec) or np.isnan(bh):
                hz[str(h)] = None
                if h == 20:
                    tail_pending_h += 1
                continue
            if bh != 0:
                hz[str(h)] = "void"
                if h == 20:
                    voided_h20 += 1
                continue
            io, ic = ih_o.get(e_date, np.nan), ih_c.get(pd.Timestamp(ed), np.nan)
            ew = ewb[h].get(m_date, np.nan)
            if pd.isna(io) or pd.isna(ic) or pd.isna(ew):
                hz[str(h)] = None
                continue
            gross = ec / x.open.values[mk + 1] - 1
            net = gross - COST
            ihr = ic / io - 1
            hz[str(h)] = {
                "exit_date": str(pd.Timestamp(ed).date()),
                "gross_return": round(float(gross), 6),
                "net_return": round(float(net), 6),
                "ihsg_return": round(float(ihr), 6),
                "excess_ihsg": round(float(net - ihr), 6),
                "ewbook_return": round(float(ew), 6),
                "excess_ewbook": round(float(net - ew), 6),
            }
        rows.append({
            "ticker": tk,
            "shock_date": str(pd.Timestamp(x.date.values[i]).date()),
            "shock_ret": round(float(x.ret.values[i]), 6),
            "marker_date": str(m_date.date()),
            "entry_date": str(e_date.date()),
            "entry_open": float(x.open.values[mk + 1]),
            "top1_score": float(x.top1_score.values[mk]),
            "top3_score": (None if pd.isna(x.top3_score.values[mk])
                           else float(x.top3_score.values[mk])),
            "net_broker_count": (None if pd.isna(x.net_broker_count.values[mk])
                                 else int(x.net_broker_count.values[mk])),
            "broker_accdist": (None if pd.isna(x.broker_accdist.values[mk])
                               else str(x.broker_accdist.values[mk])),
            "pre_shock_accum": bool((~np.isnan(pre) & (pre >= MARKER_MIN_SCORE)).any()),
            "adv20_bn": (None if pd.isna(x.adv20.values[i])
                         else round(float(x.adv20.values[i]) / 1e9, 3)),
            "vpin_label": vp_map.get((tk, m_date)),
            "horizons": hz,
        })

    df = pd.DataFrame(rows)
    stats = {}
    for h in HORIZONS:
        ok = [r for r in rows if isinstance(r["horizons"].get(str(h)), dict)]
        s = pd.DataFrame([{"e": r["horizons"][str(h)]["excess_ewbook"],
                           "i": r["horizons"][str(h)]["excess_ihsg"],
                           "d": r["entry_date"]} for r in ok])
        mu_e, t_e = cluster_t(s["e"].values, s["d"].values) if len(s) else (np.nan,) * 2
        mu_i, t_i = cluster_t(s["i"].values, s["d"].values) if len(s) else (np.nan,) * 2
        stats[h] = {"N": len(s),
                    "distinct_entry_dates": int(s["d"].nunique()) if len(s) else 0,
                    "exc_ewbook_pct": round(100 * mu_e, 3) if np.isfinite(mu_e) else None,
                    "t_ewbook": round(t_e, 3) if np.isfinite(t_e) else None,
                    "exc_ihsg_pct": round(100 * mu_i, 3) if np.isfinite(mu_i) else None,
                    "t_ihsg": round(t_i, 3) if np.isfinite(t_i) else None}

    h20 = stats[20]
    n_events = len(rows)
    n_dates = int(df["entry_date"].nunique()) if n_events else 0
    alive = (h20["N"] >= 50 and h20["distinct_entry_dates"] >= 20
             and h20["t_ewbook"] is not None and h20["t_ewbook"] >= 2.0)
    verdict = "ALIVE" if alive else ("TOO RARE" if h20["N"] < 50 else "DEAD (null)")

    anchors = df[df["ticker"].isin(["TUGU", "SMMT"])].to_dict("records") \
        if n_events else []
    out = {
        "spec": "FEASIBILITY_SPEC_2026-09-21.md @ cd0cd0a",
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "bar": "h20 N>=50 AND >=20 distinct entry dates AND cluster-t vs EW-book >= +2",
        "n_events_total": n_events,
        "n_entry_dates_total": n_dates,
        "shocks_without_marker": no_marker,
        "events_without_entry_printed": no_entry,
        "h20_tail_pending": tail_pending_h,
        "h20_voided": voided_h20,
        "per_horizon": {str(k): v for k, v in stats.items()},
        "anchors": anchors,
        "events": rows,
    }
    with open(SA / "results_2026-09-21.json", "w") as f:
        json.dump(out, f, indent=1, default=str)

    print(f"VERDICT: {verdict}")
    print(f"events={n_events} (entry dates {n_dates}); shocks w/o marker={no_marker}; "
          f"entry-tail={no_entry}; h20 tail-pending={tail_pending_h} voided={voided_h20}")
    for h in HORIZONS:
        s = stats[h]
        print(f"h={h:2d} N={s['N']:4d} dates={s['distinct_entry_dates']:3d} "
              f"exc_EWb={s['exc_ewbook_pct']}% t={s['t_ewbook']} | "
              f"exc_IHSG={s['exc_ihsg_pct']}% t={s['t_ihsg']}")
    print("anchors:", [(a["ticker"], a["shock_date"], a.get("marker_date")) for a in anchors])


if __name__ == "__main__":
    main()
