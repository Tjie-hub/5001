"""Program-wide deflation audit (D-062, 2026-09-28) — census + DSR-style expected-max bar.

METHOD (stated before results): the program's recorded multiplicity is censused from
EXPERIMENT_LEDGER.jsonl plus the disclosed scan counts (LIM-7, registry rows, D-058/D-061
grids). For N roughly-independent standardized trials, the expected maximum |Z| under the
global null is E[Z_max] = (1-g)*Phi^-1(1-1/N) + g*Phi^-1(1-1/(N*e)), g = 0.5772 (Bailey &
Lopez de Prado's deflated-Sharpe expected max under Gaussian trials). Recorded headline
|t| statistics are compared to that bar at four census depths. This is a deflation of
*recorded* statistics, not a re-test; Hansen SPA proper needs the per-arm return series,
which for the pattern arms is unavailable (see ZCODE review F-1, 2026-09-28) — recorded,
not swept away.
"""
import json
from math import log, sqrt
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
GAMMA = 0.5772156649


def e_max_z(n: int) -> float:
    if n < 2:
        return float("nan")
    from statistics import NormalDist
    nd = NormalDist()
    return (1 - GAMMA) * nd.inv_cdf(1 - 1 / n) + GAMMA * nd.inv_cdf(1 - 1 / (n * np.e))


def census() -> dict:
    led = [json.loads(l) for l in (ROOT / "docs/research_programs/EXPERIMENT_LEDGER.jsonl").read_text().splitlines() if l.strip()]
    by_type = {}
    for r in led:
        by_type[r.get("record_type", "?")] = by_type.get(r.get("record_type", "?"), 0) + 1
    # disclosed multiplicities, each with its receipt:
    disclosed = {
        "discovery_sprint_constructions": (120, "P-M discovery/SPRINT_2026-09-15 DISCOVERY_REPORT_2026-09-15.md (6 families, ~120 constructions, memory D-056 era)"),
        "pattern_scan_arms": (12, "LIM-7 / PATTERN_SCAN_2026-09-17.md (~12 arms)"),
        "wedge_variants": (6, "LIM-7 (detector-invariance set)"),
        "entry_filters": (6, "LIM-7"),
        "threshold_cells": (48, "LIM-7"),
        "alignment_cells": (27, "LIM-7 / table27.py"),
        "universe_screen_trials": (6, "D-058 EXPERIMENT_LEDGER (trials: 6)"),
        "insider_screen_cells": (16, "D-061 SCREEN-PM-INS-001 (16 cells)"),
        "registered_hypotheses": (8, "HYPOTHESIS_REGISTRY (0001,0003,0004,0005,0006,0009,0010,0012)"),
        "g1_arms": (3, "C-family {C2,C3,C7}"),
    }
    return {"ledger_records_by_type": by_type, "disclosed": disclosed,
            "total_disclosed_trials": sum(n for n, _ in disclosed.values())}


HEADLINES = [
    ("T1 reference A/EX-2025 (raw, overlapping-hold t)", 2.98, "audit2.py current-data run, 2026-09-28 review; claimed 2.83 @09-16"),
    ("T1 reference D/EX-2025 next-open vs EW (raw)", 3.84, "audit2.py current-data run; claimed 3.90"),
    ("T1 reference ex-2025 (overlap-robust, D-057)", 1.8, "AUDIT_2026-09-24_RESULT_VALIDITY.md R-1 re-reading: 1.5-1.8"),
    ("FADE failed-breakdown h20 gross vs EW-book (D-057)", 4.4, "D-057: robust t -3.6 to -4.4, survives"),
    ("FADE h20 vs IHSG (D-057 re-read, mixed)", 3.13, "D-057: calendar-time t -3.13; month -1.65, DK -1.9"),
    ("VOLEX-001 pooled ex-ante (2026-09-23 audit)", 2.59, "+0.298%/mo t 2.59, suspension-audit basis"),
    ("Insider E1s >=1% distributions h5 ex-2025 (D-061)", 2.74, "SCREEN-PM-INS-001 descriptive cell"),
    ("Insider E3 director/commissioner h20 ex-2025 (D-061)", 1.41, "SCREEN-PM-INS-001 descriptive cell"),
]


def main():
    c = census()
    depths = {
        "registered_only (N=8)": 8,
        "registered+scans (N=50)": 50,
        "+discovery sprint (N=120)": 120,
        "all disclosed trials (N=%d)" % c["total_disclosed_trials"]: c["total_disclosed_trials"],
    }
    bars = {k: round(e_max_z(n), 2) for k, n in depths.items()}
    rows = []
    for name, z, receipt in HEADLINES:
        survives = [k for k, b in bars.items() if abs(z) >= b]
        rows.append({"stat": name, "abs_z": z, "survives_at": survives or ["none"], "receipt": receipt})
    out = {"method": "E[max|Z|] = (1-g)*Phi^-1(1-1/N) + g*Phi^-1(1-1/(N*e)), g=0.5772",
           "census": c, "deflation_bars": bars, "headlines": rows,
           "spa_status": "BLOCKED: Hansen SPA needs per-arm return series; the pattern-arm "
                         "series are not regenerable from the frozen manifest (review F-1, 2026-09-28). "
                         "Recorded, not swept away.",
           "generated_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()}
    (HERE / "RESULT_2026-09-28.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({"bars": bars, "headlines": [(r["stat"], r["abs_z"], r["survives_at"]) for r in rows]},
                     indent=1))


if __name__ == "__main__":
    main()
