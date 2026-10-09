"""G1 one-shot runner — gated, WRITTEN AT G0, NOT RUN on real data.

Executes only after owner approval (TENDER_G1_APPROVED=1) and only from the
frozen tree, and ONLY if the G0 census decided the stop rule does NOT fire
(census.stop_rule.n_eligible >= 20). One run: eligibility recomputed and
matched against CENSUS_G0.json (drift -> STOP) BEFORE any outcome; the
snapshot sha256 and dataset fingerprint re-hashed against the census; the
bar's N re-verified; then the frozen T1 arm over eligible events with
month-clustered t, the EW-book excess requirement, and the report-only
variants. Writes RESULT_<utc>.json.

--synthetic: dry run on the fixture market (proves the RESULT schema
without touching real outcomes).

Run:  TENDER_WF_DB=<snap> TENDER_G1_APPROVED=1 \
        venv/bin/python docs/research_programs/P-M/tender_offer/g1_run.py
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

import tender_floor as TF  # noqa: E402
import outcomes as OC      # noqa: E402
from g0_census import census_g0  # noqa: E402


def main() -> None:
    synthetic = "--synthetic" in sys.argv
    if not synthetic and os.environ.get("TENDER_G1_APPROVED") != "1":
        raise SystemExit("TENDER_G1_APPROVED=1 required (one run after owner approval)")
    t0 = time.time()
    census = json.loads((HERE / "CENSUS_G0.json").read_text())
    if census["stop_rule"]["n_eligible"] < TF.MIN_EVENTS:
        raise SystemExit("stop rule fired at G0 (n < 20): no G1 - spread ledger is the deliverable")
    if synthetic:
        sys.path.insert(0, str(HERE))
        import synthetic as SYN
        conn = SYN.make_db()
        fac, divs = TF.load_ca(conn)
        panel = TF.Panel(conn, fac, divs)
        events = [TF.eligibility(panel, e) for e in SYN.fixture_events()]
        events = [e for e in events if e["stage"] == "ELIGIBLE"]
        fp_block = {"mode": "synthetic"}
    else:
        wf_db = os.environ.get("TENDER_WF_DB", TF.WF_SNAPSHOT)
        assert TF.sha256_file(wf_db) == census["snapshot"]["sha256"], "snapshot drift - STOP"
        recomputed = census_g0(wf_db)
        assert (recomputed["snapshot"]["dataset_fingerprint"]["sha256"]
                == census["snapshot"]["dataset_fingerprint"]["sha256"]), "dataset fingerprint drift - STOP"
        a = [(e["ticker"], e["event_id"]) for e in recomputed["eligible_events"]]
        b = [(e["ticker"], e["event_id"]) for e in census["eligible_events"]]
        assert a == b, "eligibility drift vs census - STOP"
        from data.db import connect as db_connect
        conn = db_connect(path=wf_db, read_only=True)
        fac, divs = TF.load_ca(conn)
        panel = TF.Panel(conn, fac, divs)
        tenders = {(e["ticker"], e["event_id"]): e for e in TF.load_tenders(conn)}
        conn.close()
        events = []
        for tkr, eid in b:
            ev = tenders[(tkr, eid)]
            r = TF.eligibility(panel, ev)
            assert r["stage"] == "ELIGIBLE", f"re-eligibility failed for {tkr} #{eid} - STOP"
            events.append(r)
        fp_block = {"walkforward": {"path": wf_db, "sha256": TF.sha256_file(wf_db)},
                    "dataset_fingerprint": recomputed["snapshot"]["dataset_fingerprint"],
                    "matches_census": True}

    rows = [OC.t1_event(panel, f) for f in events]
    rs = [r["R"] for r in rows if np.isfinite(r["R"])]
    months = [r["d_entry"][:7] for r in rows if np.isfinite(r["R"])]
    mean, se, t, n_cl = OC.month_clustered_t(rs, months)
    xs = [r["excess"] for r in rows if np.isfinite(r.get("excess", np.nan))]
    book_mean = float(np.mean([r["book_ret"] for r in rows if np.isfinite(r["book_ret"])]))
    acc = [r["acceptance_ub"] for r in rows if np.isfinite(r["acceptance_ub"])]
    conv = [r["convergence"] for r in rows if np.isfinite(r["convergence"])]
    cond = {
        "n_events": len(rs),
        "mean_R": mean, "se_cluster": se, "t_cluster": t, "clusters": n_cl,
        "bar_frozen": census.get("bar", {}).get("bar_frozen_609", 3.2978),
        "N_frozen": census.get("bar", {}).get("N", 609),
        "excess_mean": float(np.mean(xs)) if xs else float("nan"),
        "book_mean": book_mean,
        "acceptance_ub_mean": float(np.mean(acc)) if acc else float("nan"),
        "convergence_mean": float(np.mean(conv)) if conv else float("nan"),
        "withdrawn_suspect_n": sum(1 for r in rows if r["withdrawn_suspect"]),
        "withdrawn_suspect_mean_R": float(np.mean([r["R"] for r in rows if r["withdrawn_suspect"]]))
        if any(r["withdrawn_suspect"] for r in rows) else float("nan"),
        "non_withdrawn_mean_R": float(np.mean([r["R"] for r in rows if not r["withdrawn_suspect"]]))
        if any(not r["withdrawn_suspect"] for r in rows) else float("nan"),
    }
    cond["pass_strength"] = bool(cond["mean_R"] > 0 and cond["t_cluster"] >= cond["bar_frozen"])
    cond["pass_excess"] = bool(cond["excess_mean"] > 0)
    cond["pass"] = bool(cond["pass_strength"] and cond["pass_excess"])
    # report-only splits
    def split(key_fn):
        groups: dict[str, list[float]] = {}
        for r in rows:
            if np.isfinite(r["R"]):
                groups.setdefault(key_fn(r), []).append(r["R"])
        return {k: {"n": len(v), "mean_R": float(np.mean(v))} for k, v in sorted(groups.items())}
    splits = {"adv_tier": split(lambda r: r["adv_tier"]),
              "full_partial": split(lambda r: "full" if (r["pct"] is not None and r["pct"] >= TF.FULL_PCT_CUT) else "partial")}
    worst = sorted([r for r in rows if np.isfinite(r["R"])], key=lambda r: r["R"])[:5]
    year: dict[str, dict] = {}
    for r in rows:
        if np.isfinite(r["R"]):
            y = r["start"][:4]
            a_ = year.setdefault(y, {"n": 0, "sum": 0.0})
            a_["n"] += 1
            a_["sum"] += r["R"]
    year_table = {y: {"n": v["n"], "mean_R": v["sum"] / v["n"]} for y, v in sorted(year.items())}
    out = {"generated_utc": datetime.now(timezone.utc).isoformat(),
           "mode": "synthetic" if synthetic else "G1",
           "gate": "none (--synthetic)" if synthetic else "TENDER_G1_APPROVED",
           "snapshot": fp_block,
           "conditions": cond, "splits": splits, "year_table": year_table,
           "per_event": rows,
           "five_worst": [{k: r.get(k) for k in ("ticker", "event_id", "start", "spread",
                                                 "cost", "R", "convergence", "withdrawn_suspect")}
                          for r in worst],
           "runtime_minutes": round((time.time() - t0) / 60.0, 1)}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = f"RESULT_SYNTHETIC_{stamp}.json" if synthetic else f"RESULT_{stamp}.json"
    (HERE / name).write_text(json.dumps(out, indent=1, default=str) + "\n")
    print("WROTE", name)
    print(f"events {cond['n_events']} | mean R {cond['mean_R']:.5f} | t(cluster) {cond['t_cluster']:.3f}"
          f" vs bar {cond['bar_frozen']} | excess {cond['excess_mean']:.5f} | pass {cond['pass']}")


if __name__ == "__main__":
    main()
