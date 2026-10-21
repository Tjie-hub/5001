#!/usr/bin/env python3
"""G0 power check for the {LC} lock-up-expiry arm (counts + pre-event dispersion only).

Implements G0_FREEZE_LC_LOCKUP_2026-10-20.md section "Power method". The freeze file's sha256 is pinned
below; the script refuses to run if it changed.

What it reads and writes:
  * the SCREEN-PM-LC-001 cohort, rebuilt with the frozen S2 code (bs_common + screen_s2_listings);
  * return DISPERSION in a placebo window [E-52, E-27] that ends before the event window;
  * it never computes event-window returns, and never prints or stores the mean of any window;
  * DB opened read-only; writes only into this directory (cohort CSV + G0_RESULT_<stamp>.json).

Run after the close (it loads the full panel; refuses weekdays 08:30-17:40 WIB unless --force):
    cd "/home/tjiesar/10 Projects/idx-walkforward-5001"
    venv/bin/python3 docs/research_programs/P-M/lockup_lc/g0_lockup_power.py
Options: --db PATH (default data/walkforward.db; or the archived S2 snapshot), --force.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from math import erf, sqrt
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BS_DIR = HERE.parent / "broad_search"
FREEZE = HERE / "G0_FREEZE_LC_LOCKUP_2026-10-20.md"
FREEZE_SHA256 = "03b40527fc136c006e7fae25911c3cdea5cf13bbe873eb733b84470f46811f7e"

# ---- frozen parameters (G0_FREEZE table) ----
FIRST_FROM = pd.Timestamp("2015-01-01")
LIST_TO = pd.Timestamp("2026-09-16")
EFFECTIVE_LAG_SESSIONS = 8
LOCKUP_MONTHS = 8
WIN_PRE, WIN_POST = 5, 20            # event window returns on sessions [E-5, E+20]
WIN_LEN = WIN_PRE + WIN_POST + 1     # 26
PLACEBO_END = 27                     # placebo window = [E-52, E-27]
MIN_COVERAGE = 0.80                  # share of window sessions the name must trade
FLOOR = 0.020
LOCK_SHARE = 0.60
BAR = 3.3001                         # N = 614 at registration; recompute with the census tool
MIN_POWER = 0.20
Z80 = 0.8416
WIB = timezone(timedelta(hours=7))


# ---------------------------------------------------------------- pure functions (unit-tested)

def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


def power_one_sided(delta: float, se: float, bar: float) -> float:
    return norm_cdf(abs(delta) / se - bar)


def mde80(se: float, bar: float) -> float:
    return (bar + Z80) * se


def expiry_index(cal: pd.DatetimeIndex, first_bar: pd.Timestamp) -> int | None:
    """Session index of the estimated expiry: (first bar - 8 sessions) + 8 months, next session on/after."""
    li = int(cal.searchsorted(first_bar))
    if li >= len(cal):
        return None
    eff = cal[max(li - EFFECTIVE_LAG_SESSIONS, 0)]
    e = int(cal.searchsorted(eff + pd.DateOffset(months=LOCKUP_MONTHS)))
    return e if e < len(cal) else None


def window_excess(r: pd.Series, book: pd.Series, dates: pd.DatetimeIndex) -> float | None:
    """Compounded name return minus compounded book return over the sessions the name traded."""
    rr = r.reindex(dates).dropna()
    if len(rr) < MIN_COVERAGE * len(dates):
        return None
    bb = book.reindex(rr.index).dropna()
    rr = rr.reindex(bb.index)
    if len(rr) < MIN_COVERAGE * len(dates):
        return None
    return float(np.prod(1.0 + rr.values) - np.prod(1.0 + bb.values))


def cluster_se(values: pd.Series, months: pd.Series) -> tuple[float, int]:
    """SE of the mean of monthly cluster means (months with >= 1 value)."""
    x = pd.Series(values.values, index=months.values).groupby(level=0).mean()
    m = len(x)
    if m < 3:
        return float("nan"), m
    return float(x.std(ddof=1) / sqrt(m)), m


def g0_stats(placebo: pd.Series, months: pd.Series) -> dict:
    se_full, m = cluster_se(placebo, months)
    se_lock = se_full / sqrt(LOCK_SHARE)
    pw = power_one_sided(FLOOR, se_lock, BAR)
    return {"events_with_placebo": int(len(placebo)), "expiry_months": m,
            "placebo_event_sd": float(placebo.std(ddof=1)) if len(placebo) > 1 else None,
            "se_full": se_full, "se_lock": se_lock, "mde80_lock": mde80(se_lock, BAR),
            "power_at_floor": pw, "stop_rule_fired": bool(not (pw >= MIN_POWER))}


# ---------------------------------------------------------------- repo integration

def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def build_inputs(db: Path):
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(BS_DIR))
    B = _load("bs_common", BS_DIR / "bs_common.py")
    B.SNAP = db
    B.CUT = pd.Timestamp(datetime.now(WIB).date())          # panel to today; the cohort keeps LIST_TO
    S2 = _load("screen_s2_listings", BS_DIR / "screen_s2_listings.py")
    from research.rulecard import engine, events

    P_raw, load_audit = B.load_panel()
    firsts = S2.first_bars(P_raw)
    starts = {pd.Timestamp(P_raw["date"].min()), B.SPLIT_DATE}
    listed = set(firsts[(firsts["first_bar"] >= FIRST_FROM) & (firsts["first_bar"] <= LIST_TO)
                        & (~firsts["first_bar"].isin(starts))]["ticker"])
    ca = B.parse_ca_events(("rightissue", "bonus", "stock_reverse"))
    P, corr_audit = B.wealth_correct(P_raw, ca)
    pan = engine.Panel(P)
    flags, counted, got = S2.build_flags(pan, listed)

    PP = pan.P
    flag_rows = PP.loc[flags > 0, ["ticker", "date"]].rename(columns={"date": "flag_date"})
    adv = pd.Series(pan.F["adv20"].values, index=PP.index).loc[flag_rows.index] / 1e9
    cohort = (flag_rows.assign(adv20_bn=adv.values)
              .merge(firsts, on="ticker", how="left")
              .sort_values("first_bar").reset_index(drop=True))

    cal = pd.DatetimeIndex(np.sort(pd.to_datetime(PP["date"]).unique()))
    book, _ = events._book(pan)
    book = pd.Series(np.asarray(book.values, dtype=float), index=pd.to_datetime(book.index))
    PS = PP.sort_values(["ticker", "date"])
    ret = PS.groupby("ticker", sort=False)["close"].pct_change()
    rets = {t: pd.Series(ret.loc[g.index].values, index=pd.to_datetime(g["date"].values))
            for t, g in PS[PS["ticker"].isin(set(cohort["ticker"]))].groupby("ticker", sort=False)}
    audit = {"load": load_audit, "flag_counts": counted, "listed": len(listed),
             "corrections_applied": len(corr_audit["applied"])}
    return cohort, cal, book, rets, audit


def placebo_values(cohort: pd.DataFrame, cal: pd.DatetimeIndex, book: pd.Series, rets: dict):
    vals, months, counts = [], [], {"expiry_beyond_data": 0, "event_window_incomplete": 0,
                                   "placebo_before_flag": 0, "placebo_low_coverage": 0}
    exp_dates = []
    for _, row in cohort.iterrows():
        e = expiry_index(cal, pd.Timestamp(row["first_bar"]))
        exp_dates.append(cal[e] if e is not None else pd.NaT)
        if e is None:
            counts["expiry_beyond_data"] += 1
            continue
        if e + WIN_POST >= len(cal):
            counts["event_window_incomplete"] += 1      # not yet matured; dates only, nothing read
            continue
        p_end, p_start = e - PLACEBO_END, e - PLACEBO_END - WIN_LEN + 1
        if p_start < 0 or cal[p_start] <= pd.Timestamp(row["flag_date"]):
            counts["placebo_before_flag"] += 1
            continue
        v = window_excess(rets.get(row["ticker"], pd.Series(dtype=float)), book, cal[p_start:p_end + 1])
        if v is None:
            counts["placebo_low_coverage"] += 1
            continue
        vals.append(v)
        months.append(cal[e].to_period("M"))
    return pd.Series(vals, dtype=float), pd.Series(months), counts, exp_dates


def in_blackout(now: datetime) -> bool:
    hm = now.hour * 60 + now.minute
    return now.weekday() < 5 and 8 * 60 + 30 <= hm < 17 * 60 + 40


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(ROOT / "data" / "walkforward.db"))
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)

    sha = hashlib.sha256(FREEZE.read_bytes()).hexdigest()
    if sha != FREEZE_SHA256:
        print(f"REFUSED: {FREEZE.name} sha256 {sha[:12]} != pinned {FREEZE_SHA256[:12]}. The freeze changed.")
        return 2
    now = datetime.now(WIB)
    if in_blackout(now) and not a.force:
        print(f"REFUSED: {now:%a %H:%M} WIB is inside 08:30-17:40 (full panel load on the production box). "
              "Run after 17:40 or pass --force.")
        return 2

    cohort, cal, book, rets, audit = build_inputs(Path(a.db))
    vals, months, counts, exp_dates = placebo_values(cohort, cal, book, rets)
    cohort = cohort.assign(expiry_est=exp_dates)
    stamp = now.strftime("%Y%m%dT%H%M%S")
    cohort[["ticker", "first_bar", "flag_date", "adv20_bn", "expiry_est"]].to_csv(
        HERE / f"cohort_lc_{stamp}.csv", index=False, date_format="%Y-%m-%d")

    stats = g0_stats(vals, months)
    result = {"record_type": "g0_power", "arm": "{LC} lock-up expiry", "freeze_sha256": sha,
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "db": a.db, "run_wib": now.isoformat(), "cohort": int(len(cohort)), "exclusions": counts,
              "audit": audit, "frozen": {"floor": FLOOR, "lock_share": LOCK_SHARE, "bar": BAR,
                                         "min_power": MIN_POWER, "window": [-WIN_PRE, WIN_POST],
                                         "placebo": [-(PLACEBO_END + WIN_LEN - 1), -PLACEBO_END]},
              "g0": stats}
    (HERE / f"G0_RESULT_{stamp}.json").write_text(json.dumps(result, indent=1, default=str))

    print(f"cohort {len(cohort)} (S2 had 226) | exclusions {counts}")
    print(f"placebo events {stats['events_with_placebo']} over {stats['expiry_months']} expiry months; "
          f"per-event sd {stats['placebo_event_sd']:.4f}")
    print(f"SE_full {stats['se_full']:.4%}  SE_lock(x1/sqrt {LOCK_SHARE}) {stats['se_lock']:.4%}  "
          f"MDE80 {stats['mde80_lock']:.2%}  power at {FLOOR:.1%} floor = {stats['power_at_floor']:.1%}")
    print("STOP RULE FIRED -> withdraw before registration (uncounted); do not source lock-ups."
          if stats["stop_rule_fired"] else
          "Stop rule NOT fired -> owner: source lock-up flags for the cohort, then registration + G1.")
    print(f"files: cohort_lc_{stamp}.csv, G0_RESULT_{stamp}.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
