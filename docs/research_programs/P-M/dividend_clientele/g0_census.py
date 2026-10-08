"""G0 census runner — COUNTS ONLY (HYP-PM-0017 draft).

Calls dividend_clientele.census_g0() and writes CENSUS_G0.json. This file
never imports `outcomes` and never computes a return after any event's
entry/cum close (AST-tested by test_pit_dividend_clientele.py, test (f)).

Run from the worktree root with the pinned snapshot:
  DB_PATH=/home/tjiesar/scratch/g0_snapshots_2026-10-08/walkforward_snapshot_2026-10-08.db \
    venv/bin/python docs/research_programs/P-M/dividend_clientele/g0_census.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[3]))

import dividend_clientele as DC  # noqa: E402


def main() -> None:
    t0 = datetime.now(timezone.utc)
    db = os.environ.get("DB_PATH", DC.SNAPSHOT_DEFAULT)
    out = DC.census_g0(db)
    out["generated_utc"] = t0.isoformat()
    out["runtime_minutes"] = round(
        (datetime.now(timezone.utc) - t0).total_seconds() / 60.0, 1)
    path = HERE / "CENSUS_G0.json"
    path.write_text(json.dumps(out, indent=1, default=str) + "\n")
    print("WROTE", path.name)
    print("snapshot sha256:", out["snapshot"]["sha256"][:16],
          "| fingerprint:", out["snapshot"]["dataset_fingerprint"]["sha256"][:16])
    print("census N:", out["census"]["N"], "| bar frozen:", out["census"]["bar_frozen"],
          "(exact", out["census"]["bar_exact"], ")")
    print("liquid events:", out["liquid_events"]["n"],
          "| D1 final:", out["d1"]["n_final"],
          "| D2 yield>=2%:", out["d2"]["n_yield_ge_2pct"])
    print("funnel drops:", out["events_merged"]["drops"])


if __name__ == "__main__":
    main()
