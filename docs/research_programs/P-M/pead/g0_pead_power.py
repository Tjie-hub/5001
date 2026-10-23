#!/usr/bin/env python3
"""G0 power check for the PEAD arm (counts, pre-event characteristics and placebo dispersion only).

Implements G0_FREEZE_PEAD_2026-10-23.md, sections "Frozen design", "Distinctness" and "Power method". The
freeze file's sha256 is pinned below and the script refuses to run if it changed. Input hashes (earnings file,
KSEI file, snapshot, pre-2021 panel) are checked against the values pinned here and written to the result.

What it reads and writes:
  * the frozen Yahoo earnings file (dates, consensus EPS, reported EPS);
  * the KSEI month-end market caps (point-in-time universe, later-delisted names included);
  * the price panel from the fingerprinted 2026-09-28 snapshot + the pre-2021 backfill (sanctioned merge),
    used for: session calendar, liquidity, the E-2 close that scales SUE, pre-event characteristics, and
    return DISPERSION in a placebo window [E-70, E-12] that ends before the announcement;
  * it never computes a return inside [E-11, E+60], and never prints or stores the mean of any window;
  * DB opened read-only; writes only into this directory (events CSV + G0_RESULT_<stamp>.json).

Run after the close (it loads the full panel; refuses weekdays 08:30-17:40 WIB unless --force):
    cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
    venv/bin/python3 docs/research_programs/P-M/pead/g0_pead_power.py
Options: --snapshot PATH (default: the 2 TB archive copy), --force, --skip-snapshot-hash (trust SHA256SUMS
next to the snapshot instead of re-hashing 14 GB; recorded in the result).
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from math import erf, log, sqrt
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PM = HERE.parent
BS_DIR = PM / "broad_search"
FREEZE = HERE / "G0_FREEZE_PEAD_2026-10-23.md"
FREEZE_SHA256 = "004fce2757573974cdc6392818c7ad395a69489933574acfd0629ef44a67f237"

# ---- pinned inputs (G0_FREEZE "Frozen inputs") ----
EARN = HERE / "data" / "earnings_dates_pit.json"
EARN_SHA256 = "d07f855ca529facdfe905f4873a4067e3ee7896d2bc1e69678ba4210140a6d78"
KSEI = HERE / "data" / "ksei_mcap_2009_2026.csv"   # date,ticker,sec_num,price from ~/idx_external/ksei (sha 38c8a90b...)
KSEI_SHA256 = "e2c297dc18e7d43fe071b93a080e4d201af5de895439494b7653f8a0c673a6f0"
SNAPSHOT = Path("/mnt/storage2tb/idx-archive/wf_snapshot_20260929/walkforward-20260928-213012.db")
SNAPSHOT_SHA256 = "db48e8d885189680bced5b68899314a460efb568764f39e3bfa99bbebaabc355"   # today's bytes; bs_common's 10f9c97f is the 09-29 hash (freeze 'Snapshot bytes')
HIST_FP = "fd9f54e34f1d7d61300186f760aec943bcfdb5ccf3c39958e7a0462f327c14c9"           # remeasure fetch log

# ---- frozen parameters (G0_FREEZE table) ----
HOLDOUT_FROM = pd.Timestamp("2009-04-01")   # first KSEI month-end is 2009-03-31
ERA_SPLIT = pd.Timestamp("2021-07-05")      # D-070 era split; holdout = [HOLDOUT_FROM, ERA_SPLIT)
CUT = pd.Timestamp("2026-09-16")            # snapshot program cutoff (bs_common.CUT)
CUTOFF_HOUR = 16                            # announcement at/after 16:00 WIB -> next session
TOP_N = 200                                 # KSEI market-cap rank at the last month-end before E-2
DUP_DAYS = 20                               # same ticker within 20 days: keep the first
MIN_QUARTER_EVENTS = 10                     # quarters with fewer eligible events are dropped (counted)
TOP_Q = 0.80                                # top quintile: SUE >= 80th pct within calendar quarter of E
WIN_START, WIN_END = 2, 60                  # outcome returns on sessions [E+2, E+60] (59), G1 only
PLACEBO = (-70, -12)                        # placebo returns on sessions [E-70, E-12] (59)
MIN_COVERAGE = 0.80
FLOOR = 0.020                               # net excess over the 59-session window (literature)
BAR = 3.3001                                # N = 614 at registration; recompute with the census tool
MIN_POWER = 0.20
Z80 = 0.8416
EPS_SPLIT_ADJUST = False                    # DATA_CHECKS C2: 0 of 29 splits (factor >= 2) look unrestated
DISTINCT_FLAG = 0.50
MAX_MCAP_SHARE = 0.25                       # KSEI month-rows above this share of the month total are dropped                        # |Spearman| above this -> G1 must report the controlled increment
WIB = timezone(timedelta(hours=7))


# ---------------------------------------------------------------- pure functions (unit-tested)

def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


def power_one_sided(delta: float, se: float, bar: float) -> float:
    return norm_cdf(abs(delta) / se - bar)


def mde80(se: float, bar: float) -> float:
    return (bar + Z80) * se


def to_wib(ts: str) -> pd.Timestamp:
    return pd.Timestamp(ts).tz_convert("Asia/Jakarta").tz_localize(None)


def event_index(cal: pd.DatetimeIndex, ann_wib: pd.Timestamp) -> int | None:
    """Session index of the event day: the announcement's own session if it is a session and the stamp is
    before 16:00 WIB, else the first session after."""
    d = ann_wib.normalize()
    if ann_wib.hour >= CUTOFF_HOUR:
        d = d + pd.Timedelta(days=1)
    i = int(cal.searchsorted(d))
    return i if i < len(cal) else None


def era_of(e: pd.Timestamp) -> str | None:
    if e < HOLDOUT_FROM or e > CUT:
        return None
    return "holdout" if e < ERA_SPLIT else "recent"


def sue(rep: float, est: float, price: float) -> float | None:
    if price is None or not np.isfinite(price) or price <= 0:
        return None
    return (rep - est) / price


def dedupe(ev: pd.DataFrame, days: int = DUP_DAYS) -> tuple[pd.DataFrame, int]:
    """Keep the first row of any same-ticker run whose gaps are < days (by announcement time)."""
    ev = ev.sort_values(["ticker", "ann_wib"]).reset_index(drop=True)
    keep, last = [], {}
    for i, r in ev.iterrows():
        prev = last.get(r["ticker"])
        if prev is not None and (r["ann_wib"] - prev).days < days:
            keep.append(False)
        else:
            keep.append(True)
            last[r["ticker"]] = r["ann_wib"]
    keep = np.array(keep, dtype=bool)
    return ev[keep].reset_index(drop=True), int((~keep).sum())


def top_quintile(ev: pd.DataFrame) -> tuple[pd.Series, dict]:
    """Top-quintile flag by SUE within each calendar quarter of E. Quarters below MIN_QUARTER_EVENTS are
    dropped (flag NaN). Uses only same-quarter SUEs, all known by the quarter's last event."""
    q = ev["E"].dt.to_period("Q")
    flag = pd.Series(np.nan, index=ev.index)
    dropped = 0
    for _, idx in ev.groupby(q).groups.items():
        s = ev.loc[idx, "sue"]
        if len(s) < MIN_QUARTER_EVENTS:
            dropped += len(s)
            continue
        flag.loc[idx] = (s >= s.quantile(TOP_Q)).astype(float)
    return flag, {"quarters": int(q.nunique()), "events_in_small_quarters": dropped}


