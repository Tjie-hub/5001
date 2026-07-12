"""Per-strategy regime profile (spec §7, Flow A).

Groups collected trades into primary regime cells, assigns each a verdict
(PRESENT/ABSENT/REVERSED) from a bootstrap CI, then runs a secondary conditioning
check that may DECLARE a vol/liq axis for a (strategy, regime).
"""
from __future__ import annotations

import research.nr7_study as ns
from research import statistics as st


def _nets(trades):
    """Round-trip net % per trade. Accepts either raw prices (raw_entry/raw_exit,
    the live corpus shape) or a pre-computed 'net' (test shortcut)."""
    out = []
    for t in trades:
        if "net" in t:
            out.append(float(t["net"]))
        else:
            out.append(ns.round_trip_net_pct(t["raw_entry"], t["raw_exit"]))
    return out


def cell_verdict(trades, *, min_n: int, ci_level: float, n_boot: int, seed: int) -> dict:
    """Verdict for one regime cell. N is checked first; only then the CI sign."""
    nets = _nets(trades)
    n = len(nets)
    ci = st.bootstrap_ci(nets, n_boot=n_boot, ci=ci_level, seed=seed) if n >= 2 else {
        "point": float("nan"), "lo": float("nan"), "hi": float("nan"), "n": n}
    lo, hi = ci["lo"], ci["hi"]
    if n < min_n:
        verdict, insufficient = "ABSENT", True
    else:
        insufficient = False
        if lo > 0:
            verdict = "PRESENT"
        elif hi < 0:
            verdict = "REVERSED"
        else:
            verdict = "ABSENT"
    return {"verdict": verdict, "insufficient": insufficient, "n": n,
            "mean_net": ci["point"], "ci_low": lo, "ci_high": hi}
