"""Pre-registered GO/NO-GO rule (spec 2026-07-08) — frozen, boundary-tested."""
from research.studies.phase5_tracker import verdict, RULE


def test_rule_constants_frozen():
    assert RULE == {'min_n': 15, 'go_exp': 0.50, 'nogo_exp': 0.0,
                    'extend_n': 10, 'timebox_months': 6,
                    'start_date': '2026-07-08'}


def test_verdicts():
    assert verdict(n=14, exp=2.0) == 'INSUFFICIENT'
    assert verdict(n=15, exp=0.50) == 'GO'
    assert verdict(n=15, exp=0.0) == 'NO-GO'
    assert verdict(n=15, exp=-1.2) == 'NO-GO'
    assert verdict(n=15, exp=0.25) == 'EXTEND'
    assert verdict(n=25, exp=0.25) == 'EXTEND'
