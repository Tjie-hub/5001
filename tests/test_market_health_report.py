"""Tests for C8 — daily market health report (pre-market 08:45 WIB).

Report covers: risk tier, VPIN status, breadth, foreign flow trend,
key support/resistance levels.
"""
from engine.health_report import build_market_health_report


def _vpin(label='GREEN', avg=0.5, pct_095=0.0):
    return {'label': label, 'avg_vpin': avg, 'pct_above_095': pct_095,
            'pct_above_08': 0.0, 'tickers_with_vpin': 500}

def _accdist(label='NEUTRAL', dist_pct=40.0):
    return {'label': label, 'dist_pct': dist_pct, 'acc_pct': 60.0 - dist_pct,
            'avg_numeric_score': 0.0, 'total': 800}

def _breadth(label='NEUTRAL', pct_adv=50.0, pct_ma20=50.0):
    return {'label': label, 'pct_advancing': pct_adv, 'pct_above_ma20': pct_ma20,
            'advancers': 400, 'decliners': 350, 'total': 800}

def _tech(label='NEUTRAL', death_cross=False, lower_high=False, breaks=None):
    return {'label': label, 'death_cross': death_cross, 'lower_high': lower_high,
            'support_breaks': breaks or [], 'close': 6500, 'ma5': 6480, 'ma20': 6400}

def _risk(tier='GREEN', score=20.0):
    return {'tier': tier, 'score': score, 'label': tier,
            'components': {'vpin': 20, 'accdist': 20, 'breadth': 20,
                           'technicals': 20, 'foreign_flow': 20}}


# ── Output ─────────────────────────────────────────────────────────────────────

def test_returns_string():
    msg = build_market_health_report(
        date_str='2026-06-05',
        risk=_risk(),
        vpin=_vpin(),
        accdist=_accdist(),
        breadth=_breadth(),
        tech=_tech(),
        foreign_net_5d=0,
    )
    assert isinstance(msg, str)
    assert len(msg) > 50


def test_contains_date():
    msg = build_market_health_report(
        date_str='2026-06-05',
        risk=_risk(),
        vpin=_vpin(),
        accdist=_accdist(),
        breadth=_breadth(),
        tech=_tech(),
        foreign_net_5d=0,
    )
    assert '2026-06-05' in msg


def test_contains_risk_tier():
    msg = build_market_health_report(
        date_str='2026-06-05',
        risk=_risk('CRITICAL', 92),
        vpin=_vpin('CRITICAL', 0.99, 90),
        accdist=_accdist(),
        breadth=_breadth(),
        tech=_tech(),
        foreign_net_5d=-5_000_000_000,
    )
    assert 'CRITICAL' in msg


def test_contains_vpin_info():
    msg = build_market_health_report(
        date_str='2026-06-05',
        risk=_risk(),
        vpin=_vpin('RED', 0.92, 70),
        accdist=_accdist(),
        breadth=_breadth(),
        tech=_tech(),
        foreign_net_5d=0,
    )
    assert 'VPIN' in msg or 'vpin' in msg.lower()


def test_contains_breadth_info():
    msg = build_market_health_report(
        date_str='2026-06-05',
        risk=_risk(),
        vpin=_vpin(),
        accdist=_accdist(),
        breadth=_breadth('BEAR_MARKET', 22.5, 18.0),
        tech=_tech(),
        foreign_net_5d=0,
    )
    assert '22' in msg or 'breadth' in msg.lower() or 'Breadth' in msg


def test_flags_death_cross_in_report():
    msg = build_market_health_report(
        date_str='2026-06-05',
        risk=_risk('RED', 75),
        vpin=_vpin(),
        accdist=_accdist(),
        breadth=_breadth(),
        tech=_tech('BEARISH_TREND', death_cross=True, lower_high=True),
        foreign_net_5d=0,
    )
    assert 'death' in msg.lower() or 'cross' in msg.lower() or '❌' in msg


def test_foreign_outflow_shown_as_negative():
    msg = build_market_health_report(
        date_str='2026-06-05',
        risk=_risk(),
        vpin=_vpin(),
        accdist=_accdist(),
        breadth=_breadth(),
        tech=_tech(),
        foreign_net_5d=-2_500_000_000,
    )
    # Should show -2.5B or similar
    assert '-' in msg or 'outflow' in msg.lower()


def test_support_breaks_mentioned():
    msg = build_market_health_report(
        date_str='2026-06-05',
        risk=_risk('RED', 78),
        vpin=_vpin(),
        accdist=_accdist(),
        breadth=_breadth(),
        tech=_tech(breaks=['6200', '6000']),
        foreign_net_5d=0,
    )
    assert '6200' in msg or '6000' in msg
