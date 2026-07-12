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


def axis_declaration(cell_trades, *, axis: str, tier_key: str, min_gap_pct: float,
                     require_disjoint_ci: bool, ci_level: float, n_boot: int,
                     seed: int) -> dict:
    """Decide whether a regime cell's edge DEPENDS on a conditioning axis.

    Splits the cell's trades by their tier tag; the axis is DECLARED only if the
    HIGH-vs-LOW expectancy gap exceeds min_gap_pct and (optionally) the two tier
    CIs are disjoint. Never declared if either tier is empty."""
    from research.regime.taxonomy import AXIS_TIERS
    hi_label, lo_label = AXIS_TIERS[axis]
    hi = [t for t in cell_trades if t.get(tier_key) == hi_label]
    lo = [t for t in cell_trades if t.get(tier_key) == lo_label]
    if len(hi) < 2 or len(lo) < 2:
        return {"declared": False, "axis": axis, "gap": 0.0,
                "n_high": len(hi), "n_low": len(lo)}

    hi_ci = st.bootstrap_ci(_nets(hi), n_boot=n_boot, ci=ci_level, seed=seed)
    lo_ci = st.bootstrap_ci(_nets(lo), n_boot=n_boot, ci=ci_level, seed=seed)
    gap = abs(hi_ci["point"] - lo_ci["point"])
    disjoint = (hi_ci["lo"] > lo_ci["hi"]) or (lo_ci["lo"] > hi_ci["hi"])
    declared = gap > min_gap_pct and (disjoint or not require_disjoint_ci)
    return {"declared": bool(declared), "axis": axis, "gap": gap,
            "n_high": len(hi), "n_low": len(lo),
            "high_exp": hi_ci["point"], "low_exp": lo_ci["point"],
            "disjoint_ci": bool(disjoint)}
