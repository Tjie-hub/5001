"""P-3 regression: the Liquidity Sweep shadow cohort must have a bounded
10-session evaluation horizon, and must remain SHADOW ONLY.

Before this fix its ExitPolicy set no trail and no hold_days, so a position that
hit neither SL nor TP never exited (JSMR: 43 hold-days, vs a 10-day cap on every
`distribution` position). An unbounded cohort has no measurable horizon.
"""
import pytest

from engine.exits.policy import ExitPolicyRegistry

STRATEGY = "Liquidity Sweep"
HORIZON_SESSIONS = 10


class TestHorizon:

    def test_configured_horizon_is_ten_sessions(self):
        assert ExitPolicyRegistry().get(STRATEGY).hold_days == HORIZON_SESSIONS

    def test_policy_is_bounded_by_something(self):
        """Belt and braces: a policy with neither a trail nor a time cap can run
        forever whenever price sits between SL and TP."""
        p = ExitPolicyRegistry().get(STRATEGY)
        assert p.hold_days is not None or p.trail_enable or p.trail_atr_mult

    def test_entry_side_of_the_policy_is_untouched(self):
        """P-3 changes the horizon only. Thresholds must not move."""
        p = ExitPolicyRegistry().get(STRATEGY)
        assert (p.sl_mult, p.tp_mult, p.min_rr) == (1.0, 2.5, 2.5)
        assert p.no_sl is False and p.fixed_levels is False

    def test_kernel_exits_on_time_when_no_level_is_hit(self):
        """The cap has to actually fire, not merely be configured."""
        from engine.exits.evaluator import Bar, PositionView, evaluate_exit
        p = ExitPolicyRegistry().get(STRATEGY)
        lv = p.initial_levels("LONG", 1000.0, 20.0)
        # a bar that drifts between SL and TP -- no level touched
        bar = Bar(date="2026-09-03", open=1000.0, high=1005.0, low=998.0,
                  close=1001.0)
        view = PositionView(policy=p, direction="LONG", entry=1000.0, atr=20.0,
                            highest_seen=1005.0, lowest_seen=998.0,
                            hold_days=HORIZON_SESSIONS,
                            sl_price=lv.sl_price, tp_price=lv.tp_price)
        d = evaluate_exit(view, bar)
        assert d is not None and d.reason == "TIME"

    def test_below_the_cap_the_position_is_held(self):
        from engine.exits.evaluator import Bar, PositionView, evaluate_exit
        p = ExitPolicyRegistry().get(STRATEGY)
        lv = p.initial_levels("LONG", 1000.0, 20.0)
        bar = Bar(date="2026-09-03", open=1000.0, high=1005.0, low=998.0,
                  close=1001.0)
        view = PositionView(policy=p, direction="LONG", entry=1000.0, atr=20.0,
                            highest_seen=1005.0, lowest_seen=998.0,
                            hold_days=HORIZON_SESSIONS - 1,
                            sl_price=lv.sl_price, tp_price=lv.tp_price)
        assert evaluate_exit(view, bar) is None


class TestStillShadowOnly:
    """P-3 must not promote the strategy in any way."""

    def test_remains_in_disabled_strategies(self):
        from scheduler.scanner import _DEFAULT_DISABLED
        assert STRATEGY in {s.strip() for s in _DEFAULT_DISABLED.split(",")}

    def test_admission_still_refuses_it(self, tmp_path, monkeypatch):
        import sqlite3
        from engine import admission
        import engine.registry_loader as rl
        monkeypatch.setattr(rl, "registry_governance", lambda s: None)
        monkeypatch.setattr(admission, "manifest_rule_ids", lambda: {})
        admission.reset_evidence_cache()
        conn = sqlite3.connect(":memory:")
        from engine.wf_edge import ensure_wf_edge_table
        ensure_wf_edge_table(conn)
        import datetime as dt
        conn.execute("INSERT INTO wf_edge VALUES (?,?,?,?,?,?,?,?,?,?)",
                     ("AAA", STRATEGY, 7.2, 0.0, 55.0, 40.0, 0.4, 900, 15,
                      dt.date.today().isoformat()))
        conn.commit()
        from scheduler.scanner import _get_disabled_strategies
        v = admission.evaluate(conn, "AAA", STRATEGY,
                               disabled=_get_disabled_strategies())
        assert not v.admitted
        assert v.stage == admission.STAGE_DISABLED

    def test_it_is_not_registry_governed(self):
        from engine.registry_loader import registry_governance
        assert registry_governance(STRATEGY) is None      # UNREGISTERED

    def test_backtest_entry_thresholds_untouched(self):
        """OOS results must be unaffected: the backtest builds its own
        ExitPolicy inline and never consults ExitPolicyRegistry."""
        import inspect
        from engine import strategies as st
        src = inspect.getsource(st.strategy_liquidity_sweep_flow)
        assert "atr_sl_mult=1.0" in src and "atr_tp_mult=2.5" in src
        assert "min_rr=2.5" in src
        assert "ExitPolicyRegistry" not in inspect.getsource(st.run_strategy)
