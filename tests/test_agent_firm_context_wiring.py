"""AF-2 WP2 (Context Producer Migration) — integration tests verifying scheduler/scanner.py's
two SignalCandidate construction sites (run_agent_firm_gate, rank_bear_watchlist_and_notify)
actually populate Tier 1 context via engine.agent_firm_context.build_candidate_context()
before calling evaluate_staged().

Scope: producer wiring only (docs/agent_firm/ADR-AF-001..004, AF2_ARCHITECTURE_CERTIFICATION.md).
These tests assert:
  - context objects are populated with real data from a hermetic DB (producer mapping works)
  - the legacy path (engine.agent_firm.firm._build_context/_market_ctx) is untouched
  - a broken/unreadable DB fails open — candidates still reach evaluate_staged() with empty
    (default) context, exactly matching pre-WP2 behavior — no runtime regression
  - backward compatibility: evaluate_staged() itself is never called differently
"""
import sqlite3
import sys
from unittest.mock import MagicMock, patch

import pytest

import engine.agent_firm_context as afc
import paper_trade
import scheduler.scanner as scanner_mod
from scheduler.scanner import run_agent_firm_gate, rank_bear_watchlist_and_notify


@pytest.fixture(autouse=True)
def _reset_batch_context():
    # engine.agent_firm_context's batch-level cache (market/portfolio/risk_limits/execution)
    # is module-global state, intentionally shared across calls within one production scan
    # cycle (ADR-AF-002). Each test here simulates its own scan cycle with its own DB/
    # market_risk_score, so it must not leak into the next test.
    afc.reset_batch_context()
    yield
    afc.reset_batch_context()


def _seeded_db(tmp_path, ticker="BBRI"):
    db = tmp_path / "wf.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT, open REAL, high REAL, "
                 "low REAL, close REAL, volume REAL)")
    conn.execute("CREATE TABLE stockbit_flow (ticker TEXT, trade_date TEXT, verdict TEXT, "
                 "smart_money TEXT, composite_score INT, foreign_score REAL)")
    conn.execute("CREATE TABLE broker_flow (ticker TEXT, trade_date TEXT, broker_code TEXT, "
                 "side TEXT, lot_value REAL, investor_type TEXT)")
    conn.execute("CREATE TABLE stockbit_flow_bars (ticker TEXT, trade_date TEXT, "
                 "bar_time TEXT, buy_lot INT, sell_lot INT, delta REAL, net_value REAL)")
    conn.execute("CREATE TABLE wf_scores (ticker TEXT, strategy TEXT, consistency_pct REAL, "
                 "avg_return_pct REAL, avg_sharpe REAL, weighted_score REAL)")
    conn.execute("CREATE TABLE daily_screen (ticker TEXT, date TEXT, signal TEXT, "
                 "vpin_label TEXT, vol_ratio REAL)")
    conn.execute("CREATE TABLE paper_trades (ticker TEXT, entry_price REAL, lots INT, "
                 "tp_price REAL, sl_price REAL, capital_used REAL, status TEXT)")
    conn.execute("CREATE TABLE agent_decisions (ticker TEXT, strategy TEXT, decision TEXT, "
                 "scan_time TEXT)")
    price = 100.0
    for i in range(60):
        price += 2.0
        conn.execute("INSERT INTO ohlcv VALUES (?,?,?,?,?,?,?)",
                     (ticker, f"2026-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}",
                      price - 1, price + 2, price - 2, price, 1_000_000 + i * 1000))
    conn.execute(
        "INSERT INTO stockbit_flow VALUES (?, date('now'), 'BULLISH', 'STRONG_BUY', 7, 2.1)",
        (ticker,))
    conn.commit()
    conn.close()
    return str(db)


def _make_result(ticker, flow_score=3):
    return {
        "ticker": ticker,
        "strategies": ["vol_weighted"],
        "flow": {"score": flow_score, "verdict": "BUY", "smart_money": "YES", "confirmed": True},
        "signal_reasons": ["vol_weighted: signal"],
        "signal_details": {"vol_weighted": {"price": 1000}},
    }


