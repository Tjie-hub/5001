"""Tests for C6 — multi-sensor composite market risk score.

Combines VPIN (30%), accdist (20%), breadth (20%), technicals (15%),
foreign flow (15%) into a 0-100 score with GREEN/YELLOW/ORANGE/RED/CRITICAL tiers.
"""
from engine.risk_score import compute_market_risk_score


# ── Output shape ──────────────────────────────────────────────────────────────

def test_returns_required_keys():
    result = compute_market_risk_score(
        vpin_summary={'label': 'GREEN', 'avg_vpin': 0.5, 'pct_above_095': 0.0},
        accdist_summary={'label': 'NEUTRAL', 'dist_pct': 40.0},
        breadth_summary={'label': 'NEUTRAL', 'pct_advancing': 50.0},
        technicals={'label': 'NEUTRAL', 'death_cross': False, 'lower_high': False, 'support_breaks': []},
        foreign_net_5d=0,
    )
    required = {'score', 'tier', 'components', 'label'}
    assert required.issubset(result.keys()), f"Missing: {required - result.keys()}"


def test_score_is_between_0_and_100():
    result = compute_market_risk_score(
        vpin_summary={'label': 'CRITICAL', 'avg_vpin': 0.99, 'pct_above_095': 90.0},
        accdist_summary={'label': 'STRONG_DISTRIBUTION', 'dist_pct': 80.0},
        breadth_summary={'label': 'BEAR_MARKET', 'pct_advancing': 15.0},
        technicals={'label': 'BEARISH_TREND', 'death_cross': True, 'lower_high': True, 'support_breaks': ['6200', '6000']},
        foreign_net_5d=-5_000_000_000,
    )
    assert 0 <= result['score'] <= 100


# ── CRITICAL scenario ─────────────────────────────────────────────────────────

def test_all_sensors_red_produces_critical_tier():
    """All sensors at maximum risk → CRITICAL tier (score > 85)."""
    result = compute_market_risk_score(
        vpin_summary={'label': 'CRITICAL', 'avg_vpin': 0.99, 'pct_above_095': 95.0},
        accdist_summary={'label': 'STRONG_DISTRIBUTION', 'dist_pct': 85.0},
        breadth_summary={'label': 'BEAR_MARKET', 'pct_advancing': 10.0},
        technicals={'label': 'BEARISH_TREND', 'death_cross': True, 'lower_high': True, 'support_breaks': ['6200', '6000', '5500']},
        foreign_net_5d=-10_000_000_000,
    )
    assert result['tier'] == 'CRITICAL', f"score={result['score']} tier={result['tier']}"
    assert result['score'] > 85


# ── GREEN scenario ────────────────────────────────────────────────────────────

def test_all_sensors_green_produces_green_tier():
    """All sensors at minimal risk → GREEN tier (score < 30)."""
    result = compute_market_risk_score(
        vpin_summary={'label': 'GREEN', 'avg_vpin': 0.4, 'pct_above_095': 0.0},
        accdist_summary={'label': 'ACCUMULATION', 'dist_pct': 20.0},
        breadth_summary={'label': 'BULL_MARKET', 'pct_advancing': 75.0},
        technicals={'label': 'UPTREND', 'death_cross': False, 'lower_high': False, 'support_breaks': []},
        foreign_net_5d=3_000_000_000,
    )
    assert result['tier'] == 'GREEN', f"score={result['score']} tier={result['tier']}"
    assert result['score'] < 30


# ── Tier boundaries ───────────────────────────────────────────────────────────

def test_tier_labels_are_valid():
    result = compute_market_risk_score(
        vpin_summary={'label': 'ORANGE', 'avg_vpin': 0.85, 'pct_above_095': 50.0},
        accdist_summary={'label': 'DISTRIBUTION', 'dist_pct': 65.0},
        breadth_summary={'label': 'WEAK', 'pct_advancing': 35.0},
        technicals={'label': 'DOWNTREND', 'death_cross': True, 'lower_high': False, 'support_breaks': ['6200']},
        foreign_net_5d=-1_000_000_000,
    )
    valid_tiers = {'GREEN', 'YELLOW', 'ORANGE', 'RED', 'CRITICAL'}
    assert result['tier'] in valid_tiers, f"invalid tier: {result['tier']}"


# ── Component breakdown ───────────────────────────────────────────────────────

def test_components_dict_has_sensor_keys():
    result = compute_market_risk_score(
        vpin_summary={'label': 'GREEN', 'avg_vpin': 0.5, 'pct_above_095': 0.0},
        accdist_summary={'label': 'NEUTRAL', 'dist_pct': 40.0},
        breadth_summary={'label': 'NEUTRAL', 'pct_advancing': 50.0},
        technicals={'label': 'NEUTRAL', 'death_cross': False, 'lower_high': False, 'support_breaks': []},
        foreign_net_5d=0,
    )
    comp = result['components']
    assert 'vpin' in comp
    assert 'accdist' in comp
    assert 'breadth' in comp
    assert 'technicals' in comp
    assert 'foreign_flow' in comp


def test_vpin_critical_raises_score_significantly():
    """VPIN CRITICAL alone should push score into at least ORANGE territory."""
    base = compute_market_risk_score(
        vpin_summary={'label': 'GREEN', 'avg_vpin': 0.4, 'pct_above_095': 0.0},
        accdist_summary={'label': 'NEUTRAL', 'dist_pct': 40.0},
        breadth_summary={'label': 'NEUTRAL', 'pct_advancing': 50.0},
        technicals={'label': 'NEUTRAL', 'death_cross': False, 'lower_high': False, 'support_breaks': []},
        foreign_net_5d=0,
    )
    critical = compute_market_risk_score(
        vpin_summary={'label': 'CRITICAL', 'avg_vpin': 0.99, 'pct_above_095': 95.0},
        accdist_summary={'label': 'NEUTRAL', 'dist_pct': 40.0},
        breadth_summary={'label': 'NEUTRAL', 'pct_advancing': 50.0},
        technicals={'label': 'NEUTRAL', 'death_cross': False, 'lower_high': False, 'support_breaks': []},
        foreign_net_5d=0,
    )
    assert critical['score'] > base['score'] + 20, (
        f"VPIN CRITICAL should raise score by >20pts: base={base['score']}, critical={critical['score']}"
    )


def test_missing_sensor_data_handled_gracefully():
    """None/empty sensor inputs → score still computed, no exception."""
    result = compute_market_risk_score(
        vpin_summary={'label': 'INSUFFICIENT_DATA', 'avg_vpin': None, 'pct_above_095': 0.0},
        accdist_summary={'label': 'NEUTRAL', 'dist_pct': 0.0},
        breadth_summary={'label': 'INSUFFICIENT_DATA', 'pct_advancing': 0.0},
        technicals={'label': 'INSUFFICIENT_DATA', 'death_cross': False, 'lower_high': False, 'support_breaks': []},
        foreign_net_5d=None,
    )
    assert isinstance(result['score'], (int, float))
    assert result['tier'] in {'GREEN', 'YELLOW', 'ORANGE', 'RED', 'CRITICAL'}
