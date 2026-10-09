"""Realised-spread cost model — the recommended replacement for D-059's
Abdi-Ranaldo spread on liquid names (Task A cost audit, 2026-10-09).

Baked from `cost_audit.py` / `COST_AUDIT.json` (ticks window 2026-04-18 →
2026-10-08, 115 sessions, 24.45M prints): the AR spread overstates the
realised Roll spread ~1.5–2.4× on ADV ≥ Rp 1bn names, worst in the most
liquid buckets — exactly the D-059 VERDICT's suspicion (Spearman vs Roll
only 0.2 for liquid names). Realised spreads do NOT widen on wide-range /
stress days for liquid names (AR's high/low term is what inflates there).

FROZEN API (call-shape matches how studies consume D-059's floored spread
`s = max(s_ar, tick_floor)`, so a future G0 can cite this module by the
sha256 sidecar next to it and swap one call):

    realised_spread(adv20_idr, daytype="normal"|"wide"|"stress") -> float
    d059_cost_realised(adv20_idr, sigma_d, daytype, q_idr=100e6, fees=0.005) -> float
        = fees + realised_spread(...) + 2*sigma_d*sqrt(q_idr/adv20_idr)

The impact and fee terms are D-059's, unchanged — only the spread estimate
is replaced. Day-type: "wide" = top decile of EW-market |r|; "stress" cells
are from the 3 D-079 stress days inside the ticks window (51 liquid names) —
treat them as a small-sample refinement of "wide", not an independent
estimate. Validity: ADV ≥ Rp 1bn only (the audit measured no sub-1bn cell);
raises ValueError below that.
"""
from __future__ import annotations

import math

FEES = 0.005
Q_DEFAULT = 100e6

# median realised (Roll-on-ticks) spreads per D-059 ADV bucket and day-type,
# each already >= the cell's median 1-tick floor (COST_AUDIT.json: cells).
REALISED_SPREAD = {
    "1-2bn":   {"normal": 0.007767, "wide": 0.008457, "stress": 0.011329},
    "2-5bn":   {"normal": 0.007782, "wide": 0.007436, "stress": 0.007688},
    "5-20bn":  {"normal": 0.007538, "wide": 0.007493, "stress": 0.007561},
    "20-100bn": {"normal": 0.006310, "wide": 0.004404, "stress": 0.004151},
    ">100bn":  {"normal": 0.004861, "wide": 0.003783, "stress": 0.003766},
}

BUCKETS = [("1-2bn", 1e9, 2e9), ("2-5bn", 2e9, 5e9), ("5-20bn", 5e9, 20e9),
           ("20-100bn", 20e9, 100e9), (">100bn", 100e9, math.inf)]


def _bucket(adv20_idr: float) -> str:
    if not (adv20_idr >= 1e9):
        raise ValueError("realised-spread table measured only for ADV >= Rp 1bn "
                         f"(got {adv20_idr:.3g}); use D-059 AR below that")
    for name, lo, hi in BUCKETS:
        if lo <= adv20_idr < hi:
            return name
    return ">100bn"


def realised_spread(adv20_idr: float, daytype: str = "normal") -> float:
    """Median realised (Roll-on-ticks, 1-tick-floored) spread as a fraction."""
    if daytype not in ("normal", "wide", "stress"):
        raise ValueError("daytype must be normal|wide|stress")
    return REALISED_SPREAD[_bucket(adv20_idr)][daytype]


def d059_cost_realised(adv20_idr: float, sigma_d: float, daytype: str = "normal",
                       q_idr: float = Q_DEFAULT, fees: float = FEES) -> float:
    """D-059 round trip with the AR spread replaced by the realised spread:
    fees + s_realised + 2*sigma_d*sqrt(q/adv20). Call-shape matches the study
    assembly (stress_reversal/outcomes.d059_cost, tender_floor.d059_cost)."""
    return fees + realised_spread(adv20_idr, daytype) + 2.0 * sigma_d * math.sqrt(q_idr / adv20_idr)
