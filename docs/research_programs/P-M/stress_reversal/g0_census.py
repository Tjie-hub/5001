"""G0 census runner — COUNTS ONLY (HYP-PM-0019 draft).

Builds both panels on the pinned snapshots, computes the stress flags,
episodes and events (pre-event facts only), the E1/E2 agreement gate, the
15:49 pre-close agreement (prices only), and writes CENSUS_G0.json. This file
never imports `outcomes` and never computes a return after any stress day's
close (AST-tested by test_pit_stress_reversal.py, test (f)). All SQL is an
inline literal at the execute call (read-only connections throughout).

Run from the worktree root:
  STRESS_WF_DB=<walkforward snapshot> STRESS_HL_DB=<history_long snapshot> \
    venv/bin/python docs/research_programs/P-M/stress_reversal/g0_census.py
"""
from __future__ import annotations

import json
import math
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[3]))

import stress_reversal as SR  # noqa: E402
from data.db import connect as db_connect  # noqa: E402
from research.tracking import dataset_fingerprint  # noqa: E402


def build_panels(wf_db: str, hl_db: str) -> tuple[SR.Panel, SR.Panel]:
    """Both panels share the CA table (factors + dividend add-back), which lives
    only in walkforward.db; history_long.db carries prices alone."""
    wf = db_connect(path=wf_db, read_only=True)
    fac, divs = SR.load_ca(wf)
    e2 = SR.Panel(wf, fac, divs, "E2")
    hl = db_connect(path=hl_db, read_only=True)
    e1 = SR.Panel(hl, fac, divs, "E1")
    wf.close()
    hl.close()
    return e1, e2


def coverage(conn) -> dict:
    rows = conn.execute("SELECT SUBSTR(date,1,4), COUNT(*), COUNT(DISTINCT ticker), MIN(date), MAX(date) FROM ohlcv_long GROUP BY 1 ORDER BY 1").fetchall()
    per_year = {y: {"rows": n, "tickers": t, "min": mn, "max": mx}
                for y, n, t, mn, mx in rows}
    n_t = conn.execute("SELECT COUNT(DISTINCT ticker) FROM ohlcv_long").fetchone()[0]
    stale = conn.execute("SELECT COUNT(*) FROM (SELECT ticker FROM ohlcv_long GROUP BY ticker HAVING MAX(date) < '2026-01-01')").fetchone()[0]
    ex = [r[0] for r in conn.execute("SELECT ticker FROM ohlcv_long GROUP BY ticker HAVING MAX(date) < '2026-01-01' ORDER BY RANDOM() LIMIT 8").fetchall()]
    return {"tickers": n_t, "stale_last_bar_before_2026": stale,
            "stale_examples": ex, "per_year": per_year}


def liquid_year_table(panel: SR.Panel) -> dict:
    """Median liquid-name count per year, true-ADV vs naive-ADV definition."""
    per_year: dict[int, list[int]] = {}
    per_year_naive: dict[int, list[int]] = {}
    for d in panel.sessions:
        n = n_naive = 0
        for t, i in panel.by_date[d]:
            g = panel.tickers[t]
            if i >= SR.ADV_WINDOW:
                n += int(bool(g["liq_true"][i]))
                n_naive += int(bool(g["liq_naive"][i]))
        per_year.setdefault(d.year, []).append(n)
        per_year_naive.setdefault(d.year, []).append(n_naive)
    return {"median_liquid_per_day_true_adv": {str(y): float(np.median(v)) for y, v in sorted(per_year.items())},
            "median_liquid_per_day_naive_adv": {str(y): float(np.median(v)) for y, v in sorted(per_year_naive.items())}}


