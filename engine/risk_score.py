# engine/risk_score.py
"""Composite market risk score combining all crash sensors.

Weights (macro_idx.md design spec):
  VPIN                          30%
  Accdist                       20%
  Breadth                       20%
  Technicals                    15%
  Foreign-owned brokerage flow  15%

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


def _foreign_owned_brokerage_flow_risk(net_5d) -> float:
    """net_5d: signed IDR net (SUM(value)) of broker_flow rows where investor_type='Asing'
    — i.e. flow through foreign-owned brokerages. This is brokerage ownership, not
    end-investor identity (D1: docs/research_programs/P-M/D1_D2_PRODUCTION_SEMANTIC_AUDIT_2026-09-10.md)."""
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

# Live-event lessons (2026-10-16, MSCI consultation: IHSG opened -8.01% and halted, 2% of names advancing) -- the
# score read 57.2 ORANGE, LOWER than the day before, because (1) VPIN had no data yet and INSUFFICIENT_DATA scored
# 0 = "safe" at a 30% weight, and (2) the index's own move was not an input at all.
#   (1) a sensor without data is left out and the other weights are rescaled (missing is not safe);
#   (2) the IHSG day move (provisional bar allowed) sets a tier FLOOR: the market already told us.
# Floors are fixed by the IDX rulebook / the event, not fitted: -8% is the IDX trading-halt threshold.
SHOCK_FLOORS = ((-0.08, 'CRITICAL', 86.0), (-0.05, 'RED', 71.0), (-0.03, 'ORANGE', 51.0))
_WEIGHTS = {'vpin': 0.30, 'accdist': 0.20, 'breadth': 0.20, 'technicals': 0.15, 'foreign_flow': 0.15}

# Coverage gate (2026-10-22, brief B): CRITICAL/RED claim "the market is in trouble NOW", so they
# need live corroboration — at least MIN_LIVE_FLOW_BREADTH of the four flow/breadth sensors. The
# 10-21 09:05 pre-open scan had only the 5-day foreign-owned flow alive next to a slow BEARISH_TREND
# read; the rescale handed technicals half the weight and the day opened at 97.5 CRITICAL while IHSG
# sat +0.36% (score 97.5 -> 74.5 -> 96.0 -> 96.0 -> 94.0 all day). With fewer live sensors the tier
# caps at ORANGE and the result is labelled. The IHSG shock floor overrides this gate: a real -8% day
# is CRITICAL whatever the sensors say (the 10-16 -8.01% event reads CRITICAL, unchanged).
FLOW_BREADTH_SENSORS = ('vpin', 'accdist', 'breadth', 'foreign_flow')
MIN_LIVE_FLOW_BREADTH_FOR_TOP_TIERS = 2  # reasoning-set, not fitted: two independent live readings


def ihsg_last_move(conn, date_str: str):
    """(bar_date, move) for the latest IHSG bar on or before date_str (a provisional intraday bar counts); move is
    the close-to-close change as a fraction. (None, None) without two bars."""
    rows = conn.execute("SELECT date, close FROM ohlcv WHERE ticker='IHSG' AND date<=? ORDER BY date DESC LIMIT 2",
                        (date_str,)).fetchall()
    if len(rows) < 2 or not rows[0][1] or not rows[1][1]:
        return None, None
    return str(rows[0][0])[:10], rows[0][1] / rows[1][1] - 1


def ihsg_move(conn, date_str: str):
    """IHSG close-to-close change of date_str's OWN bar (a provisional intraday bar counts), as a fraction; None
    when date_str has no IHSG bar yet.

    Until 2026-10-21 this took the latest bar on or before date_str. The 09:05 scan runs before the first intraday
    IHSG bar, so it reported the PREVIOUS session's move as "IHSG today" and applied its shock floor: 10-19 09:05
    showed Friday's -8.01%, and 10-20 09:05 showed Monday's -4.46% while IHSG was opening about +2%."""
    bar_date, move = ihsg_last_move(conn, date_str)
    return move if bar_date == str(date_str)[:10] else None


def compute_market_risk_score(
    vpin_summary: dict,
    accdist_summary: dict,
    breadth_summary: dict,
    technicals: dict,
    foreign_net_5d,
    ihsg_day_move=None,
    ihsg_prev=None,
) -> dict:
    """Compute composite market risk score from sensor summaries.

    Args:
        vpin_summary    : from get_market_vpin_summary()
        accdist_summary : from get_market_accdist_summary()
        breadth_summary : from get_market_breadth()
        technicals      : from detect_ihsg_technicals()
        foreign_net_5d  : 5-day net IDR flow through foreign-owned brokerages
                          (investor_type='Asing'; negative = net sell). This is brokerage
                          ownership, not end-investor identity — see D1 in
                          docs/research_programs/P-M/D1_D2_PRODUCTION_SEMANTIC_AUDIT_2026-09-10.md
        ihsg_day_move   : TODAY's IHSG move (ihsg_move); sets the shock floor
        ihsg_prev       : (bar_date, move) of the last session, for display only when today has no IHSG bar yet
                          (pre-open); never sets a floor

    Returns dict with: score (0-100), tier, label (=tier), components dict, and ihsg_prev_date when the
    previous-session move is reported instead of today's.
    """
    missing = lambda d: (d or {}).get('label') == 'INSUFFICIENT_DATA'
    comps = {
        'vpin': None if missing(vpin_summary) else _vpin_risk(vpin_summary),
        # 0 tickers classified = no flow yet (pre-open, outage): missing, not "NEUTRAL" (review 2026-10-16)
        'accdist': None if (missing(accdist_summary) or (accdist_summary or {}).get('total') == 0)
        else _accdist_risk(accdist_summary),
        'breadth': None if missing(breadth_summary) else _breadth_risk(breadth_summary),
        'technicals': None if missing(technicals) else _technicals_risk(technicals),
        'foreign_flow': _foreign_owned_brokerage_flow_risk(foreign_net_5d),
    }
    present = {k: v for k, v in comps.items() if v is not None}
    wsum = sum(_WEIGHTS[k] for k in present)
    score = round(sum(v * _WEIGHTS[k] for k, v in present.items()) / wsum, 1) if wsum else 40.0
    score = max(0.0, min(100.0, score))

    shock = None
    if ihsg_day_move is not None:
        for cut, _tier, floor in SHOCK_FLOORS:
            if ihsg_day_move <= cut:
                shock = _tier
                score = max(score, floor)
                break
    tier = _score_to_tier(score)

    # Coverage gate (see FLOW_BREADTH_SENSORS above): without enough LIVE flow/breadth sensors a
    # top tier is a slow/no-data artefact, not today's market. The shock floor (shock is not None)
    # overrides the cap — the index already told us.
    live_fb = sum(1 for k in FLOW_BREADTH_SENSORS if comps.get(k) is not None)
    partial = live_fb < MIN_LIVE_FLOW_BREADTH_FOR_TOP_TIERS
    capped = partial and shock is None and tier in ('CRITICAL', 'RED')
    if capped:
        tier = 'ORANGE'

    out_comps = {k: (round(v, 1) if v is not None else None) for k, v in comps.items()}
    prev_date = None
    if ihsg_day_move is not None:
        out_comps['ihsg_move_pct'] = round(ihsg_day_move * 100, 2)
    elif ihsg_prev and ihsg_prev[0] and ihsg_prev[1] is not None:
        prev_date = ihsg_prev[0]
        out_comps['ihsg_prev_move_pct'] = round(ihsg_prev[1] * 100, 2)
    out = {
        'score': score,
        'tier': tier,
        'label': tier,
        'shock_floor': shock,
        'components': out_comps,
    }
    if partial:
        out['coverage'] = (
            f"partial sensors: {live_fb}/4 flow-breadth live"
            + ("; tier capped at ORANGE" if capped else "")
        )
    if prev_date:
        out['ihsg_prev_date'] = prev_date
    return out
