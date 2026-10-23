#!/usr/bin/env python3
"""PEAD G0 data checks on the frozen earnings file (EPS and dates only; no price or return is read).

Checks (gap 6 of the 2026-10-23 completeness review):
  C1 EPS basis    IDX statements are cumulative year-to-date. If Yahoo's reported EPS were YTD while the
                  consensus were single-quarter (or the reverse), rep/est would climb ~1, 2, 3, 4 across
                  Q1, H1, 9M, FY. Report median rep/est and median |rep| relative to the same ticker-year's
                  Q1, by inferred fiscal period.
  C2 split units  For tickers with a split in split_hist.pkl, median |EPS| in the 4 events before vs the 4
                  after. Ratio ~ split factor => EPS history is NOT restated to the current share basis;
                  ratio ~ 1 => it is (consistent with the split-adjusted price panel).
  C3 duplicates   Same ticker, two rows within 20 calendar days.
  C4 consensus    Share of rows with est missing, rep missing, and est == rep exactly (a revised-to-actual
                  consensus would show up as a spike of exact matches).
  C5 coverage     Per year, share of the KSEI point-in-time top-200 (by count and by market cap) with at
                  least one usable event (est and rep present) in that year.

Writes DATA_CHECKS_<stamp>.json in this directory and prints a summary.
    venv/bin/python3 docs/research_programs/P-M/pead/pead_data_checks.py
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PM = HERE.parent
EARN = HERE / "data" / "earnings_dates_pit.json"
KSEI = HERE / "data" / "ksei_mcap_2009_2026.csv"
SPLITS = PM / "data_gaps" / "data" / "split_hist.pkl"
WIB = timezone(timedelta(hours=7))
TOP_N = 200
DUP_DAYS = 20
MAX_MCAP_SHARE = 0.25   # a month-row worth >25% of that month's total is a KSEI data error (BCIC 2010-17)


# ---------------------------------------------------------------- pure functions (unit-tested)

def to_wib(ts: str) -> pd.Timestamp:
    return pd.Timestamp(ts).tz_convert("Asia/Jakarta").tz_localize(None)


def fiscal_period(ann: pd.Timestamp) -> tuple[int, str]:
    """Inferred calendar-year fiscal period from the announcement month (WIB).

    Jan-Mar -> FY of the prior year; Apr-Jun -> Q1; Jul-Sep -> H1; Oct-Dec -> 9M. Late FY filers in April
    land in Q1; the share is small and only blurs C1 toward 1, never manufactures a YTD pattern.
    """
    m = ann.month
    if m <= 3:
        return ann.year - 1, "FY"
    return ann.year, ("Q1" if m <= 6 else "H1" if m <= 9 else "9M")


def events_frame(earn: dict) -> pd.DataFrame:
    rows = []
    for t, v in earn.items():
        if not isinstance(v, list):
            continue
        for r in v:
            ann = to_wib(r["ts"])
            fy, per = fiscal_period(ann)
            rows.append({"ticker": t, "ann_wib": ann, "fy": fy, "period": per,
                         "est": r.get("est"), "rep": r.get("rep")})
    E = pd.DataFrame(rows, columns=["ticker", "ann_wib", "fy", "period", "est", "rep"])
    return E.sort_values(["ticker", "ann_wib"]).reset_index(drop=True)


def basis_check(E: pd.DataFrame) -> dict:
    ok = E.dropna(subset=["est", "rep"])
    pos = ok[(ok["est"] > 0) & (ok["rep"] > 0)]
    ratio = (pos["rep"] / pos["est"]).groupby(pos["period"]).median()
    q1 = ok[ok["period"] == "Q1"].groupby(["ticker", "fy"])["rep"].apply(lambda s: s.abs().median())
    rel = {}
    for per in ("Q1", "H1", "9M", "FY"):
        x = ok[ok["period"] == per].groupby(["ticker", "fy"])["rep"].apply(lambda s: s.abs().median())
        j = pd.concat([x.rename("x"), q1.rename("q1")], axis=1).dropna()
        j = j[j["q1"] > 0]
        rel[per] = float((j["x"] / j["q1"]).median()) if len(j) else None
    return {"median_rep_over_est": {k: float(v) for k, v in ratio.items()},
            "median_abs_rep_vs_same_year_Q1": rel,
            "n_positive_pairs": int(len(pos))}


def split_check(E: pd.DataFrame, splits: pd.DataFrame, k: int = 4) -> dict:
    out = []
    for _, s in splits.iterrows():
        g = E[(E["ticker"] == s["ticker"])].dropna(subset=["rep"])
        if g.empty:
            continue
        d = pd.Timestamp(s["date"])
        pre, post = g[g["ann_wib"] < d].tail(k), g[g["ann_wib"] >= d].head(k)
        if len(pre) < 2 or len(post) < 2:
            continue
        a, b = pre["rep"].abs().median(), post["rep"].abs().median()
        if a > 0 and b > 0:
            out.append({"ticker": s["ticker"], "date": str(d.date()), "factor": float(s["ratio"]),
                        "pre_over_post": float(a / b)})
    if not out:
        return {"n": 0}
    df = pd.DataFrame(out)
    big = df[df["factor"] >= 2]
    # restated -> pre/post ~ 1 regardless of factor; unrestated -> pre/post ~ factor
    lr, lf = np.log(big["pre_over_post"]), np.log(big["factor"])
    near_one = (lr.abs() < lf / 2).mean() if len(big) else None
    # unrestated history: pre/post within a factor of sqrt(split) of the split factor itself
    unrestated = ((lr - lf).abs() < lf / 2).mean() if len(big) else None
    return {"n": int(len(df)), "n_factor_ge2": int(len(big)),
            "share_factor_ge2_closer_to_1_than_factor": None if near_one is None else float(near_one),
            "share_factor_ge2_like_unrestated": None if unrestated is None else float(unrestated),
            "cases": out}


def duplicate_check(E: pd.DataFrame, days: int = DUP_DAYS) -> dict:
    g = E.groupby("ticker")["ann_wib"].diff().dt.days
    dup = E[g.notna() & (g < days)]
    return {"rows_within_days_of_previous": int(len(dup)), "days": days,
            "examples": dup.head(10).assign(ann_wib=dup["ann_wib"].astype(str).head(10)).to_dict("records")}


def consensus_check(E: pd.DataFrame) -> dict:
    n = len(E)
    both = E.dropna(subset=["est", "rep"])
    return {"rows": n, "est_missing": int(E["est"].isna().sum()), "rep_missing": int(E["rep"].isna().sum()),
            "usable": int(len(both)), "est_equals_rep": int((both["est"] == both["rep"]).sum()),
            "est_equals_rep_share": float((both["est"] == both["rep"]).mean()) if len(both) else None}


def ksei_top(ksei_csv: Path = KSEI, top_n: int = TOP_N) -> pd.DataFrame:
    k = pd.read_csv(ksei_csv, usecols=["date", "ticker", "sec_num", "price"])
    k["mcap"] = k["sec_num"] * k["price"]
    k = k[k["mcap"] <= MAX_MCAP_SHARE * k.groupby("date")["mcap"].transform("sum")]
    k["rk"] = k.groupby("date")["mcap"].rank(ascending=False, method="first")
    return k[k["rk"] <= top_n]


def coverage_check(E: pd.DataFrame, top: pd.DataFrame) -> dict:
    use = E.dropna(subset=["est", "rep"])
    have = use.assign(year=use["ann_wib"].dt.year).groupby("year")["ticker"].apply(set).to_dict()
    out = {}
    for y, t in top.assign(year=top["date"].str[:4].astype(int)).groupby("year"):
        last = t[t["date"] == t["date"].max()]
        cov = last["ticker"].isin(have.get(y, set()))
        out[int(y)] = {"names": float(cov.mean()), "mcap": float(last["mcap"][cov].sum() / last["mcap"].sum())}
    return out


def main() -> int:
    earn_bytes = EARN.read_bytes()
    earn = json.loads(earn_bytes)
    E = events_frame(earn)
    status = {"tickers": len(earn), "with_rows": sum(isinstance(v, list) and len(v) > 0 for v in earn.values()),
              "empty": sum(isinstance(v, list) and len(v) == 0 for v in earn.values()),
              "error": sum(isinstance(v, dict) for v in earn.values())}
    res = {"record_type": "pead_data_checks", "earnings_sha256": hashlib.sha256(earn_bytes).hexdigest(),
           "ksei_sha256": hashlib.sha256(KSEI.read_bytes()).hexdigest(),
           "run_wib": datetime.now(WIB).isoformat(), "fetch_status": status,
           "C1_basis": basis_check(E),
           "C2_split": split_check(E, pd.read_pickle(SPLITS)),
           "C3_duplicates": duplicate_check(E),
           "C4_consensus": consensus_check(E),
           "C5_coverage": coverage_check(E, ksei_top())}
    stamp = datetime.now(WIB).strftime("%Y%m%dT%H%M%S")
    (HERE / f"DATA_CHECKS_{stamp}.json").write_text(json.dumps(res, indent=1, default=str))
    s = {k: v for k, v in res["C2_split"].items() if k != "cases"}
    print(json.dumps({k: res[k] for k in ("fetch_status", "C1_basis", "C4_consensus")}, indent=1))
    print("C2", s)
    print("C3", {k: v for k, v in res["C3_duplicates"].items() if k != "examples"})
    print("C5", json.dumps(res["C5_coverage"]))
    print(f"file DATA_CHECKS_{stamp}.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