def window_excess(r: pd.Series, book: pd.Series, dates: pd.DatetimeIndex) -> float | None:
    rr = r.reindex(dates).dropna()
    if len(rr) < MIN_COVERAGE * len(dates):
        return None
    bb = book.reindex(rr.index).dropna()
    rr = rr.reindex(bb.index)
    if len(rr) < MIN_COVERAGE * len(dates):
        return None
    return float(np.prod(1.0 + rr.values) - np.prod(1.0 + bb.values))


def cluster_se(values: pd.Series, months: pd.Series) -> tuple[float, int]:
    x = pd.Series(values.values, index=months.values).groupby(level=0).mean()
    m = len(x)
    if m < 3:
        return float("nan"), m
    return float(x.std(ddof=1) / sqrt(m)), m


def g0_stats(placebo: pd.Series, months: pd.Series) -> dict:
    se, m = cluster_se(placebo, months)
    pw = power_one_sided(FLOOR, se, BAR)
    return {"events_with_placebo": int(len(placebo)), "months": m,
            "placebo_event_sd": float(placebo.std(ddof=1)) if len(placebo) > 1 else None,
            "se": se, "mde80": mde80(se, BAR), "power_at_floor": pw,
            "stop_rule_fired": bool(not (pw >= MIN_POWER))}


