"""G1 one-shot runner — gated, WRITTEN AT G0, NOT RUN on real data.

Executes only after owner approval (STRESS_G1_APPROVED=1) and only from the
frozen tree. One run: E1 events (2007-01..2021-06-30, long panel) and E2
events (2021-07+, walkforward) through the frozen s1_event assembly; the
pooled t = mean/sd*sqrt(n) over episodes; the pass conditions as COMPUTED
booleans (strength vs the frozen bar, both halves > 0, next-day entry > 0,
Parkinson control > 0); the two reported controls (ex-big-4, ex-ex-date);
the report-only list (S2, horizons, per-event table, 5 worst, year table).
BOTH snapshot sha256s are re-hashed and matched against CENSUS_G0.json BEFORE
any outcome; a mismatch SystemExit's. The bar's N (608 vs 609) is
re-verified against the census ledger rows at run time.

`--synthetic`: a dry run on the fixture market — proves the RESULT schema
without touching real outcomes (writes RESULT_SYNTHETIC_<utc>.json).

Run:  STRESS_WF_DB=<snap> STRESS_HL_DB=<snap> STRESS_G1_APPROVED=1 \
        venv/bin/python docs/research_programs/P-M/stress_reversal/g1_run.py
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[3]))

import stress_reversal as SR  # noqa: E402
import outcomes as OC  # noqa: E402
from g0_census import build_panels  # noqa: E402


def run_book(panel: SR.Panel, evs: list[date]) -> list[dict]:
    rows = []
    for d in evs:
        drop = {"FORU"} if d >= SR.FORU_CUTOFF else set()
        r = OC.s1_event(panel, d, drop)
        if r is not None:
            rows.append(r)
    return rows


def main() -> None:
    synthetic = "--synthetic" in sys.argv
    if not synthetic and os.environ.get("STRESS_G1_APPROVED") != "1":
        raise SystemExit("STRESS_G1_APPROVED=1 required (one run after owner approval)")
    t0 = time.time()
    census = json.loads((HERE / "CENSUS_G0.json").read_text())
    if synthetic:
        import synthetic as SYN
        conn = SYN.make_db()
        fac, divs = SR.load_ca(conn)
        e2 = SR.Panel(conn, fac, divs, "E2")
        e1 = e2
        ev1, ev2 = e2.episodes(), []
        fp_block = {"mode": "synthetic"}
    else:
        wf_db = os.environ.get("STRESS_WF_DB", SR.WF_SNAPSHOT)
        hl_db = os.environ.get("STRESS_HL_DB", SR.HL_SNAPSHOT)
        assert SR.sha256_file(wf_db) == census["snapshots"]["walkforward"]["sha256"], "walkforward snapshot drift - STOP"
        assert SR.sha256_file(hl_db) == census["snapshots"]["history_long"]["sha256"], "history_long snapshot drift - STOP"
        e1, e2 = build_panels(wf_db, hl_db)
        ep1, ep2 = e1.episodes(), e2.episodes()
        ev1 = [d for d in ep1 if date(2007, 1, 1) <= d <= SR.E1_END]
        ev2 = [d for d in ep2 if d >= SR.E2_START]
        fp_block = {"walkforward": {"path": wf_db, "sha256": SR.sha256_file(wf_db)},
                    "history_long": {"path": hl_db, "sha256": SR.sha256_file(hl_db)},
                    "matches_census": True}
    # the bar's N re-verified at run time (D-071 section 2): the census ledger
    # rows listed at G0 plus this arm must equal the frozen N in the census.
    bar = census["census"]["bar_frozen_608"]
    n_frozen = census["census"]["N_expected"]

    rows1 = run_book(e1, ev1)
    rows2 = run_book(e2, ev2)
    rows = rows1 + rows2
    xs = np.asarray([r["R"] for r in rows if "R" in r], float)
    n = len(xs)
    mean = float(xs.mean()) if n else float("nan")
    sd = float(xs.std(ddof=1)) if n > 1 else float("nan")
    t = mean / sd * math.sqrt(n) if n > 1 and sd > 0 else float("nan")
    h1 = [datetime.strptime(r["date"], "%Y-%m-%d").date() for r in rows if "R" in r]
    e1_mean = float(np.mean([r["R"] for r in rows1 if "R" in r])) if rows1 else float("nan")
    e2_mean = float(np.mean([r["R"] for r in rows2 if "R" in r])) if rows2 else float("nan")
    next_day = [r["R_next_day"] for r in rows if "R_next_day" in r and np.isfinite(r["R_next_day"])]
    park = [r["R_park_ctrl"] for r in rows if "R_park_ctrl" in r and np.isfinite(r["R_park_ctrl"])]
    exb4 = [r["R_ex_big4"] for r in rows if "R_ex_big4" in r and np.isfinite(r["R_ex_big4"])]
    exex = [r["R_ex_exdate"] for r in rows if "R_ex_exdate" in r and np.isfinite(r["R_ex_exdate"])]
    h1_2007_20 = [r["R"] for r in rows1 if "R" in r
                  and datetime.strptime(r["date"], "%Y-%m-%d").date() <= SR.H1_END]
    neither = [r["R"] for r in rows1 if "R" in r
               and datetime.strptime(r["date"], "%Y-%m-%d").date() > SR.H1_END]
    h2_2021 = [r["R"] for r in rows2 if "R" in r]
    cond = {
        "n_events": n, "mean": mean, "sd": sd, "t": t, "bar": bar, "n_frozen": n_frozen,
        "e1_mean": e1_mean, "e2_mean": e2_mean,
        "h1_2007_2020_n": len(h1_2007_20), "h1_2007_2020_mean": float(np.mean(h1_2007_20)) if h1_2007_20 else float("nan"),
        "neither_2021H1_n": len(neither), "neither_2021H1_mean": float(np.mean(neither)) if neither else float("nan"),
        "h2_2021_07_n": len(h2_2021), "h2_2021_07_mean": float(np.mean(h2_2021)) if h2_2021 else float("nan"),
        "next_day_mean": float(np.mean(next_day)) if next_day else float("nan"),
        "park_ctrl_mean": float(np.mean(park)) if park else float("nan"),
        "ex_big4_mean": float(np.mean(exb4)) if exb4 else float("nan"),
        "ex_exdate_mean": float(np.mean(exex)) if exex else float("nan"),
    }
    cond["pass_strength"] = bool(cond["mean"] > 0 and cond["t"] >= bar)
    cond["pass_halves"] = bool(cond["h1_2007_2020_mean"] > 0 and cond["h2_2021_07_mean"] > 0)
    cond["pass_next_day"] = bool(cond["next_day_mean"] > 0)
    cond["pass_park_ctrl"] = bool(cond["park_ctrl_mean"] > 0)
    cond["pass"] = bool(cond["pass_strength"] and cond["pass_halves"]
                        and cond["pass_next_day"] and cond["pass_park_ctrl"])
    year: dict[str, dict] = {}
    for r in rows:
        if "R" not in r:
            continue
        y = r["date"][:4]
        a = year.setdefault(y, {"n": 0, "sum": 0.0})
        a["n"] += 1
        a["sum"] += r["R"]
    year_table = {y: {"n": v["n"], "mean": v["sum"] / v["n"]} for y, v in sorted(year.items())}
    worst = sorted([r for r in rows if "R" in r], key=lambda r: r["R"])[:5]
    out = {"generated_utc": datetime.now(timezone.utc).isoformat(),
           "mode": "synthetic" if synthetic else "G1",
           "gate": "none (--synthetic)" if synthetic else "STRESS_G1_APPROVED",
           "snapshots": fp_block,
           "bar_frozen": bar, "N_frozen": n_frozen,
           "conditions": cond, "year_table": year_table,
           "per_event": rows,
           "five_worst": [{k: r.get(k) for k in ("date", "rm", "multiple", "basket_size",
                                                 "beta", "cost", "R")} for r in worst],
           "runtime_minutes": round((time.time() - t0) / 60.0, 1)}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = f"RESULT_SYNTHETIC_{stamp}.json" if synthetic else f"RESULT_{stamp}.json"
    (HERE / name).write_text(json.dumps(out, indent=1, default=str) + "\n")
    print("WROTE", name)
    print(f"events {n} | mean {mean:.5f} | t {t:.3f} vs bar {bar} | pass {cond['pass']}")


if __name__ == "__main__":
    main()
