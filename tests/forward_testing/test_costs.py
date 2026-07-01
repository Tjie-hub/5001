"""Costs value object + apply_costs (mirrors engine.strategies constants)."""
from forward_testing.positions.costs import Costs, apply_costs


def test_default_costs_match_engine():
    c = Costs()
    assert c.commission_buy == 0.0015
    assert c.commission_sell == 0.0025
    assert c.slippage == 0.001


def test_apply_costs_buy_adds_sell_subtracts():
    c = Costs()
    assert round(apply_costs(100.0, "BUY", c), 6) == round(100.0 * (1 + 0.0015 + 0.001), 6)
    assert round(apply_costs(100.0, "SELL", c), 6) == round(100.0 * (1 - 0.0025 - 0.001), 6)


def test_zero_costs_pass_through():
    z = Costs.zero()
    assert apply_costs(123.456, "BUY", z) == 123.456
    assert apply_costs(123.456, "SELL", z) == 123.456