def preclose_1549(wf_db: str, panel: SR.Panel, days: list[date]) -> dict:
    """15:49 pre-close flag agreement on 2025+ stress and near-miss days.
    Prices only (the known minute-volume under-capture since 2026-07 is
    irrelevant here). sigma(t) and membership are known before the close."""
    conn = db_connect(path=wf_db, read_only=True)
    out = {"days": 0, "members_no_print_total": 0, "agree": 0, "disagree": 0,
           "flag1549_true_close_false": 0, "flag1549_false_close_true": 0, "per_day": []}
    for d in days:
        thr = SR.STRESS_MULT * panel.sigma[d]
        rets, no_print = [], 0
        for t, i in panel.by_date[d]:
            g = panel.tickers[t]
            if not (i >= SR.ADV_WINDOW and bool(g["liq_true"][i])):
                continue
            if np.isnan(g["ret"][i]) or i < 1:
                continue
            row = conn.execute("SELECT price FROM stockbit_flow_bars WHERE ticker=? AND trade_date=? AND bar_time<=? ORDER BY bar_time DESC LIMIT 1", (t, d.isoformat(), SR.PRE_CLOSE_1549)).fetchone()
            if row is None or not row[0]:
                no_print += 1
                continue
            prev_close = float(g["c"][i - 1])
            if prev_close <= 0:
                no_print += 1
                continue
            r49 = float(row[0]) / prev_close - 1.0
            if abs(r49) > SR.BAD_PRINT:        # same frozen bad-print guard as day-t returns
                no_print += 1
                continue
            rets.append(r49)
        if not rets:
            continue
        rm49 = float(np.mean(rets))
        flag49 = rm49 <= thr
        flag_close = d in panel.flags
        out["days"] += 1
        out["members_no_print_total"] += no_print
        if flag49 == flag_close:
            out["agree"] += 1
        else:
            out["disagree"] += 1
            if flag49:
                out["flag1549_true_close_false"] += 1
            else:
                out["flag1549_false_close_true"] += 1
        out["per_day"].append({"date": str(d),
                               "rm_close_multiple": round(panel.flags.get(d, float("nan")), 3),
                               "rm_1549": round(rm49, 5), "flag_1549": flag49,
                               "flag_close": flag_close, "no_print": no_print})
    conn.close()
    return out


def _year_counts(es: list[date]) -> dict:
    out: dict[str, int] = {}
    for d in es:
        out[str(d.year)] = out.get(str(d.year), 0) + 1
    return dict(sorted(out.items()))


def _event_facts(panel: SR.Panel, evs: list[date]) -> dict:
    sizes, arbs, liq, mults = [], [], [], []
    for d in evs:
        drop = {"FORU"} if d >= SR.FORU_CUTOFF else set()
        b, k, arb = panel.basket(d, drop)
        sizes.append(k)
        arbs.append(arb)
        liq.append(panel.market[d][1])
        mults.append(panel.market[d][0] / panel.sigma[d])
    return {"basket_sizes": sizes, "arb_excluded": arbs, "liquid_names": liq,
            "sigma_multiples": mults}


def _power(panel: SR.Panel, evs: list[date]) -> dict:
    """Pre-event dispersion only: each basket member's daily-return SD over the
    60 days before t; stress multiplier = day-t cross-sectional SD of the
    basket over that normal daily sigma; MDE = bar * sigma_5 / sqrt(n)."""
    sig_daily, stress_mult = [], []
    for d in evs:
        drop = {"FORU"} if d >= SR.FORU_CUTOFF else set()
        members, _, _ = panel.basket(d, drop)
        day_rets, name_sds = [], []
        for t in members:
            g = panel.tickers[t]
            i = next((j for j, dd in enumerate(g["d"]) if dd == d), None)
            if i is None:
                continue
            if not np.isnan(g["ret"][i]):
                day_rets.append(float(g["ret"][i]))
            vals = [float(g["ret"][j]) for j in range(max(0, i - 70), i)
                    if not np.isnan(g["ret"][j])][-60:]
            if len(vals) >= 30:
                name_sds.append(float(np.std(vals, ddof=1)))
        if len(day_rets) >= 2 and name_sds:
            sig_daily.append(float(np.mean(name_sds)))
            stress_mult.append(float(np.std(day_rets, ddof=1)) / float(np.mean(name_sds)))
    if not sig_daily:
        return {}
    sd = float(np.median(sig_daily))
    m = float(np.median(stress_mult))
    sigma5 = sd * math.sqrt(SR.HORIZON) * m
    n = max(1, len(evs))
    return {"n_events": len(evs), "median_member_daily_sigma": sd,
            "median_stress_dispersion_multiplier": round(m, 3), "sigma_5_sessions": sigma5,
            "mde_at_bar604": SR.BAR_FROZEN_604 * sigma5 / math.sqrt(n)}


