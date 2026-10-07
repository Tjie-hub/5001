"""Structural-event feasibility census — counts, PIT dates and power ONLY.

Rule 1 of ZCODE_BRIEF_STRUCTURAL_EVENTS_FEASIBILITY_2026-10-07.md: **NO
post-event price of any kind is read.** Every price query in this script
filters `date < decision_date` (strictly before), so no row on or after any
event's decision date is ever touched — not for outcomes, not for anything
else. Power comes from pre-event volatility only (the daily-return std over
the 60 sessions ENDING the day before the decision date).

Read-only DB (mode=ro). No network. Decision dates are DECLARED per class
(the scheduled public date each class offers, per the brief's rule that an
event without a stored announcement date is usable only when a later date is
itself public in advance):

  A tenderoffer  -> tender_start           (the offer window opens; public)
  B idx80 recon  -> effective_from         (announced ~1 week ahead; see notes)
  C rightissue   -> rightissue_cumdate     (scheduled cum date, public in advance)
  D dividend     -> dividend_cumdate       (scheduled cum date, public in advance)
  E split/bonus/ -> stocksplit_cumdate     (scheduled cum date, public in advance)
    reverse
  F warrant      -> wrant_trading_from     (scheduled trading window start)

RUPS (6,727) are out of scope (no named forced-flow mechanism). Ownership
composition (2 snapshots) is infeasible historically — noted, not counted.
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
sys.path.insert(0, str(REPO_ROOT))

from data.db import connect as db_connect  # noqa: E402

DB_PATH = None  # via env DB_PATH / config
ADV_MIN = 10.0e9
T_BAR = 3.06
VOL_WINDOW = 60          # sessions of daily returns ENDING the day before the decision date
ADV_WINDOW = 20
CLASSES = {
    "A_tenderoffer":  ("tenderoffer", "tender_start"),
    "C_rightissue":   ("rightissue", "rightissue_cumdate"),
    "D_dividend":     ("dividend", "dividend_cumdate"),
    "E_stocksplit":   ("stocksplit", "stocksplit_cumdate"),
    "E_bonus":        ("bonus", "stocksplit_cumdate"),
    "E_stock_reverse": ("stock_reverse", "stocksplit_cumdate"),
    "F_warrant":      ("warrant", "wrant_trading_from"),
}


def parse_date(v):
    if not v:
        return None
    try:
        return datetime.strptime(str(v)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def pre_event_stats(c, ticker: str, d: date):
    """(adv20_ok, adv20_value, vol60, n_pre_bars) — every query is strictly
    `date < decision_date`. NOTHING on/after d is selected, ever."""
    rows = c.execute(
        "SELECT close, volume FROM ohlcv WHERE ticker=? AND date<? "
        "AND COALESCE(is_final,1)=1 ORDER BY date DESC LIMIT ?",
        (ticker, d.isoformat(), VOL_WINDOW + 1)).fetchall()
    n_pre = len(rows)
    if len(rows) < ADV_WINDOW + 1:
        return (False, None, None, n_pre)
    adv20 = sum(cl * v for cl, v in rows[:ADV_WINDOW]) / ADV_WINDOW
    vol60 = None
    if len(rows) >= VOL_WINDOW + 1:
        closes = [r[0] for r in rows[:VOL_WINDOW + 1]]   # 61 closes, all pre-event
        rets = [math.log(closes[i] / closes[i + 1]) for i in range(len(closes) - 1)
                if closes[i] > 0 and closes[i + 1] > 0]
        vol60 = float(np.std(rets, ddof=1)) if len(rets) >= 30 else None
    return (adv20 >= ADV_MIN, adv20, vol60, n_pre)


def main() -> None:
    out = {"generated_utc": datetime.utcnow().isoformat() + "Z",
           "rule": "NO post-event price read; every price query filters date < decision_date",
           "decision_date_convention": {k: v[1] for k, v in CLASSES.items()},
           "adv_min": ADV_MIN, "t_bar": T_BAR, "vol_window": VOL_WINDOW,
           "classes": {}, "idx80": {}}

    with db_connect(read_only=True) as c:
        for cls, (atype, date_field) in CLASSES.items():
            rows = c.execute(
                "SELECT ticker, event_date, raw_json FROM corporate_action_events "
                "WHERE action_type=?", (atype,)).fetchall()
            per_year = defaultdict(int)
            liq = {"E1_2009_2021_09": 0, "E2_2021_10_2026": 0}
            tickers = defaultdict(int)
            n_total = n_parsed = n_liquid = n_pre60 = 0
            vols, advs = [], []
            liquid_months = set()
            missing_date = 0
            for ticker, _event_date, raw in rows:
                n_total += 1
                tickers[ticker] += 1
                try:
                    j = json.loads(raw)
                except ValueError:
                    missing_date += 1
                    continue
                d = parse_date(j.get(date_field))
                if d is None:
                    missing_date += 1
                    continue
                n_parsed += 1
                per_year[d.year] += 1
                adv_ok, adv, vol, n_pre = pre_event_stats(c, ticker, d)
                if n_pre >= VOL_WINDOW:
                    n_pre60 += 1
                if vol is not None:
                    vols.append(vol)
                if adv is not None:
                    advs.append(adv)
                if adv_ok:
                    n_liquid += 1
                    era = "E1_2009_2021_09" if d < date(2021, 10, 1) else "E2_2021_10_2026"
                    if d >= date(2009, 1, 1):
                        liq[era] += 1
                        liquid_months.add((d.year, d.month))
            vols_s = sorted(vols)
            med = float(np.median(vols_s)) if vols_s else None
            iqr = (float(np.percentile(vols_s, 25)), float(np.percentile(vols_s, 75))) \
                if vols_s else None
            n_liquid_2009 = liq["E1_2009_2021_09"] + liq["E2_2021_10_2026"]
            # month-clustered effective n: distinct (year, month) of decision dates
            # since 2009 (events cluster in months; overlap breaks independence)
            liquid_months = set()
            for ticker, _ed, raw in rows:
                try:
                    j = json.loads(raw)
                except ValueError:
                    continue
                d = parse_date(j.get(date_field))
                if d and d >= date(2009, 1, 1):
                    liquid_months.add((d.year, d.month))
            mde = {}
            for h in (5, 10, 20):
                if med and n_liquid_2009:
                    mde[f"h{h}_independent_pct"] = round(
                        100 * T_BAR * med * math.sqrt(h) / math.sqrt(n_liquid_2009), 3)
                else:
                    mde[f"h{h}_independent_pct"] = None
            # month-clustered effective n: distinct (year, month) of LIQUID
            # decision dates since 2009 (collected in the main loop; events
            # cluster in months, and overlap breaks the independence
            # assumption — conservative)
            n_months = len(liquid_months)
            mde_clustered = {}
            for h in (5, 10, 20):
                if med and n_months:
                    mde_clustered[f"h{h}_monthclustered_pct"] = round(
                        100 * T_BAR * med * math.sqrt(h) / math.sqrt(n_months), 3)
                else:
                    mde_clustered[f"h{h}_monthclustered_pct"] = None
            out["classes"][cls] = {
                "n_total": n_total,
                "n_decision_date_parsed": n_parsed,
                "n_missing_decision_date": missing_date,
                "date_coverage_pct": round(100 * n_parsed / n_total, 1) if n_total else None,
                "per_year_decision_date": dict(sorted(per_year.items())),
                "n_multi_event_tickers": sum(1 for t, k in tickers.items() if k > 1),
                "max_events_one_ticker": max(tickers.values()) if tickers else 0,
                "n_with_60_pre_bars": n_pre60,
                "frac_with_60_pre_bars_pct": round(100 * n_pre60 / n_total, 1) if n_total else None,
                "n_liquid_total_2009": n_liquid_2009,
                "n_liquid_by_era": {k: v for k, v in liq.items()},
                "pre_event_vol60_median_daily": round(med, 5) if med else None,
                "pre_event_vol60_iqr_daily": [round(x, 5) for x in iqr] if iqr else None,
                "mde_independent": mde,
                "mde_month_clustered": mde_clustered,
                "n_distinct_event_months": n_months,
            }

        # B: index reconstitution — membership SNAPSHOT per period; the passive
        # flow events are the DELTAS between consecutive periods (effective order)
        periods = c.execute(
            "SELECT period_label, effective_from, effective_to, left_censored, notes "
            "FROM idx80_reconstitution_periods ORDER BY effective_from").fetchall()
        members = defaultdict(set)
        for tk, pl in c.execute(
                "SELECT ticker, period_label FROM idx80_membership_history"):
            members[pl].add(tk)
        changes_per_period = {}
        ordered = [(p, ef, lc) for p, ef, _et, lc, _n in periods]
        for (pl_prev, _, _), (pl, ef, lc) in zip(ordered, ordered[1:]):
            added = sorted(members[pl] - members[pl_prev])
            removed = sorted(members[pl_prev] - members[pl])
            changes_per_period[pl] = {"effective_from": ef, "left_censored": lc,
                                      "added": len(added), "removed": len(removed),
                                      "added_tickers": added, "removed_tickers": removed}
        out["idx80"] = {
            "n_periods": len(periods),
            "n_reconstitution_events": max(0, len(periods) - 1),
            "periods": [{"period": p, "effective_from": ef, "effective_to": et,
                         "left_censored": lc} for p, ef, et, lc, _n in periods],
            "membership_status_counts": {"MEMBER": sum(len(v) for v in members.values())},
            "changes_per_period": changes_per_period,
            "pit_note": "announcement dates are not stored; the period notes cite the "
                        "BEI announcement documents (e.g. Peng-00012/BEI.POP/01-2025, "
                        "announced 22 Jan 2025 for effective 2025-02-03) — reconstitution "
                        "announcements land about a week before the effective date; "
                        "P0 is left-censored to the window start (a baseline snapshot, "
                        "not a reconstitution event)",
        }

    path = HERE / "CENSUS_FEASIBILITY.json"
    path.write_text(json.dumps(out, indent=1) + "\n")
    print("WROTE", path.name)
    for cls, d in out["classes"].items():
        print(f"{cls}: n={d['n_total']} parsed={d['n_decision_date_parsed']} "
              f"liquid2009={d['n_liquid_total_2009']} "
              f"vol60_med={d['pre_event_vol60_median_daily']} "
              f"MDE10={d['mde_independent'].get('h10_independent_pct')}% "
              f"(clustered {d['mde_month_clustered'].get('h10_monthclustered_pct')}%)")


if __name__ == "__main__":
    main()
