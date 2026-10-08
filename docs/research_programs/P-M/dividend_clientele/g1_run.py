"""G1 one-shot runner — gated, WRITTEN AT G0, NOT RUN on real data.

Executes only after owner approval (DIVIDEND_G1_APPROVED=1) and only from the
frozen tree. One run: the frozen event populations (dividend_clientele, the
G0 census code path), then the outcome machinery (outcomes.py) — D1 and D2,
each against the EW liquid book and the Parkinson-decile-matched control, the
frozen primary t (min of month-mean and two-way cluster), the halves, the
yield-tercile and AGM-season reports, and the pass conditions as COMPUTED
booleans. The snapshot sha256 + dataset fingerprint are verified against
CENSUS_G0.json BEFORE any outcome is read; a mismatch SystemExit's.

`--synthetic`: a dry run on the synthetic fixture market — proves the RESULT
schema without touching real outcomes (writes RESULT_SYNTHETIC_<utc>.json).

Run:  DB_PATH=<snapshot> DIVIDEND_G1_APPROVED=1 \
        venv/bin/python docs/research_programs/P-M/dividend_clientele/g1_run.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[3]))

import dividend_clientele as DC  # noqa: E402
import outcomes as OC  # noqa: E402

FOREIGN_OWNERSHIP = "none PIT; not reported"


def load_world(db_path: str):
    """Panel, events, book and fingerprint from the pinned snapshot."""
    conn = DC.db_connect(path=db_path, read_only=True)
    fp = DC.dataset_fingerprint(conn)
    panel = DC.Panel(conn)
    rows, dq = DC.load_dividend_rows(conn)
    freq = DC.created_date_freq(rows)
    ca_ex = DC.load_ca_exdates(conn)
    rups = DC.load_rups(conn)
    conn.close()
    built = DC.build_events(panel, rows, freq, ca_ex, rups)
    div_ab: dict = {}
    for r in rows:
        k = (r["ticker"], r["ex"])
        div_ab[k] = div_ab.get(k, 0.0) + r["value"]
    book = OC.Book(panel, ca_ex, div_ab)
    return panel, book, built, fp, dq


def run_arm(arm_events, panel, book, bar: float, kind: str) -> tuple[dict, list]:
    per = []
    for ev in arm_events:
        r = OC.d1_event_return(panel, book, ev) if kind == "D1" \
            else OC.d2_event_return(panel, book, ev)
        per.append((ev, r))
    pairs = [(e, r["excess"]) for e, r in per if r["excess"] is not None]
    xs = [x for _, x in pairs]
    xd = [r["excess_decile"] for _, r in per if r["excess_decile"] is not None]
    months = [e["month"] for e, _ in pairs]
    tickers = [e["ticker"] for e, _ in pairs]
    x = np.asarray(xs, float)
    t = OC.primary_t(xs, months, tickers) if xs else {"t_month": float("nan"),
                                                      "t_two_way_cluster": float("nan"),
                                                      "primary_t": float("nan")}
    h1 = [x for e, x in pairs if e["half"] == 1]
    h2 = [x for e, x in pairs if e["half"] == 2]
    cond = {
        "n": len(xs), "mean": float(x.mean()) if len(x) else float("nan"),
        "median": float(np.median(x)) if len(x) else float("nan"),
        "win_rate": float((x > 0).mean()) if len(x) else float("nan"),
        "t_month": t["t_month"], "t_two_way_cluster": t["t_two_way_cluster"],
        "primary_t": t["primary_t"], "bar": bar,
        "half1_n": len(h1), "half1_mean": float(np.mean(h1)) if h1 else float("nan"),
        "half2_n": len(h2), "half2_mean": float(np.mean(h2)) if h2 else float("nan"),
        "decile_n": len(xd),
        "decile_mean": float(np.mean(xd)) if xd else float("nan"),
    }
    cond["pass_strength"] = bool(cond["mean"] > 0 and cond["primary_t"] >= bar)
    cond["pass_halves"] = bool(cond["half1_mean"] > 0 and cond["half2_mean"] > 0)
    cond["pass_decile"] = bool(cond["decile_mean"] > 0)
    per_year: dict[str, dict] = {}
    for e, x_ in pairs:
        y = str(e["cum"].year)
        a = per_year.setdefault(y, {"n": 0, "sum": 0.0})
        a["n"] += 1
        a["sum"] += x_
    cond["year_table"] = {y: {"n": v["n"], "mean": v["sum"] / v["n"]}
                          for y, v in sorted(per_year.items())}
    agm = [x_ for e, x_ in pairs if e["agm_season"]]
    rest = [x_ for e, x_ in pairs if not e["agm_season"]]
    cond["agm_season"] = {"may_jul_n": len(agm),
                          "may_jul_mean": float(np.mean(agm)) if agm else None,
                          "rest_n": len(rest),
                          "rest_mean": float(np.mean(rest)) if rest else None}
    cond["foreign_ownership_proxy"] = FOREIGN_OWNERSHIP
    return cond, per


def d2_extras(per, edges) -> dict:
    gross = [r["excess_gross"] for _, r in per if r["excess_gross"] is not None]
    drops = [r["drop_ratio"] for _, r in per if r["drop_ratio"] is not None]
    ter: dict[str, list] = {"t1": [], "t2": [], "t3": []}
    for e, r in per:
        if r["excess"] is None or e["yield"] is None:
            continue
        k = "t1" if e["yield"] <= edges[0] else ("t2" if e["yield"] <= edges[1] else "t3")
        ter[k].append(r["excess"])
    low2 = ter["t1"] + ter["t2"]
    return {
        "gross_mean": float(np.mean(gross)) if gross else None,
        "drop_ratio_median": float(np.median(drops)) if drops else None,
        "drop_ratio_iqr": [float(np.percentile(drops, 25)), float(np.percentile(drops, 75))]
        if drops else None,
        "yield_terciles": {k: {"n": len(v), "mean": float(np.mean(v)) if v else None}
                           for k, v in ter.items()},
        "lower_two_terciles_mean": float(np.mean(low2)) if low2 else None,
    }


def populations(built) -> tuple[list, list]:
    ev = built["events"]
    d1_events = [e for e in ev if e["anchor"] is not None and e["window"] is not None
                 and 3 <= e["window"] <= 10 and e["entry_bar_ok"]]
    d2_events = [e for e in ev if e["yield"] is not None and e["yield"] >= DC.YIELD_MIN]
    return d1_events, d2_events


def main() -> None:
    synthetic = "--synthetic" in sys.argv
    if not synthetic and os.environ.get("DIVIDEND_G1_APPROVED") != "1":
        raise SystemExit("DIVIDEND_G1_APPROVED=1 required (one run after owner approval)")
    t0 = time.time()
    census = json.loads((HERE / "CENSUS_G0.json").read_text())
    bar = census["census"]["bar_frozen"]
    edges = census["d2"]["yield_tercile_edges"]
    if synthetic:
        import synthetic as SYN
        conn = SYN.make_db()
        fp = DC.dataset_fingerprint(conn)
        panel = DC.Panel(conn)
        rows, dq = DC.load_dividend_rows(conn)
        freq = DC.created_date_freq(rows)
        ca_ex = DC.load_ca_exdates(conn)
        rups = DC.load_rups(conn)
        conn.close()
        built = DC.build_events(panel, rows, freq, ca_ex, rups)
        div_ab: dict = {}
        for r in rows:
            div_ab[(r["ticker"], r["ex"])] = div_ab.get((r["ticker"], r["ex"]), 0.0) + r["value"]
        book = OC.Book(panel, ca_ex, div_ab)
        fp_block = {"mode": "synthetic", "dataset_fingerprint": fp}
    else:
        db = os.environ.get("DB_PATH", DC.SNAPSHOT_DEFAULT)
        snap_sha = DC._sha256(db)
        panel, book, built, fp, dq = load_world(db)
        if snap_sha != census["snapshot"]["sha256"]:
            raise SystemExit("snapshot sha256 drift vs CENSUS_G0.json — STOP")
        if fp["sha256"] != census["snapshot"]["dataset_fingerprint"]["sha256"]:
            raise SystemExit("dataset fingerprint drift vs CENSUS_G0.json — STOP")
        fp_block = {"path": db, "sha256": snap_sha, "dataset_fingerprint": fp,
                    "matches_census": True}

    d1_events, d2_events = populations(built)
    d1, _ = run_arm(d1_events, panel, book, bar, "D1")
    d2, d2_per = run_arm(d2_events, panel, book, bar, "D2")
    dx = d2_extras(d2_per, edges)
    d2["window_distribution"] = {str(w): sum(1 for e in d1_events if e["window"] == w)
                                 for w in sorted({e["window"] for e in d1_events})}
    d2["not_top_tercile_only"] = bool(dx["lower_two_terciles_mean"] is not None
                                      and dx["lower_two_terciles_mean"] > 0)
    d1["pass"] = bool(d1["pass_strength"] and d1["pass_halves"] and d1["pass_decile"])
    d2["pass"] = bool(d2["pass_strength"] and d2["pass_halves"] and d2["pass_decile"]
                      and d2["not_top_tercile_only"])

    out = {"generated_utc": datetime.now(timezone.utc).isoformat(),
           "mode": "synthetic" if synthetic else "G1",
           "gate": "none (--synthetic)" if synthetic else "DIVIDEND_G1_APPROVED",
           "snapshot": fp_block,
           "census_n": census["census"]["N"], "bar_frozen": bar,
           "runs": {"D1": d1, "D2": {**d2, "extras": dx}},
           "runtime_minutes": round((time.time() - t0) / 60.0, 1)}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = f"RESULT_SYNTHETIC_{stamp}.json" if synthetic else f"RESULT_{stamp}.json"
    (HERE / name).write_text(json.dumps(out, indent=1, default=str) + "\n")
    print("WROTE", name)
    for arm in ("D1", "D2"):
        r = out["runs"][arm]
        pt = r["primary_t"]
        print(f"{arm} pass:", r["pass"], "| n", r["n"], "| mean",
              round(r["mean"], 5) if np.isfinite(r["mean"]) else r["mean"],
              "| primary t", round(pt, 3) if np.isfinite(pt) else pt)


if __name__ == "__main__":
    main()
