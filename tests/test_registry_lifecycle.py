import datetime as _dt

from engine.registry_loader import validate_evidence, _FORWARD_BAR

BAR = _FORWARD_BAR  # {'min_n': 15, 'go_exp': 0.50}
_PROMOTE = {"gate_decision": {"final_state": "PROMOTE_TO_FORWARD_TEST"}}


def test_non_loadable_status_needs_no_evidence():
    assert validate_evidence({"status": "CANDIDATE"}, {}, BAR) == []


def test_shadow_requires_promote_gate_decision():
    assert validate_evidence({"status": "SHADOW"}, {"evidence": {}}, BAR)          # missing -> reasons
    assert validate_evidence({"status": "SHADOW"}, {"evidence": _PROMOTE}, BAR) == []


def test_approved_requires_promote_and_forward_go():
    ev = {"evidence": dict(_PROMOTE,
          forward={"verdict": "GO", "n": 17, "exp_pct": 0.63})}
    assert validate_evidence({"status": "APPROVED"}, ev, BAR) == []


def test_approved_with_promote_but_no_forward_fails():
    reasons = validate_evidence({"status": "APPROVED"}, {"evidence": _PROMOTE}, BAR)
    assert reasons and any("forward" in r for r in reasons)


def test_approved_forward_below_bar_fails():
    ev = {"evidence": dict(_PROMOTE,
          forward={"verdict": "GO", "n": 10, "exp_pct": 0.63})}   # n < 15
    reasons = validate_evidence({"status": "APPROVED"}, ev, BAR)
    assert reasons and any("below bar" in r for r in reasons)


def test_forward_bar_matches_phase5_rule():
    # Tests may import research/; engine/ may not. Lock the mirrored bar so it can
    # never drift from the canonical Phase 5 rule.
    from research.studies.phase5_tracker import RULE
    assert _FORWARD_BAR['min_n'] == RULE['min_n']
    assert _FORWARD_BAR['go_exp'] == RULE['go_exp']


from engine.registry_loader import load_registry, _LIFECYCLE_DEBT


def test_real_registry_loads_with_nr7_as_debt_not_violation():
    r = load_registry()
    # governance unchanged: NR7_BULL still loads
    assert any(e['id'] == 'NR7_BULL' for e in r['entries'])
    # it is classified as known debt, NOT a live violation
    debt_ids = {d[0] for d in r['debt']}
    viol_ids = {v[0] for v in r['violations']}
    assert 'NR7_BULL_v1' in debt_ids
    assert 'NR7_BULL_v1' not in viol_ids
    assert r['violations'] == []          # no un-grandfathered violations today


def test_nr7_bull_is_the_only_grandfathered_entry():
    assert set(_LIFECYCLE_DEBT) == {("NR7_BULL", 1)}


def test_no_ungrandfathered_lifecycle_violations_in_real_registry():
    """CI gate: any SHADOW/APPROVED entry lacking a valid receipt fails the build,
    unless explicitly grandfathered. New bad approvals cannot merge."""
    r = load_registry()
    assert r['violations'] == [], f"un-grandfathered lifecycle violations: {r['violations']}"


def test_a_new_noncompliant_approved_entry_would_fail():
    # Prove the door is shut: a fabricated APPROVED entry with no forward GO,
    # not in the allowlist, yields violation reasons.
    fabricated = {"status": "APPROVED", "id": "FAKE_EDGE", "version": 1}
    reasons = validate_evidence(fabricated, {"evidence":
        {"gate_decision": {"final_state": "PROMOTE_TO_FORWARD_TEST"}}}, _FORWARD_BAR)
    assert reasons and ("FAKE_EDGE", 1) not in _LIFECYCLE_DEBT


def test_grandfathered_debt_not_past_deadline():
    """Once a debt entry's remediation deadline passes, this fails until it is
    remediated (compliant receipt) or demoted + removed from the allowlist."""
    today = _dt.date.today()
    overdue = [k for k, v in _LIFECYCLE_DEBT.items()
               if _dt.date.fromisoformat(v['deadline']) < today]
    assert overdue == [], f"lifecycle debt past remediation deadline: {overdue}"


from engine.registry_loader import startup_summary, _reset_cache


def test_startup_summary_reports_debt_and_violations():
    _reset_cache()
    s = startup_summary()
    assert "1 debt" in s          # NR7_BULL
    assert "0 unverified" in s     # no live violations


# ── T7 invariant #6: Registry -> Strategy identity -> Production
# implementation lineage. Every loadable registry entry's strategy_fn must
# be a real, live-checker-backed production strategy -- the same audit-C-1
# bug pattern (a name selectable with no checker behind it) one layer up:
# tests/test_strategy_specs.py::test_regime_map_strategies_are_live_capable
# already proves this for the regime map; nothing proved it for the Edge
# Registry itself before this test. ─────────────────────────────────────

from engine.registry_loader import admission_path


def test_admission_path_unregistered_strategy():
    assert admission_path("Totally Made Up Strategy") == "UNREGISTERED"


def test_admission_path_approved_via_debt_grandfather():
    # Real production registry: NR7_BULL is APPROVED but only loads via the
    # _LIFECYCLE_DEBT grandfather exception (no clean evidence receipt).
    _reset_cache()
    assert admission_path("NR7 Breakout") == "APPROVED_DEBT"
    _reset_cache()


def test_every_registry_entry_strategy_fn_has_a_live_production_checker():
    from engine.strategy_specs import SPECS
    from engine.strategies import _CHECKER_DISPATCH
    r = load_registry()
    for e in r['entries']:
        name = e['strategy_fn']
        assert name in SPECS, f"{e['id']}_v{e['version']}: {name!r} not in SPECS"
        assert SPECS[name].live_checker, \
            f"{e['id']}_v{e['version']}: {name!r} has no live checker"
        assert name in _CHECKER_DISPATCH, \
            f"{e['id']}_v{e['version']}: {name!r} missing from _CHECKER_DISPATCH"
