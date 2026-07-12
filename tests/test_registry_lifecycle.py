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
