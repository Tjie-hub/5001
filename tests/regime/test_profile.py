from research.regime.profile import cell_verdict


def _trades_with_net(mean_net, n, spread=0.0):
    """Deterministic trade dicts whose net% is a fixed sequence with the requested
    mean. We hand pre-computed nets through the 'net' shortcut the verdict accepts."""
    nets = [mean_net - spread, mean_net + spread] * (n // 2)
    if len(nets) < n:
        nets.append(mean_net)
    return [{"net": v} for v in nets]


def test_present_when_ci_lower_bound_above_zero():
    trades = _trades_with_net(1.2, 200, spread=0.3)
    v = cell_verdict(trades, min_n=100, ci_level=0.95, n_boot=2000, seed=1)
    assert v["verdict"] == "PRESENT"
    assert v["ci_low"] > 0


def test_reversed_when_ci_upper_bound_below_zero():
    trades = _trades_with_net(-1.2, 200, spread=0.3)
    v = cell_verdict(trades, min_n=100, ci_level=0.95, n_boot=2000, seed=1)
    assert v["verdict"] == "REVERSED"
    assert v["ci_high"] < 0


def test_absent_when_ci_straddles_zero():
    trades = _trades_with_net(0.0, 200, spread=5.0)
    v = cell_verdict(trades, min_n=100, ci_level=0.95, n_boot=2000, seed=1)
    assert v["verdict"] == "ABSENT"
    assert v["ci_low"] < 0 < v["ci_high"]


def test_insufficient_sample_is_absent_flagged():
    trades = _trades_with_net(1.2, 40, spread=0.3)
    v = cell_verdict(trades, min_n=100, ci_level=0.95, n_boot=2000, seed=1)
    assert v["verdict"] == "ABSENT"
    assert v["insufficient"] is True
