"""M2: STRATEGY_FUNCS lives on the shared floor (engine.strategies), so the
dashboard and research both import it without crossing the boundary."""


def test_strategy_funcs_importable_from_strategies():
    from engine.strategies import STRATEGY_FUNCS
    assert len(STRATEGY_FUNCS) == 14
    assert "NR7 Breakout" in STRATEGY_FUNCS
    assert callable(STRATEGY_FUNCS["NR7 Breakout"])