def ksei_rank_asof(ksei: pd.DataFrame, ticker: str, before: pd.Timestamp) -> tuple[float | None, float | None]:
    """Rank and market cap at the last month-end strictly before `before` (a month-end file is known from the
    next session at the earliest; requiring the file date < the E-2 session satisfies that)."""
    g = ksei[(ksei["ticker"] == ticker) & (ksei["date"] < before)]
    if g.empty:
        return None, None
    last = g.iloc[-1]
    return float(last["rk"]), float(last["mcap"])


def t1_state(close: pd.Series) -> pd.Series:
    """HYP-PM-0010 trend state (EMA20 slope over 10 > 2%, ER20 >= 0.30, >= 70% of last 20 closes above EMA20)."""
    ema = close.ewm(span=20, adjust=False).mean()
    slope = ema / ema.shift(10) - 1.0
    er = (close - close.shift(20)).abs() / close.diff().abs().rolling(20).sum()
    above = (close > ema).astype(float).rolling(20).mean()
    return (slope > 0.02) & (er >= 0.30) & (above >= 0.70)


def parkinson60(high: pd.Series, low: pd.Series) -> pd.Series:
    x = np.log(high / low) ** 2
    return np.sqrt(x.rolling(60, min_periods=50).mean() / (4.0 * log(2.0)))


def hi52(close: pd.Series, high: pd.Series) -> pd.Series:
    return close / high.rolling(252, min_periods=200).max()


# ---------------------------------------------------------------- repo integration

def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def load_ksei() -> pd.DataFrame:
    k = pd.read_csv(KSEI, usecols=["date", "ticker", "sec_num", "price"])
    k["date"] = pd.to_datetime(k["date"])
    k["mcap"] = k["sec_num"] * k["price"]
    k = k[k["mcap"] <= MAX_MCAP_SHARE * k.groupby("date")["mcap"].transform("sum")]   # BCIC 2010-17 error
    k["rk"] = k.groupby("date")["mcap"].rank(ascending=False, method="first")
    return k.sort_values(["ticker", "date"]).reset_index(drop=True)


def raw_events(earn: dict) -> pd.DataFrame:
    rows = [{"ticker": t, "ann_wib": to_wib(r["ts"]), "est": r.get("est"), "rep": r.get("rep")}
            for t, v in earn.items() if isinstance(v, list) for r in v]
    return pd.DataFrame(rows, columns=["ticker", "ann_wib", "est", "rep"])


def build_panel(snapshot: Path):
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(BS_DIR))
    B = _load("bs_common", BS_DIR / "bs_common.py")
    B.SNAP = snapshot
    from research.rulecard import engine, events
    P_raw, load_audit = B.load_panel()
    hist_fp = hashlib.sha256(pd.util.hash_pandas_object(
        pd.read_pickle(PM / "forward_volex" / "remeasure" / "work" / "hist_pre2021.pkl"),
        index=False).values.tobytes()).hexdigest()
    ca = B.parse_ca_events(B.CORR_TYPES)
    P, corr_audit = B.wealth_correct(P_raw, ca)
    pan = engine.Panel(P)
    book, _ = events._book(pan)
    book = pd.Series(np.asarray(book.values, dtype=float), index=pd.to_datetime(book.index))
    audit = {"load": load_audit, "corrections_applied": len(corr_audit["applied"]),
             "non_sessions_dropped": len(pan.non_sessions_dropped), "hist_fingerprint": hist_fp}
    return pan, book, audit


