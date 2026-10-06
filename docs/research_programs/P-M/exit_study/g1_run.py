"""G1 one-shot runner for the exit study — executed ONCE, 2026-10-06, after the
owner approved G0-ter (research/exit-study-2026-10 @ c483886).

NOT one of the three frozen artifacts (the freeze covers PREDECLARATION.md,
exit_study.py, test_pit_exit_study.py). This runner only orchestrates the
frozen evaluate() — it introduces no settings of its own: the universe mask,
indicator set and seed RNG are built exactly as census_g0() builds them.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

if os.environ.get("EXIT_STUDY_G1_APPROVED") != "1":
    raise SystemExit("G1 is gated: set EXIT_STUDY_G1_APPROVED=1 only after "
                     "owner/planner approval of the frozen G0.")

import exit_study as E  # noqa: E402
from data.db import connect as db_connect  # noqa: E402

FROZEN_NAMES = ("PREDECLARATION.md", "exit_study.py", "test_pit_exit_study.py")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def to_pure(o):
    """JSON-safe conversion; non-finite floats become None (paired_t can be
    +/-inf when the paired differences have zero variance)."""
    if isinstance(o, dict):
        return {str(k): to_pure(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [to_pure(v) for v in o]
    if isinstance(o, (bool, np.bool_)):
        return bool(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, (float, np.floating)):
        v = float(o)
        return v if np.isfinite(v) else None
    if o is None or isinstance(o, str):
        return o
    return str(o)


def main() -> None:
    t0 = time.time()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    frozen = {name: sha256_file(HERE / name) for name in FROZEN_NAMES}
    sidecar = {}
    for line in (HERE / "PREDECLARATION.sha256").read_text().strip().splitlines():
        h, n = line.split()
        sidecar[n] = h
    for name, h in frozen.items():
        if sidecar.get(name) != h:
            raise SystemExit(f"freeze check FAILED for {name}: {h} != {sidecar.get(name)}")
    print("freeze check: all three OK")

    P = E.load_panel()
    C = P["close"]
    adv20 = (C * P["volume"]).rolling(20, min_periods=20).mean()
    owner = adv20 >= E.ADV20_MIN                      # exactly the census mask
    I_by_stock = {}
    for tk in C.columns:
        if C[tk].notna().sum() >= E.PIVOT_WINDOW + 2 * E.PIVOT_HALF + 2:
            I_by_stock[tk] = E.stock_indicators(
                P["open"][tk].values.astype(float),
                P["high"][tk].values.astype(float),
                P["low"][tk].values.astype(float),
                C[tk].values.astype(float),
                P["volume"][tk].values.astype(float))
    print("indicators built:", len(I_by_stock))

    result = E.evaluate(P, I_by_stock, {"owner_adv20_10bn": owner})
    with db_connect(read_only=True) as conn:
        result["dataset_fingerprint"] = E.dataset_fingerprint(conn)
    result["git_commit"] = E.git_commit()
    result["frozen_artifact_sha256"] = frozen
    result["generated_utc"] = datetime.now(timezone.utc).isoformat()
    result["runtime_seconds"] = round(time.time() - t0, 1)
    result["gates"] = {
        "env": "EXIT_STUDY_G1_APPROVED=1 (owner approval of G0-ter c483886, 2026-10-06)",
        "single_run": True,
        "data_access": "read-only (PKLs + mode=ro DB for the fingerprint)",
    }

    out = HERE / f"RESULT_{stamp}.json"
    out.write_text(json.dumps(to_pure(result), indent=1) + "\n")
    print("WROTE", out.name)
    print("populations:", {k: v["n_trades"] for k, v in result["populations"].items()})
    print("runtime_s:", result["runtime_seconds"])


if __name__ == "__main__":
    main()
