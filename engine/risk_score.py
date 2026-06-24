# engine/risk_score.py
"""Composite market risk score combining all crash sensors.

Weights (macro_idx.md design spec):
  VPIN          30%
  Accdist       20%
  Breadth       20%
  Technicals    15%
  Foreign flow  15%

Score 0-100: 0=safe, 100=maximum risk.
Tiers: GREEN <30 | YELLOW 30-50 | ORANGE 51-70 | RED 71-85 | CRITICAL >85
"""

# ── Per-sensor risk functions (return 0-100) ─────────────────────────────────

_VPIN_LABEL_SCORE = {
    'GREEN': 5, 'YELLOW': 25, 'ORANGE': 55, 'RED': 75, 'CRITICAL': 95,
    'INSUFFICIENT_DATA': 0,
}

_ACCDIST_LABEL_SCORE = {
    'STRONG_ACCUMULATION': 5, 'ACCUMULATION': 15, 'NEUTRAL': 40,
    'DISTRIBUTION': 65, 'STRONG_DISTRIBUTION': 85,
}

_BREADTH_LABEL_SCORE = {
    'BULL_MARKET': 10, 'NEUTRAL': 40, 'WEAK': 65, 'BEAR_MARKET': 85,
    'INSUFFICIENT_DATA': 0,
}

_TECH_LABEL_SCORE = {
    'UPTREND': 10, 'NEUTRAL': 35, 'DOWNTREND': 65, 'BEARISH_TREND': 90,
    'INSUFFICIENT_DATA': 0,
}


def _vpin_risk(summary: dict) -> float:
    base = _VPIN_LABEL_SCORE.get(summary.get('label', ''), 40)
    # Boost from the extreme tail. Under BVC VPIN tops out ~0.6-0.7, so the toxic
    # tail is "share of names above 0.6" (the legacy pct_above_095 is ~0 under BVC).
    pct_06 = summary.get('pct_above_06')
    if pct_06 is None:  # back-compat with old saturated summaries
        pct_06 = summary.get('pct_above_095') or 0.0
    boost = min(pct_06 * 0.5, 15)  # up to +15 pts
    return min(base + boost, 100)


def _accdist_risk(summary: dict) -> float:
    base = _ACCDIST_LABEL_SCORE.get(summary.get('label', ''), 40)
    dist_pct = summary.get('dist_pct') or 0.0
    # Additional boost from dist_pct above 60%
    boost = max(dist_pct - 60, 0) * 0.5
    return min(base + boost, 100)


def _breadth_risk(summary: dict) -> float:
    base = _BREADTH_LABEL_SCORE.get(summary.get('label', ''), 40)
    pct_adv = summary.get('pct_advancing') or 50.0
    # Penalty for very low advancing
    penalty = max(35 - pct_adv, 0) * 0.8
    return min(base + penalty, 100)


def _technicals_risk(tech: dict) -> float:
    base = _TECH_LABEL_SCORE.get(tech.get('label', ''), 35)
    if tech.get('death_cross'):
        base = min(base + 10, 100)
    if tech.get('lower_high'):
        base = min(base + 10, 100)
    n_breaks = len(tech.get('support_breaks') or [])
    base = min(base + n_breaks * 8, 100)
    return float(base)


def _foreign_flow_risk(net_5d) -> float:
    if net_5d is None:
        return 40.0
    # Scale: -10B IDR → 90, 0 → 40, +5B → 10
    if net_5d >= 5_000_000_000:
        return 10.0
    elif net_5d >= 0:
        return 40.0 - (net_5d / 5_000_000_000) * 30
    else:
        clamped = max(net_5d, -10_000_000_000)
        return 40.0 + (-clamped / 10_000_000_000) * 55


def _score_to_tier(score: float) -> str:
    if score > 85:
        return 'CRITICAL'
    elif score > 70:
        return 'RED'
    elif score > 50:
        return 'ORANGE'
    elif score > 30:
        return 'YELLOW'
    return 'GREEN'


# ── Public API ────────────────────────────────────────────────────────────────

def compute_market_risk_score(
    vpin_summary: dict,
    accdist_summary: dict,
    breadth_summary: dict,
    technicals: dict,
    foreign_net_5d,
) -> dict:
    """Compute composite market risk score from sensor summaries.

    Args:
        vpin_summary    : from get_market_vpin_summary()
        accdist_summary : from get_market_accdist_summary()
        breadth_summary : from get_market_breadth()
        technicals      : from detect_ihsg_technicals()
        foreign_net_5d  : 5-day net foreign flow in IDR (negative = outflow)

    Returns dict with: score (0-100), tier, label (=tier), components dict.
    """
    c_vpin = _vpin_risk(vpin_summary)
    c_accdist = _accdist_risk(accdist_summary)
    c_breadth = _breadth_risk(breadth_summary)
    c_tech = _technicals_risk(technicals)
    c_foreign = _foreign_flow_risk(foreign_net_5d)

    score = round(
        c_vpin * 0.30
        + c_accdist * 0.20
        + c_breadth * 0.20
        + c_tech * 0.15
        + c_foreign * 0.15,
        1,
    )
    score = max(0.0, min(100.0, score))
    tier = _score_to_tier(score)

    return {
        'score': score,
        'tier': tier,
        'label': tier,
        'components': {
            'vpin': round(c_vpin, 1),
            'accdist': round(c_accdist, 1),
            'breadth': round(c_breadth, 1),
            'technicals': round(c_tech, 1),
            'foreign_flow': round(c_foreign, 1),
        },
    }