def characteristics(pan) -> pd.DataFrame:
    """Per (ticker, date) pre-event characteristics, trailing only."""
    P = pan.P
    g = P.groupby("ticker", sort=False)
    C = pd.DataFrame({"ticker": P["ticker"], "date": pd.to_datetime(P["date"]), "close": P["close"],
                      "eligible": pan.eligible.values})
    C["hi52"] = g.apply(lambda d: hi52(d["close"], d["high"])).reset_index(level=0, drop=True)
    C["park60"] = g.apply(lambda d: parkinson60(d["high"], d["low"])).reset_index(level=0, drop=True)
    C["t1"] = g["close"].transform(lambda s: t1_state(s).astype(float))
    for col in ("hi52", "park60"):
        C[col + "_pct"] = C.groupby("date")[col].rank(pct=True).where(C["eligible"])
    return C


def build_events(earn: dict, ksei: pd.DataFrame, cal: pd.DatetimeIndex, C: pd.DataFrame):
    counts = {}
    ev = raw_events(earn)
    counts["rows"] = len(ev)
    ev = ev.dropna(subset=["est", "rep"])
    counts["usable_est_rep"] = len(ev)
    ev, counts["duplicates_dropped"] = dedupe(ev)
    idx = ev["ann_wib"].map(lambda a: event_index(cal, a))
    ev = ev[idx.notna()].assign(e_i=idx[idx.notna()].astype(int))
    ev["E"] = cal[ev["e_i"].values]
    ev["era"] = ev["E"].map(era_of)
    counts["outside_eras"] = int(ev["era"].isna().sum())
    ev = ev[ev["era"].notna() & (ev["e_i"] >= -PLACEBO[0])].copy()
    ev["d_e2"] = cal[ev["e_i"].values - 2]
    key = C.set_index(["ticker", "date"])
    look = key.reindex(pd.MultiIndex.from_arrays([ev["ticker"], ev["d_e2"]]))
    for col in ("close", "eligible", "hi52", "park60", "hi52_pct", "park60_pct", "t1"):
        ev[col] = look[col].values
    rk = [ksei_rank_asof(ksei, t, d) for t, d in zip(ev["ticker"], ev["d_e2"])]
    ev["ksei_rank"] = [r[0] for r in rk]
    ev["log_mcap"] = [np.log(r[1]) if r[1] else np.nan for r in rk]
    in_top = ev["ksei_rank"].notna() & (ev["ksei_rank"] <= TOP_N)
    liquid = ev["eligible"].fillna(False).astype(bool)
    counts["not_top200_at_E-2"] = int((~in_top).sum())
    counts["not_liquid_at_E-2"] = int((in_top & ~liquid).sum())
    ev = ev[in_top & liquid].copy()
    ev["sue"] = [sue(r, e, p) for r, e, p in zip(ev["rep"], ev["est"], ev["close"])]
    counts["no_price_at_E-2"] = int(ev["sue"].isna().sum())
    ev = ev[ev["sue"].notna()].copy()
    ev["top_q"], qa = top_quintile(ev)
    counts.update(qa)
    counts["eligible_events"] = int(ev["top_q"].notna().sum())
    counts["top_quintile_events"] = int((ev["top_q"] == 1).sum())
    counts["by_era"] = {e: {"eligible": int(((ev["era"] == e) & ev["top_q"].notna()).sum()),
                            "top_q": int(((ev["era"] == e) & (ev["top_q"] == 1)).sum())}
                        for e in ("holdout", "recent")}
    nxt = ev.sort_values(["ticker", "e_i"]).groupby("ticker")["e_i"].shift(-1)
    ev["next_inside_window"] = (nxt.reindex(ev.index) - ev["e_i"]).le(WIN_END)
    counts["matured_by_cut"] = int((ev["e_i"] + WIN_END < len(cal)).sum())
    return ev.reset_index(drop=True), counts


