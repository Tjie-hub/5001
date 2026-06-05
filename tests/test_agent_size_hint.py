"""Phase 2.1 — agent conviction sizing.

Tests:
- open_trade() respects lots_multiplier parameter
- run_agent_firm_gate() attaches agent_size_hint to approved signals
"""
import sys
import sqlite3
import pytest
from unittest.mock import MagicMock

# Pre-import scanner so it's in sys.modules before any patch.dict operations;
# prevents numpy from being re-loaded when the module is removed from cache on cleanup
import scheduler.scanner  # noqa: F401


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def pt_db(tmp_path, monkeypatch):
    """Isolated paper_trade DB with two tickers seeded for comparison tests."""
    import paper_trade as pt
    db = str(tmp_path / "pt.db")
    monkeypatch.setattr(pt, "DB_PATH", db)
    pt.init_paper_table()
    conn = sqlite3.connect(db)
    conn.execute("""CREATE TABLE IF NOT EXISTS backtest_cache (
        ticker TEXT, computed_date TEXT, best_strategy TEXT, best_return REAL,
        win_rate REAL, sharpe REAL, total_trades INTEGER, profitable INTEGER,
        regime TEXT, updated_at TEXT, PRIMARY KEY (ticker, computed_date))""")
    for t in ("BBCA", "BBRI"):
        conn.execute(
            "INSERT INTO backtest_cache VALUES (?,?,?,?,?,?,?,?,?,?)",
            (t, "2026-01-01", "vol_weighted", 5.0, 60.0, 1.0, 10, 6, "BULL", "2026-01-01"),
        )
    conn.commit()
    conn.close()
    return db


def _make_signal(ticker, score=1.0):
    return {
        "ticker": ticker,
        "strategies": ["vol_weighted"],
        "flow": {"score": score, "verdict": "BULLISH", "confirmed": True},
    }


def _mock_firm_module(decisions_fn):
    m = MagicMock()
    m.evaluate = MagicMock(side_effect=decisions_fn)
    return m


def _mock_config_module(is_active=True, get_enforce=False):
    m = MagicMock()
    m.is_active = MagicMock(return_value=is_active)
    m.get_enforce = MagicMock(return_value=get_enforce)
    return m


def _call_gate(intersection_results, flow_confirmed, mock_firm, mock_cfg):
    with __import__("unittest.mock", fromlist=["patch"]).patch.dict(sys.modules, {
        "engine.agent_firm.firm":   mock_firm,
        "engine.agent_firm.config": mock_cfg,
    }):
        from scheduler.scanner import run_agent_firm_gate
        return run_agent_firm_gate(
            intersection_results, flow_confirmed, "2026-06-05", "10:00"
        )


# ── 2.1a: open_trade lots_multiplier ─────────────────────────────────────────
# ATR=1000 → base_lots = int(500_000 / 100_000) = 5; max_lots=18 (not capped)
# multiplier=0.5 → lots = max(1, int(5*0.5)) = 2
# multiplier=1.5 → lots = max(1, int(5*1.5)) = 7

_SWING = "swing trend"   # skips R/R gate — lets us test lots_multiplier cleanly
# ATR=1000, entry=8000, swing trend:
#   base_lots = int(500_000 / (1000*100)) = 5
#   max_lots  = int(15_000_000 / 800_000) = 18  → NOT capped
#   x0.5 → 2, x1.0 → 5, x1.5 → 7


def test_open_trade_lots_multiplier_half(pt_db, monkeypatch):
    """lots_multiplier=0.5 halves computed lots (BBCA=1.0 vs BBRI=0.5)."""
    import paper_trade as pt
    monkeypatch.setattr(pt, "_calc_atr_from_db", lambda t: 1000.0)

    result_base = pt.open_trade("BBCA", entry_price=8000, strategy=_SWING, notify=False, lots_multiplier=1.0)
    result_half = pt.open_trade("BBRI", entry_price=8000, strategy=_SWING, notify=False, lots_multiplier=0.5)

    assert "error" not in result_base, result_base.get("error")
    assert "error" not in result_half, result_half.get("error")
    assert result_half["lots"] == max(1, int(result_base["lots"] * 0.5))


def test_open_trade_lots_multiplier_default_is_1(pt_db, monkeypatch):
    """Omitting lots_multiplier gives same lots as explicitly passing 1.0."""
    import paper_trade as pt
    monkeypatch.setattr(pt, "_calc_atr_from_db", lambda t: 1000.0)

    result_default = pt.open_trade("BBCA", entry_price=8000, strategy=_SWING, notify=False)

    conn = sqlite3.connect(pt_db)
    conn.execute("DELETE FROM paper_trades WHERE ticker='BBCA'")
    conn.commit(); conn.close()

    result_one = pt.open_trade("BBCA", entry_price=8000, strategy=_SWING, notify=False, lots_multiplier=1.0)

    assert "error" not in result_default, result_default.get("error")
    assert "error" not in result_one, result_one.get("error")
    assert result_default["lots"] == result_one["lots"]


def test_open_trade_lots_multiplier_above_1_increases_lots(pt_db, monkeypatch):
    """lots_multiplier=1.5 produces more lots than multiplier=1.0."""
    import paper_trade as pt
    monkeypatch.setattr(pt, "_calc_atr_from_db", lambda t: 1000.0)

    result_base = pt.open_trade("BBCA", entry_price=8000, strategy=_SWING, notify=False, lots_multiplier=1.0)
    result_up   = pt.open_trade("BBRI", entry_price=8000, strategy=_SWING, notify=False, lots_multiplier=1.5)

    assert "error" not in result_base, result_base.get("error")
    assert "error" not in result_up, result_up.get("error")
    assert result_up["lots"] > result_base["lots"]


# ── 2.1b: gate attaches agent_size_hint ───────────────────────────────────────

def test_gate_attaches_size_hint_to_approved_signal():
    """Approved signals get agent_size_hint attached; flow_confirmed shares same dicts."""
    decision = MagicMock(ticker="BBCA", decision="approve", size_hint=0.5)
    # Use the same dict object in both lists (mirrors real scanner behaviour)
    sig = _make_signal("BBCA")
    result = _call_gate(
        intersection_results=[sig],
        flow_confirmed=[sig],
        mock_firm=_mock_firm_module(lambda c: [decision]),
        mock_cfg=_mock_config_module(is_active=True, get_enforce=False),
    )
    assert sig.get("agent_size_hint") == 0.5


def test_gate_size_hint_defaults_to_1_when_absent():
    """If decision has no size_hint, agent_size_hint defaults to 1.0."""
    decision = MagicMock(ticker="AMMN", decision="approve", size_hint=None)
    sig = _make_signal("AMMN")
    result = _call_gate(
        intersection_results=[sig],
        flow_confirmed=[sig],
        mock_firm=_mock_firm_module(lambda c: [decision]),
        mock_cfg=_mock_config_module(is_active=True, get_enforce=False),
    )
    assert sig.get("agent_size_hint") == 1.0


def test_gate_vetoed_signal_gets_no_size_hint():
    """Vetoed signal: size_hint not in size_map, so agent_size_hint = 1.0 (default)."""
    decision = MagicMock(ticker="MDKA", decision="veto", size_hint=None)
    sig = _make_signal("MDKA")
    _call_gate(
        intersection_results=[sig],
        flow_confirmed=[sig],
        mock_firm=_mock_firm_module(lambda c: [decision]),
        mock_cfg=_mock_config_module(is_active=True, get_enforce=False),
    )
    assert sig.get("agent_size_hint") == 1.0