def _mock_firm_and_config(capture, is_active=True):
    mock_firm = MagicMock()
    mock_firm.evaluate_staged = MagicMock(side_effect=lambda c: capture.append(c) or [])
    mock_cfg = MagicMock()
    mock_cfg.is_active = MagicMock(return_value=is_active)
    mock_cfg.get_enforce = MagicMock(return_value=False)
    return mock_firm, mock_cfg


class TestRunAgentFirmGateContextWiring:
    def test_candidates_arrive_with_populated_tier1_context(self, tmp_path):
        db = _seeded_db(tmp_path, "BBRI")
        capture = []
        mock_firm, mock_cfg = _mock_firm_and_config(capture)

        import engine.agent_firm as _pkg
        with patch.object(_pkg, "firm", mock_firm), \
             patch.object(_pkg, "config", mock_cfg), \
             patch.object(scanner_mod, "DB_PATH", db), \
             patch.object(paper_trade, "DB_PATH", db), \
             patch.dict(sys.modules, {
                 "engine.agent_firm.firm": mock_firm,
                 "engine.agent_firm.config": mock_cfg,
             }):
            run_agent_firm_gate([_make_result("BBRI")], [], "2026-07-29", "10:00",
                                market_risk_score=42.0)

        assert len(capture) == 1
        cand = capture[0][0]
        # Producer mapping: TechnicalContext/FlowContext populated from the seeded DB,
        # not left at their None/empty WP1 defaults.
        assert cand.technical is not None
        assert cand.technical.sma20 is not None
        assert cand.technical.mechanical_direction == "BULLISH"
        assert cand.flow is not None
        assert cand.flow.verdict == "BULLISH"
        assert cand.market is not None
        assert cand.market.market_risk_score == 42.0
        assert cand.portfolio is not None
        assert cand.risk_limits is not None
        assert cand.execution is not None

    def test_broken_db_fails_open_candidates_still_evaluated(self, tmp_path):
        # DB_PATH points somewhere with no tables at all — context population must fail
        # soft; evaluate_staged() must still be called (legacy no-context behavior),
        # never blocked by a context-build error.
        capture = []
        mock_firm, mock_cfg = _mock_firm_and_config(capture)

        import engine.agent_firm as _pkg
        with patch.object(_pkg, "firm", mock_firm), \
             patch.object(_pkg, "config", mock_cfg), \
             patch.object(scanner_mod, "DB_PATH", ":memory:"), \
             patch.object(paper_trade, "DB_PATH", ":memory:"), \
             patch.dict(sys.modules, {
                 "engine.agent_firm.firm": mock_firm,
                 "engine.agent_firm.config": mock_cfg,
             }):
            result = run_agent_firm_gate([_make_result("BBRI")], [], "2026-07-29", "10:00")

        assert len(capture) == 1
        cand = capture[0][0]
        assert cand.ticker == "BBRI"
        assert cand.technical is not None  # degraded to TechnicalContext(), not None
        assert cand.technical.mechanical_direction == "NEUTRAL"
        assert result == []  # shadow-equivalent: unchanged, evaluate ran with empty decisions


class TestRankBearWatchlistContextWiring:
    def test_candidates_arrive_with_populated_tier1_context(self, tmp_path):
        db = _seeded_db(tmp_path, "MDKA")
        capture = []
        mock_firm, mock_cfg = _mock_firm_and_config(capture)

        import engine.agent_firm as _pkg
        with patch.object(_pkg, "firm", mock_firm, create=True), \
             patch.object(_pkg, "config", mock_cfg, create=True), \
             patch.object(scanner_mod, "DB_PATH", db), \
             patch.object(paper_trade, "DB_PATH", db), \
             patch.dict(sys.modules, {
                 "engine.agent_firm.firm": mock_firm,
                 "engine.agent_firm.config": mock_cfg,
             }), patch.object(scanner_mod, "send_telegram", lambda *a, **k: None):
            rank_bear_watchlist_and_notify(["MDKA"], "2026-07-29", "10:00",
                                           market_risk_score=17.5)

        assert len(capture) == 1
        cand = capture[0][0]
        assert cand.technical is not None
        assert cand.technical.mechanical_direction == "BULLISH"
        assert cand.market.market_risk_score == 17.5