def distinctness(ev: pd.DataFrame) -> dict:
    el = ev[ev["top_q"].notna()]
    top = el[el["top_q"] == 1]
    out = {}
    for col in ("hi52", "park60", "log_mcap", "t1"):
        sp = el[["sue", col]].dropna().corr(method="spearman").iloc[0, 1]
        out[col] = {"spearman_with_sue": float(sp), "flag": bool(abs(sp) > DISTINCT_FLAG)}
    out["share_top_q_in_hi52_top20"] = float((top["hi52_pct"] >= 0.80).mean())
    out["share_all_in_hi52_top20"] = float((el["hi52_pct"] >= 0.80).mean())
    out["share_top_q_in_park60_top10"] = float((top["park60_pct"] >= 0.90).mean())
    out["share_all_in_park60_top10"] = float((el["park60_pct"] >= 0.90).mean())
    out["share_top_q_in_t1"] = float(top["t1"].mean())
    out["share_all_in_t1"] = float(el["t1"].mean())
    out["share_top_q_next_event_inside_window"] = float(top["next_inside_window"].mean())
    return out


def placebo_values(ev: pd.DataFrame, cal: pd.DatetimeIndex, pan, book: pd.Series):
    top = ev[ev["top_q"] == 1]
    rets = pan.ret_w
    vals, months, eras, short = [], [], [], 0
    for _, r in top.iterrows():
        a, b = r["e_i"] + PLACEBO[0], r["e_i"] + PLACEBO[1]
        dates = cal[a:b + 1]
        s = rets[r["ticker"]] if r["ticker"] in rets.columns else pd.Series(dtype=float)
        v = window_excess(s, book, dates)
        if v is None:
            short += 1
            continue
        vals.append(v)
        months.append(r["E"].to_period("M"))
        eras.append(r["era"])
    return pd.Series(vals, dtype=float), pd.Series(months), pd.Series(eras), short


