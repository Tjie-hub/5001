"""Phase 9 tests — costs must NEVER alter historical trigger geometry (§12).

Non-zero transaction costs may change net P&L only; entry/exit raw prices,
dates, sides, protective levels, conventions and the rule identity must be
bit-identical to the zero-cost run.
"""
from engine.historical.base import (BreakevenPolicy, ExitConvention, ExitKind,
                                    ProtectiveStopMode, SessionDefinition)
from engine.historical.costs import CostModel
from engine.historical.crabel_open_stretch import CrabelOpenStretchConfig
from engine.historical.crabel_open_stretch import run as run_a2
from engine.historical.kernel import AmbiguityPolicy, GapPolicy
from engine.historical.nr7 import TiePolicy


def _cfg():
    return CrabelOpenStretchConfig(
        nr7_tie_policy=TiePolicy.STRICT_LESS,
        session=SessionDefinition("09:00:00"),
        gap_policy=GapPolicy.FILL_AT_OPEN,
        ambiguity_policy=AmbiguityPolicy.PREFER_LONG,
        exit_convention=ExitConvention(ExitKind.MOC_AFTER_N_SESSIONS, 1),
        breakeven_move=BreakevenPolicy.NONE,
        protective_stop_mode=ProtectiveStopMode.ENABLED)


def _bars():
    from engine.historical.kernel import Bar
    bars = [Bar(date=f"2026-01-{i+1:02d}", open=100, high=102, low=92, close=101)
            for i in range(9)]
    bars.append(Bar(date="2026-01-10", open=100, high=102, low=97, close=101))  # NR7 setup
    bars.append(Bar(date="2026-01-11", open=100, high=110, low=96, close=105))  # execution
    bars.append(Bar(date="2026-01-12", open=104, high=106, low=100, close=104))
    return bars


def test_costs_do_not_move_triggers_levels_or_identity():
    zero = run_a2(_bars(), _cfg(), cost_model=CostModel.zero())
    heavy = run_a2(_bars(), _cfg(), cost_model=CostModel(0.015, 0.025, 0.010))

    assert zero.n_trades == heavy.n_trades == 1
    z, h = zero.trades[0], heavy.trades[0]
    assert (z.entry_date, z.exit_date) == (h.entry_date, h.exit_date)
    assert z.entry_price_raw == h.entry_price_raw          # trigger untouched
    assert z.exit_price_raw == h.exit_price_raw            # trigger untouched
    assert z.stop_level_raw == h.stop_level_raw            # level untouched
    assert z.side == h.side and z.exit_reason == h.exit_reason
    assert z.conventions == h.conventions
    assert zero.identity == heavy.identity                 # costs are not rule material
    assert z.pnl_raw == h.pnl_raw


def test_costs_change_only_net_pnl():
    zero = run_a2(_bars(), _cfg(), cost_model=CostModel.zero())
    heavy = run_a2(_bars(), _cfg(), cost_model=CostModel(0.015, 0.025, 0.010))
    z, h = zero.trades[0], heavy.trades[0]
    assert z.pnl_net == z.pnl_raw
    assert h.pnl_net != h.pnl_raw
    assert h.pnl_net < z.pnl_net                           # long: costs strictly reduce net


def test_cost_model_default_is_zero():
    assert CostModel.zero().buy_fill(100.0) == 100.0
    assert CostModel.zero().sell_fill(100.0) == 100.0