def _fp(db_path: str) -> dict:
    conn = db_connect(path=db_path, read_only=True)
    fp = dataset_fingerprint(conn)
    conn.close()
    return fp


def census_g0(wf_db: str, hl_db: str) -> dict:
    e1, e2 = build_panels(wf_db, hl_db)

    agreement = SR.overlap_agreement(e1, e2)
    rate = agreement["disagree_rate_union"]
    if rate is not None and rate > 0.20:
        raise SystemExit(f"E1/E2 flag disagreement {rate:.1%} > 20% - STOP per the brief")

    ep1, ep2 = e1.episodes(), e2.episodes()
    ev1 = [d for d in ep1 if date(2007, 1, 1) <= d <= SR.E1_END]
    ev2 = [d for d in ep2 if d >= SR.E2_START]
    pooled = ev1 + ev2
    facts1, facts2 = _event_facts(e1, ev1), _event_facts(e2, ev2)
    sd1, sd2 = sorted(e1.flags), sorted(e2.flags)

    days_2025 = sorted({d for d, m in e2.flags.items()
                        if d >= date(2025, 1, 2) and SR.NEAR_MISS_LO <= m <= SR.NEAR_MISS_HI})
    pre = preclose_1549(wf_db, e2, days_2025)

    cov_conn = db_connect(path=hl_db, read_only=True)
    cov = coverage(cov_conn)
    cov_conn.close()
    pre2009 = sum(1 for d in ev1 if d < date(2009, 1, 1))

    pooled_halves = {"h1_2007_2020": sum(1 for d in pooled if d <= SR.H1_END),
                     "neither_2021H1": sum(1 for d in pooled if SR.H1_END < d < SR.E2_START),
                     "h2_2021_07_on": sum(1 for d in pooled if d >= SR.E2_START)}
    return {
        "rule": "COUNTS ONLY: no return after any stress day's close was computed, printed or "
                "stored (day-t returns are the trigger itself; D-075)",
        "snapshots": {
            "walkforward": {"path": wf_db, "sha256": SR.sha256_file(wf_db),
                            "dataset_fingerprint": _fp(wf_db)},
            "history_long": {"path": hl_db, "sha256": SR.sha256_file(hl_db)},
        },
        "provenance": {
            "builder": "atr_plan/build_long_db.py: pre-2021-07-05 from forward_volex remeasure "
                       "hist_pre2021.pkl (yfinance, split-adjusted, NOT dividend-adjusted); "
                       "2021-07-05+ appended from walkforward ohlcv is_final=1 (same vendor "
                       "basis - sampled overlap rows byte-identical)",
            "adj_close": "a copy of close (the builder sets adj_close = close); no dividend "
                         "adjustment exists in either panel, so returns add the dividend back",
            "zero_volume_bars": "19% of pre-2021 rows were dropped by the builder (stale "
                                "prints); the zero-volume ARB basket exclusion is structural "
                                "on pre-2021 E1 rows",
            "dividend_addback": "the vendor pre-scales dividend_value to the stored price basis "
                                "(verified: AKRA 2021-08 = 60 = 300/5 for its 2022-01 1:5 split; "
                                "ASRM 2021-07 = 194/4.2 for its 4.2 bonus); add-back uses "
                                "corporate_action_events (IDR, deduped by dividend_id, summed "
                                "per ex-date) on EX dates only; CA coverage starts 2009",
            "adv": "stored closes are split-adjusted to the fetch basis while volume is "
                   "as-traded, so the liquid floor uses TRUE rupiah ADV20 = mean(close x f_cum "
                   "x volume) with f_cum the product of share-factors of split-class CA whose "
                   "ex-date is after t; naive-ADV medians reported alongside",
            "coverage": cov,
        },
        "census": {
            "ledger": SR.CENSUS_LEDGER,
            "ledger_rows_counted": [
                "D-071 ratified census N=595 (its 9 components)",
                "2 exploratory arms run 2026-10-08 (A/D 'trap' check, volume-profile swing "
                "check), both null (D-075 census note)",
                "HYP-PM-0017's 2 arms (D1, D2) - G0 frozen 2026-10-08 on "
                "research/dividend-clientele-2026-10, registered at owner approval (the "
                "submission gate for this study)"],
            "n_this_g0_arms": 1,
            "N_expected": SR.N_EXPECTED,
            "bar_exact_604": round(SR.BAR_EXACT_604, 6),
            "bar_frozen_604": SR.BAR_FROZEN_604,
            "N_if_d074_registered_first": SR.N_IF_D074,
            "bar_exact_605": round(SR.BAR_EXACT_605, 6),
            "bar_frozen_605": SR.BAR_FROZEN_605,
            "which": "604 is expected: this G0 submits only after HYP-PM-0017's registration "
                     "(owner gate) and D-074's G0 is NOT NOW per the owner; 605 applies only "
                     "if D-074 registers before this one. The final N is re-verified at "
                     "submission and at G1 (D-071 section 2).",
        },
        "events": {
            "e1_days": len(sd1), "e1_episodes": len(ep1), "e1_events": len(ev1),
            "e2_days": len(sd2), "e2_episodes": len(ep2), "e2_events": len(ev2),
            "pooled_events": len(pooled),
            "per_year": _year_counts(pooled),
            "e1_per_year": _year_counts(ev1),
            "e2_per_year": _year_counts(ev2),
            "halves": pooled_halves,
            "later_in_episode_stress_days": len(sd1) + len(sd2) - len(pooled),
            "basket_size_median_e1": float(np.median(facts1["basket_sizes"])) if facts1["basket_sizes"] else None,
            "basket_size_median_e2": float(np.median(facts2["basket_sizes"])) if facts2["basket_sizes"] else None,
            "basket_sizes_e2": facts2["basket_sizes"],
            "arb_excluded_median_e1": float(np.median(facts1["arb_excluded"])) if facts1["arb_excluded"] else None,
            "arb_excluded_median_e2": float(np.median(facts2["arb_excluded"])) if facts2["arb_excluded"] else None,
            "liquid_names_median_e1": float(np.median(facts1["liquid_names"])) if facts1["liquid_names"] else None,
            "liquid_names_median_e2": float(np.median(facts2["liquid_names"])) if facts2["liquid_names"] else None,
            "sigma_multiple_range_e1": [round(min(facts1["sigma_multiples"]), 2),
                                        round(max(facts1["sigma_multiples"]), 2)] if facts1["sigma_multiples"] else None,
            "pre2009_events_price_only_legs": pre2009,
        },
        "panel_agreement": agreement,
        "adv_floor": {"e1": liquid_year_table(e1), "e2": liquid_year_table(e2)},
        "power": {"e1": _power(e1, ev1), "e2": _power(e2, ev2)},
        "preclose_1549": pre,
    }