def in_blackout(now: datetime) -> bool:
    hm = now.hour * 60 + now.minute
    return now.weekday() < 5 and 8 * 60 + 30 <= hm < 17 * 60 + 40


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", default=str(SNAPSHOT))
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--skip-snapshot-hash", action="store_true")
    a = ap.parse_args(argv)

    sha = hashlib.sha256(FREEZE.read_bytes()).hexdigest()
    if sha != FREEZE_SHA256:
        print(f"REFUSED: {FREEZE.name} sha256 {sha[:12]} != pinned {FREEZE_SHA256[:12]}. The freeze changed.")
        return 2
    for p, pinned in ((EARN, EARN_SHA256), (KSEI, KSEI_SHA256)):
        got = sha256_file(p)
        if got != pinned:
            print(f"REFUSED: {p.name} sha256 {got[:12]} != pinned {pinned[:12]}.")
            return 2
    snap = Path(a.snapshot)
    if a.skip_snapshot_hash:
        sums = (snap.parent / "SHA256SUMS").read_text()
        snap_check = "SHA256SUMS" if SNAPSHOT_SHA256 in sums else "MISMATCH"
    else:
        snap_check = "rehashed" if sha256_file(snap) == SNAPSHOT_SHA256 else "MISMATCH"
    if snap_check == "MISMATCH":
        print("REFUSED: snapshot hash does not match the pinned SNAPSHOT_SHA256.")
        return 2
    now = datetime.now(WIB)
    if in_blackout(now) and not a.force:
        print(f"REFUSED: {now:%a %H:%M} WIB is inside 08:30-17:40 (full panel load). Run after 17:40 or --force.")
        return 2
    if EPS_SPLIT_ADJUST is None:
        print("REFUSED: EPS_SPLIT_ADJUST not set; the freeze must record the C2 decision first.")
        return 2

    st0 = snap.stat()
    pan, book, audit = build_panel(snap)
    st1 = snap.stat()
    if (st0.st_size, st0.st_mtime_ns) != (st1.st_size, st1.st_mtime_ns):
        # the 09-29 -> 10-13 byte drift of this file is why this is checked (G0_FREEZE "Frozen inputs")
        print("REFUSED: the snapshot file changed during the read; nothing is reported.")
        return 2
    audit["panel_content_sha256"] = hashlib.sha256(pd.util.hash_pandas_object(
        pan.P[["ticker", "date", "open", "high", "low", "close", "volume"]], index=False).values.tobytes()).hexdigest()
    if audit["hist_fingerprint"] != HIST_FP:
        print(f"REFUSED: pre-2021 panel fingerprint {audit['hist_fingerprint'][:12]} != pinned {HIST_FP[:12]}.")
        return 2
    cal = pd.DatetimeIndex(np.sort(pd.to_datetime(pan.P["date"]).unique()))
    C = characteristics(pan)
    ev, counts = build_events(json.loads(EARN.read_text()), load_ksei(), cal, C)
    dist = distinctness(ev)
    vals, months, eras, short = placebo_values(ev, cal, pan, book)
    counts["placebo_low_coverage"] = short

    stats = {"pooled": g0_stats(vals, months)}
    for e in ("holdout", "recent"):
        m = eras == e
        stats[e] = g0_stats(vals[m.values].reset_index(drop=True), months[m.values].reset_index(drop=True))

    stamp = now.strftime("%Y%m%dT%H%M%S")
    cols = ["ticker", "ann_wib", "E", "era", "est", "rep", "close", "sue", "top_q", "ksei_rank", "log_mcap",
            "hi52", "park60", "t1", "next_inside_window"]
    ev[cols].to_csv(HERE / f"events_pead_{stamp}.csv", index=False, date_format="%Y-%m-%d %H:%M")
    events_sha = sha256_file(HERE / f"events_pead_{stamp}.csv")
    result = {"record_type": "g0_power", "arm": "PEAD long top-SUE quintile", "freeze_sha256": sha,
              "script_sha256": sha256_file(Path(__file__)), "inputs": {
                  "earnings_sha256": EARN_SHA256, "ksei_sha256": KSEI_SHA256, "snapshot": str(snap),
                  "snapshot_sha256": SNAPSHOT_SHA256, "snapshot_check": snap_check, "hist_fingerprint": HIST_FP},
              "events_csv_sha256": events_sha, "run_wib": now.isoformat(), "counts": counts, "audit": audit,
              "frozen": {"floor": FLOOR, "bar": BAR, "min_power": MIN_POWER, "window": [WIN_START, WIN_END],
                         "placebo": list(PLACEBO), "top_n": TOP_N, "top_q": TOP_Q,
                         "eps_split_adjust": EPS_SPLIT_ADJUST},
              "distinctness": dist, "g0": stats}
    (HERE / f"G0_RESULT_{stamp}.json").write_text(json.dumps(result, indent=1, default=str))

    p = stats["pooled"]
    print(f"events: {json.dumps(counts)}")
    print(f"distinctness: {json.dumps(dist)}")
    print(f"placebo events {p['events_with_placebo']} over {p['months']} months; per-event sd "
          f"{p['placebo_event_sd']:.4f}; SE {p['se']:.4%}; MDE80 {p['mde80']:.2%}; "
          f"power at {FLOOR:.1%} floor = {p['power_at_floor']:.1%}")
    for e in ("holdout", "recent"):
        s = stats[e]
        print(f"  {e}: n {s['events_with_placebo']} months {s['months']} SE {s['se']:.4%} "
              f"power {s['power_at_floor']:.1%} (reported, not the stop metric)")
    print("STOP RULE FIRED -> withdraw before registration (uncounted)." if p["stop_rule_fired"] else
          "Stop rule NOT fired -> owner: mechanism D-entry + registration (HYP-PM-0023), then one G1 run.")
    print(f"files: events_pead_{stamp}.csv, G0_RESULT_{stamp}.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
