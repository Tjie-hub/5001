"""Phase 2.3 — agent exit review for R3_ADX_FADE and R4_DISTRIBUTION.

Agent gets final say on probabilistic swing-trend exits.
Fail-open: if agent errors or firm is disabled, the close proceeds.
"""
import sys
from unittest.mock import MagicMock, patch

# Pre-import schemas so sys.modules["engine.agent_firm.schemas"] is never None
import engine.agent_firm.schemas  # noqa: F401


def _mock_firm(decisions):
    m = MagicMock()
    m.evaluate = MagicMock(return_value=decisions)
    return m


def _mock_cfg(is_active=True):
    m = MagicMock()
    m.is_active = MagicMock(return_value=is_active)
    return m


def _call_confirms(trade, result, mock_firm, mock_cfg):
    with __import__("unittest.mock", fromlist=["patch"]).patch.dict(sys.modules, {
        "engine.agent_firm.firm":   mock_firm,
        "engine.agent_firm.config": mock_cfg,
    }):
        from monitor import _agent_confirms_exit
        return _agent_confirms_exit(trade, result)


_TRADE = {
    "id": 1, "ticker": "BBCA", "strategy": "swing trend",
    "entry_price": 8000, "sl_price": 7600, "tp_price": 9600,
    "lots": 10, "highest_seen": 8200, "adx_peak": 30.0,
}


def test_agent_veto_prevents_r4_close():
    """Agent veto on R4_DISTRIBUTION → _agent_confirms_exit returns False (hold)."""
    decision = MagicMock(ticker="BBCA", decision="veto")
    result = {"action": "CLOSE", "reason": "R4_DISTRIBUTION"}
    confirmed = _call_confirms(_TRADE, result, _mock_firm([decision]), _mock_cfg())
    assert confirmed is False


def test_agent_approve_confirms_r4_close():
    """Agent approve on R4_DISTRIBUTION → _agent_confirms_exit returns True (close)."""
    decision = MagicMock(ticker="BBCA", decision="approve")
    result = {"action": "CLOSE", "reason": "R4_DISTRIBUTION"}
    confirmed = _call_confirms(_TRADE, result, _mock_firm([decision]), _mock_cfg())
    assert confirmed is True


def test_agent_veto_prevents_r3_close():
    """Agent veto on R3_ADX_FADE → _agent_confirms_exit returns False (hold)."""
    decision = MagicMock(ticker="BBCA", decision="veto")
    result = {"action": "CLOSE", "reason": "R3_ADX_FADE"}
    confirmed = _call_confirms(_TRADE, result, _mock_firm([decision]), _mock_cfg())
    assert confirmed is False


def test_firm_disabled_always_confirms():
    """If agent firm is disabled, _agent_confirms_exit returns True (proceed with close)."""
    result = {"action": "CLOSE", "reason": "R4_DISTRIBUTION"}
    confirmed = _call_confirms(_TRADE, result, _mock_firm([]), _mock_cfg(is_active=False))
    assert confirmed is True


def test_firm_error_confirms_fail_open():
    """If agent firm raises, _agent_confirms_exit returns True (fail-open, proceed with close)."""
    bad_firm = MagicMock()
    bad_firm.evaluate = MagicMock(side_effect=RuntimeError("API error"))
    result = {"action": "CLOSE", "reason": "R4_DISTRIBUTION"}
    confirmed = _call_confirms(_TRADE, result, bad_firm, _mock_cfg())
    assert confirmed is True


def test_check_all_open_trades_r4_agent_veto_skips_close(monkeypatch):
    """End-to-end: when agent vetoes R4, check_all_open_trades does not call close_trade."""
    import monitor
    import paper_trade

    fake_trade = dict(_TRADE)

    # get_open_trades / close_trade are imported inside check_all_open_trades
    monkeypatch.setattr(paper_trade, "get_open_trades", lambda: [fake_trade])
    monkeypatch.setattr(monitor, "_get_current_price", lambda t: 7900.0)

    r4_result = {
        "action": "CLOSE", "reason": "R4_DISTRIBUTION",
        "new_sl": 7600, "new_highest": 8200, "new_adx_peak": 30.0,
        "message": "⚠️ R4 test",
    }
    monkeypatch.setattr(monitor, "_evaluate_swing_trend", lambda t: r4_result)

    close_calls = []
    monkeypatch.setattr(paper_trade, "close_trade", lambda *a, **kw: close_calls.append(a))

    veto_decision = MagicMock(ticker="BBCA", decision="veto")
    fake_firm = _mock_firm([veto_decision])
    fake_cfg  = _mock_cfg(is_active=True)

    with patch.dict(sys.modules, {
        "engine.agent_firm.firm":   fake_firm,
        "engine.agent_firm.config": fake_cfg,
    }), patch("monitor.send_telegram"):
        monitor.check_all_open_trades()

    assert close_calls == [], "close_trade must NOT be called when agent vetoes R4"


def test_check_all_open_trades_r1_ma_break_closes_without_agent(monkeypatch):
    """R1_MA_BREAK is NOT subject to agent review — it closes unconditionally."""
    import monitor
    import paper_trade

    fake_trade = dict(_TRADE)
    monkeypatch.setattr(paper_trade, "get_open_trades", lambda: [fake_trade])
    monkeypatch.setattr(monitor, "_get_current_price", lambda t: 7900.0)

    r1_result = {
        "action": "CLOSE", "reason": "R1_MA_BREAK",
        "new_sl": 7600, "new_highest": 8200, "new_adx_peak": 30.0,
        "message": "🔴 R1 test",
    }
    monkeypatch.setattr(monitor, "_evaluate_swing_trend", lambda t: r1_result)

    close_calls = []
    monkeypatch.setattr(paper_trade, "close_trade", lambda *a, **kw: close_calls.append(a))

    with patch("monitor.send_telegram"), patch("screener.db.log_trade_alert"):
        monitor.check_all_open_trades()

    assert len(close_calls) == 1, "R1_MA_BREAK must close unconditionally (no agent review)"
