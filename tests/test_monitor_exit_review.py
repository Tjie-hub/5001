"""Phase 2.3 — agent exit review for R3_ADX_FADE and R4_DISTRIBUTION.

Agent gets final say on probabilistic swing-trend exits.
Fail-open: if agent errors or firm is disabled, the close proceeds.
"""
import sys
from unittest.mock import MagicMock, patch

# Pre-import schemas so sys.modules["engine.agent_firm.schemas"] is never None
import engine.agent_firm.schemas  # noqa: F401

# AF-2 WP4: pre-import at collection time, before any test's importlib.reload() gymnastics
# run at runtime (tests/agent_firm/test_firm.py reloads config/firm in several tests). This
# module lazily imports engine.agent_firm_context (hence pandas/numpy) inside
# _agent_confirms_exit — on this Windows .winvenv environment, a *first-ever* pandas/numpy
# import performed *after* an importlib.reload() cycle has already run in the same process
# fails with "ImportError: cannot load module more than once per process" (a numpy C-extension
# guard, not a logic bug). Importing it here, at collection time, sidesteps the ordering
# entirely — mirrors how tests/test_scheduler_jobs_context_wiring.py avoids the same trap by
# importing engine.agent_firm_context at module level instead of relying on the lazy import.
import engine.agent_firm_context  # noqa: F401


def _mock_firm(decisions):
    m = MagicMock()
    m.evaluate = MagicMock(return_value=decisions)
    return m


def _mock_cfg(is_active=True):
    m = MagicMock()
    m.is_active = MagicMock(return_value=is_active)
    return m


def _call_confirms(trade, result, mock_firm, mock_cfg):
    # monitor does ``from engine.agent_firm import firm`` lazily, which resolves to
    # package attributes; patch those (not just sys.modules) so the mock holds even
    # after an earlier test imports the real submodules.
    import monitor as monitor_mod
    import engine.agent_firm as _pkg
    with patch.object(_pkg, "firm", mock_firm), \
         patch.object(_pkg, "config", mock_cfg), \
         patch.dict(sys.modules, {
             "engine.agent_firm.firm":   mock_firm,
             "engine.agent_firm.config": mock_cfg,
         }), \
         patch.object(monitor_mod, "DB_PATH", ":memory:"):
        # AF-2 WP4: _agent_confirms_exit now opens a real db_connect(DB_PATH) to build
        # Tier 1 context (mirrors scanner.py's WP2 wiring) — pinned to ":memory:" here,
        # same fix WP2 applied to test_scheduler_firm_hook.py/test_agent_size_hint.py,
        # so this test suite never touches the real gitignored data/walkforward.db.
        from monitor import _agent_confirms_exit
        return _agent_confirms_exit(trade, result)


_TRADE = {
    "id": 1, "ticker": "BBCA", "strategy": "swing trend",
    "entry_price": 8000, "sl_price": 7600, "tp_price": 9600,
    "lots": 10, "highest_seen": 8200, "adx_peak": 30.0,
}


def test_exit_review_candidate_carries_populated_tier1_context(tmp_path, monkeypatch):
    """AF-2 WP4: _agent_confirms_exit's SignalCandidate must carry real Tier 1 context
    (built via engine.agent_firm_context.build_candidate_context()) when a real DB is
    available — a WP4 audit found this call site was never wired, unlike scanner.py's two
    sites (WP2). This is the regression coverage for closing that gap."""
    import sqlite3
    import monitor as monitor_mod

    db = tmp_path / "wf.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT, open REAL, high REAL, "
                 "low REAL, close REAL, volume REAL)")
    conn.execute("CREATE TABLE paper_trades (ticker TEXT, entry_price REAL, lots INT, "
                 "tp_price REAL, sl_price REAL, capital_used REAL, status TEXT)")
    price = 100.0
    for i in range(30):
        price += 1.5
        conn.execute("INSERT INTO ohlcv VALUES (?,?,?,?,?,?,?)",
                     ("BBCA", f"2026-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}",
                      price - 1, price + 2, price - 2, price, 1_000_000))
    conn.commit()
    conn.close()

    captured = {}

    def _capture_evaluate(candidates):
        captured["candidate"] = candidates[0]
        return [MagicMock(ticker="BBCA", decision="approve")]

    mock_firm = MagicMock()
    mock_firm.evaluate = MagicMock(side_effect=_capture_evaluate)
    result = {"action": "CLOSE", "reason": "R4_DISTRIBUTION"}

    import engine.agent_firm as _pkg
    with patch.object(_pkg, "firm", mock_firm), \
         patch.object(_pkg, "config", _mock_cfg()), \
         patch.dict(sys.modules, {
             "engine.agent_firm.firm":   mock_firm,
             "engine.agent_firm.config": _mock_cfg(),
         }), \
         patch.object(monitor_mod, "DB_PATH", str(db)):
        from monitor import _agent_confirms_exit
        _agent_confirms_exit(_TRADE, result)

    cand = captured["candidate"]
    assert cand.ticker == "BBCA"
    assert cand.technical is not None
    assert cand.technical.mechanical_direction == "BULLISH"


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

    import engine.agent_firm as _pkg
    with patch.object(_pkg, "firm", fake_firm), \
         patch.object(_pkg, "config", fake_cfg), \
         patch.dict(sys.modules, {
             "engine.agent_firm.firm":   fake_firm,
             "engine.agent_firm.config": fake_cfg,
         }), \
         patch.object(monitor, "DB_PATH", ":memory:"), \
         patch("monitor.send_telegram"):
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
