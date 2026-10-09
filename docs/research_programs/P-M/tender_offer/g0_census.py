"""G0 census — tender-offer floor (HYP-PM-0018 draft). COUNTS ONLY.

No return/price after any event's entry close is computed, printed or
stored (D-070 rule 1; D-074 G0 mode). The eligibility path touches bars at
indices <= the entry index only (structurally asserted in
test_pit_tender.py). Window "lengths" are session COUNTS (calendar facts),
not prices.

Run:  venv/bin/python docs/research_programs/P-M/tender_offer/g0_census.py
Writes CENSUS_G0.json next to this file.
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[3]))

import tender_floor as TF  # noqa: E402
from data.db import connect as db_connect          # noqa: E402
from research.tracking import dataset_fingerprint  # noqa: E402

sys.path.insert(0, str(HERE.parents[1] / "deflation_audit"))
import bar_v2  # noqa: E402

_BAR_609 = float(bar_v2.e_max_abs_z(609))


def census_g0(wf_db: str) -> dict:
    t0 = time.time()
    conn = db_connect(path=wf_db, read_only=True)
    fac, divs = TF.load_ca(conn)
    panel = TF.Panel(conn, fac, divs)
    tenders = TF.load_tenders(conn)
    conn.close()

    fp = db_connect(path=wf_db, read_only=True)
    fingerprint = dataset_fingerprint(fp)
    fp.close()

    waterfall: dict[str, int] = {"S0_rows": len(tenders)}
    stage_fail: dict[str, list] = {}
    eligible = []
    for ev in tenders:
        r = TF.eligibility(panel, ev)
        st = r["stage"]
        if st == "ELIGIBLE":
            eligible.append(r)
        else:
            stage_fail.setdefault(st, []).append(
                {"ticker": ev["ticker"], "event_id": ev["event_id"]})
    for st in ("S1_rule1", "S2_settled", "S3_entry", "S4_prebars", "S5_volume",
               "S6_above", "S7_adv", "S8_spread", "S9_guard"):
        waterfall[st] = len(stage_fail.get(st, []))
    waterfall["eligible"] = len(eligible)

    # ---- tender_created audit (report only; created is used for NOTHING else)
    ok_rows = [e for e in tenders if e["start"] and e["end"]]
    created_le_start = sum(1 for e in ok_rows if e["created"] and e["created"] <= e["start"])
    created_ge_end = sum(1 for e in ok_rows if e["created"] and e["created"] >= e["end"])
    cc = Counter(e["created"] for e in ok_rows if e["created"])
    bulk = {str(d): c for d, c in cc.items() if c > 50}

    # ---- basis check (pre-entry closes only)
    basis = []
    for ev in tenders:
        if (ev["price_raw"] is None or ev["price_raw"] <= 0
                or ev["start"] is None or ev["end"] is None or not (ev["start"] < ev["end"])):
            continue
        d_entry = panel.last_session_before(ev["start"])
        if d_entry is None:
            continue
        g = panel.tickers.get(ev["ticker"])
        if g is None:
            continue
        import bisect
        i = bisect.bisect_left(g["d"], d_entry)
        if i < len(g["d"]) and g["d"][i] == d_entry:
            c_entry = float(g["c"][i])
        else:
            continue
        f = TF.f_cum(fac, ev["ticker"], d_entry)
        if f < 1.05:
            continue
        basis.append({"ticker": ev["ticker"], "event_id": ev["event_id"],
                      "d_entry": str(d_entry), "close_entry": round(c_entry, 2),
                      "f_cum": round(f, 4),
                      "r_stored": round(ev["price_raw"] / c_entry, 4),
                      "r_asannounced": round(ev["price_raw"] / (c_entry * f), 4)})

    # ---- power (pre-entry sigma only) + optimistic bound (the spread itself)
    sig, spreads, wins = [], [], []
    for r in eligible:
        s = TF.sigma_d(panel, r["ticker"], r["d_entry"])
        if s is not None:
            sig.append(s * np.sqrt(r["window_sessions"]))
        spreads.append(r["spread"])
        wins.append(r["window_sessions"])
    n = len(eligible)
    median_sw = float(np.median(sig)) if sig else float("nan")
    power = {
        "n_events": n,
        "median_preentry_sigma_d": float(np.median([TF.sigma_d(panel, r["ticker"], r["d_entry"])
                                                    for r in eligible
                                                    if TF.sigma_d(panel, r["ticker"], r["d_entry"]) is not None]))
        if eligible else float("nan"),
        "median_sigma_scaled_to_window": median_sw,
        "mde_at_bar": 3.297758 * median_sw / np.sqrt(n) if n and np.isfinite(median_sw) else float("nan"),
        "optimistic_bound_median_spread": float(np.median(spreads)) if spreads else float("nan"),
        "optimistic_bound_mean_spread": float(np.mean(spreads)) if spreads else float("nan"),
        "window_sessions_median": float(np.median(wins)) if wins else float("nan"),
        "window_sessions_min": int(min(wins)) if wins else None,
        "window_sessions_max": int(max(wins)) if wins else None,
    }

    per_year = Counter(str(r["start"])[:4] for r in eligible)
    census = {
        "rule": ("COUNTS ONLY: no return/price after any event's entry close was computed, "
                 "printed or stored (D-074 G0 mode; D-070 rule 1)"),
        "snapshot": {
            "path": wf_db,
            "sha256": TF.sha256_file(wf_db),
            "dataset_fingerprint": fingerprint,
            "reuse_decision": ("reuses the 2026-10-08 walkforward snapshot: the live DB's "
                               "tenderoffer rows are logically identical (165=165, same "
                               "(ticker,event_id,event_date,raw_json) sets; newest event_date "
                               "2026-10-02) - nothing newer than the snapshot"),
        },
        "panel": {"first_session": str(panel.sessions[0]), "last_session": str(panel.sessions[-1]),
                  "tickers": len(panel.tickers)},
        "waterfall": waterfall,
        "waterfall_fail_detail": stage_fail,
        "tender_created_audit": {
            "rows_with_start_end": len(ok_rows),
            "created_le_start": created_le_start,
            "created_after_start": len(ok_rows) - created_le_start,
            "created_ge_end": created_ge_end,
            "created_dates_shared_gt50": bulk,
            "note": ("tender_created is a vendor stamp, used for THIS audit only; PIT rule: the "
                     "offer is public at the close before tender_start (POJK 9/2018 - the offer "
                     "statement precedes the window); example artefact ZBRA created 2021-09-23 "
                     "for window 2021-04-30..05-29"),
        },
        "basis_check": {
            "rule_frozen": TF.BASIS_RULE,
            "rescale": "adj_price = tender_price / f_cum(split-class factors with ex-date strictly after the entry session)",
            "discriminating_events_f_ge_1.05": basis,
            "finding": ("as-announced: LPGI 2023 r_stored 10.42 vs r_asannounced 1.042; PTRO "
                        "2022 10.19 vs 1.019; EDGE 2021 2.02 vs 0.404 - stored-basis ratios of "
                        "6-10x are impossible spreads; dividend_value by contrast IS pre-scaled "
                        "(stress G0)"),
        },
        "mandatory_voluntary": {
            "rule": "NONE - event_note is empty for all 165 rows and no stored field classifies; left unreported (brief: don't guess)",
            "full_partial_cut": TF.FULL_PCT_CUT,
            "full_partial": ("tender_percentage max is 90.0 -> under the >=99 full cut ALL "
                             "events are partial; reported as such, no guessing"),
        },
        "eligible_per_year": dict(sorted(per_year.items())),
        "eligible_events": [{"ticker": r["ticker"], "event_id": r["event_id"],
                             "start": str(r["start"]), "end": str(r["end"]),
                             "d_entry": str(r["d_entry"]), "d_exit": str(r["d_exit"]),
                             "close_entry": round(r["close_entry"], 2),
                             "price_raw": r["price_raw"], "f_cum_entry": round(r["f_cum_entry"], 4),
                             "price_adj": round(r["price_adj"], 2),
                             "spread": round(r["spread"], 4),
                             "adv20_idrbn": round(r["adv20"] / 1e9, 3),
                             "cost": round(r["cost"], 4),
                             "window_sessions": r["window_sessions"]}
                            for r in sorted(eligible, key=lambda x: x["start"])],
        "bar": {
            "N": 609,
            "bar_exact_609": _BAR_609,
            "bar_frozen_609": 3.2978,
            "ledger_decomposition": ("608 after D-078 (605 after D-071/D-072 + 2 exploratory "
                                     "arms + 4 NR7 post-mortem comparisons + HYP-PM-0017's 2 "
                                     "arms + HYP-PM-0019's 1 arm) + THIS arm = 609"),
            "which": ("609: D-074's stale 602/3.2945 is superseded (owner 2026-10-09; brief "
                      "census line wins on this one point); exact bar_v2.e_max_abs_z(609)"),
            "source": "docs/research_programs/deflation_audit/bar_v2.py e_max_abs_z",
        },
        "stop_rule": {
            "threshold": TF.MIN_EVENTS,
            "n_eligible": n,
            "decision": "G1 PROCEEDS (n >= 20)" if n >= TF.MIN_EVENTS else "STOP: n < 20 -> spread ledger, no G1",
        },
        "power": power,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "runtime_minutes": round((time.time() - t0) / 60.0, 1),
    }
    return census


if __name__ == "__main__":
    out = census_g0(TF.WF_SNAPSHOT)
    (HERE / "CENSUS_G0.json").write_text(json.dumps(out, indent=1, default=str) + "\n")
    print("WROTE CENSUS_G0.json")
    print(json.dumps({"waterfall": out["waterfall"], "stop": out["stop_rule"]["decision"],
                      "per_year": out["eligible_per_year"]}, indent=1))
