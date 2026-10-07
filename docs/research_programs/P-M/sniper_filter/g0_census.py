"""G0 census runner — COUNTS ONLY (HYP-PM-0016 draft).

Writes CENSUS_G0.json: setup/fill counts, event counters, feature NaN and
rank-fallback counts, the dataset fingerprint vs G1FIX's, and the frozen
deflation bar. NO outcome, NO R, NO return of any kind is computed, printed
or stored (PREDECLARATION §2/§9).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import sniper_filter as SF  # noqa: E402


def main() -> None:
    t0 = datetime.now(timezone.utc)
    out = SF.census_g0()
    out["generated_utc"] = t0.isoformat()
    out["runtime_minutes"] = round(
        (datetime.now(timezone.utc) - t0).total_seconds() / 60.0, 1)
    path = HERE / "CENSUS_G0.json"
    path.write_text(json.dumps(out, indent=1) + "\n")
    print("WROTE", path.name)
    print("fingerprint:", out["dataset_fingerprint"]["sha256"][:16],
          "| matches G1FIX:", out["fingerprint_matches_g1fix"])
    print("filled setups:", out["n_filled_setups"], "| by era:", out["n_filled_by_era"])
    print("events:", out["events"])
    print("census N:", out["census_n"], "| exact bar:",
          out["deflection_bar_exact"], "-> frozen", out["deflection_bar_frozen"])


if __name__ == "__main__":
    main()