def main() -> None:
    t0 = datetime.now(timezone.utc)
    wf_db = os.environ.get("STRESS_WF_DB", SR.WF_SNAPSHOT)
    hl_db = os.environ.get("STRESS_HL_DB", SR.HL_SNAPSHOT)
    out = census_g0(wf_db, hl_db)
    out["generated_utc"] = t0.isoformat()
    out["runtime_minutes"] = round((datetime.now(timezone.utc) - t0).total_seconds() / 60.0, 1)
    path = HERE / "CENSUS_G0.json"
    path.write_text(json.dumps(out, indent=1, default=str) + "\n")
    print("WROTE", path.name)
    a = out["panel_agreement"]
    print("agreement:", a["agree"], "/", a["union"], "flagged days; disagree rate", a["disagree_rate_union"])
    print("events: E1", out["events"]["e1_events"], "| E2", out["events"]["e2_events"],
          "| pooled", out["events"]["pooled_events"])
    print("bar: N=604 ->", out["census"]["bar_frozen_604"], "(605 ->", out["census"]["bar_frozen_605"], ")")
    print("preclose 15:49:", out["preclose_1549"]["agree"], "agree /", out["preclose_1549"]["disagree"],
          "disagree over", out["preclose_1549"]["days"], "days")


if __name__ == "__main__":
    main()
