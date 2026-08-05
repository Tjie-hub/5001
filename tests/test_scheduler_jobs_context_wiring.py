"""AF-2 WP4 — integration tests verifying scheduler/jobs.py's two SignalCandidate
construction sites (run_premarket_firm_scan, run_eod_trade_plan) populate Tier 1 context
via engine.agent_firm_context.build_candidate_context() before calling evaluate_staged().

Background: WP2 (Audit/AF2_WP2_IMPLEMENTATION_REPORT.md) wired this producer into
scheduler/scanner.py's two construction sites only. A WP4 repository-wide audit found two
more live, scheduled construction sites in scheduler/jobs.py (the 08:35 premarket job and
the 16:40 EOD trade plan job, both documented in CLAUDE.md's "Telegram operational
reporting" section) that never received the same wiring — every candidate from these two
jobs reached the WP3-migrated specialists with every Tier 1 context field at its None
default, silently degrading every analyst to its neutral/insufficient-data fallback. This
file is the regression coverage for closing that gap.

Mirrors tests/test_agent_firm_context_wiring.py's structure and fixtures closely.
"""
import sqlite3
import sys
from unittest.mock import MagicMock, patch

import pytest

import engine.agent_firm_context as afc
import scheduler.jobs as jobs_mod


@pytest.fixture(autouse=True)
def _reset_batch_context():
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


def _mock_firm_and_config(capture, is_active=True):
    mock_firm = MagicMock()
    mock_firm.evaluate_staged = MagicMock(side_effect=lambda c, **k: capture.append(c) or [])
    mock_cfg = MagicMock()
    mock_cfg.is_active = MagicMock(return_value=is_active)
    mock_cfg.get_enforce = MagicMock(return_value=False)
    return mock_firm, mock_cfg


class TestPremarketFirmScanContextWiring:
    def test_candidates_arrive_with_populated_tier1_context(self, tmp_path, monkeypatch):
        db = _seeded_db(tmp_path, "BBRI")
        capture = []
        mock_firm, mock_cfg = _mock_firm_and_config(capture)

        monkeypatch.setattr(jobs_mod, "_holiday_skip", lambda name: False)
        monkeypatch.setattr(jobs_mod, "DB_PATH", db)
        monkeypatch.setattr(
            "engine.unified_watchlist.build_unified_watchlist",
            lambda db_path: [{"ticker": "BBRI", "direction": "long", "strength": 70.0,
                              "sources": ["REVERSAL"], "confluence": False, "close": 1000,
                              "detail": {}}],
        )
        monkeypatch.setattr(
            "engine.liquidity.select_top_liquid_longs",
            lambda rows, conn, date_str, top_n=3: rows,
        )
        monkeypatch.setattr("config.edge_mode", lambda: "off")

        import engine.agent_firm as _pkg
        with patch.object(_pkg, "firm", mock_firm), \
             patch.object(_pkg, "config", mock_cfg), \
             patch.dict(sys.modules, {
                 "engine.agent_firm.firm": mock_firm,
                 "engine.agent_firm.config": mock_cfg,
             }), \
             patch.object(jobs_mod, "send_telegram", lambda *a, **k: None):
            jobs_mod.run_premarket_firm_scan()

        assert len(capture) == 1
        cand = capture[0][0]
        assert cand.ticker == "BBRI"
        assert cand.technical is not None
        assert cand.technical.mechanical_direction == "BULLISH"
        assert cand.flow is not None
        assert cand.flow.verdict == "BULLISH"
        assert cand.portfolio is not None
        assert cand.risk_limits is not None

    def test_broken_context_db_fails_open(self, tmp_path, monkeypatch):
        """Context build error must not block the shortlist — candidates still reach
        evaluate_staged(), just without Tier 1 context (pre-WP4 shape)."""
        capture = []
        mock_firm, mock_cfg = _mock_firm_and_config(capture)

        # DB_PATH points at a real, empty (no tables) tmp file — the dedup-guard/
        # watchlist/liquidity mocks below never touch it, only the context builder does,
        # and it must fail soft rather than raise.
        empty_db = str(tmp_path / "empty.db")
        monkeypatch.setattr(jobs_mod, "_holiday_skip", lambda name: False)
        monkeypatch.setattr(jobs_mod, "DB_PATH", empty_db)
        monkeypatch.setattr(
            "engine.unified_watchlist.build_unified_watchlist",
            lambda db_path: [{"ticker": "BBRI", "direction": "long", "strength": 70.0,
                              "sources": ["REVERSAL"], "confluence": False, "close": 1000,
                              "detail": {}}],
        )
        monkeypatch.setattr(
            "engine.liquidity.select_top_liquid_longs",
            lambda rows, conn, date_str, top_n=3: rows,
        )
        monkeypatch.setattr("config.edge_mode", lambda: "off")

        import engine.agent_firm as _pkg
        with patch.object(_pkg, "firm", mock_firm), \
             patch.object(_pkg, "config", mock_cfg), \
             patch.dict(sys.modules, {
                 "engine.agent_firm.firm": mock_firm,
                 "engine.agent_firm.config": mock_cfg,
             }), \
             patch.object(jobs_mod, "send_telegram", lambda *a, **k: None):
            jobs_mod.run_premarket_firm_scan()

        assert len(capture) == 1
        cand = capture[0][0]
        assert cand.ticker == "BBRI"
        assert cand.technical is not None  # degraded to TechnicalContext(), not None
        assert cand.technical.mechanical_direction == "NEUTRAL"


class TestEodTradePlanContextWiring:
    def test_candidates_arrive_with_populated_tier1_context(self, tmp_path, monkeypatch):
        db = _seeded_db(tmp_path, "MDKA")
        capture = []
        mock_firm, mock_cfg = _mock_firm_and_config(capture)

        monkeypatch.setattr(jobs_mod, "_holiday_skip", lambda name: False)
        monkeypatch.setattr(jobs_mod, "DB_PATH", db)
        monkeypatch.setattr(
            "engine.trade_plan.gather_long_candidates",
            lambda conn, date_str: [{"ticker": "MDKA", "conviction": 70.0,
                                     "smart_money": "YES", "sources": ["REVERSAL"],
                                     "confluence": False, "vol_ratio": 1.5, "net_value": 1e9}],
        )
        monkeypatch.setattr("engine.trade_plan.get_regime", lambda conn, date_str: "BULL")
        monkeypatch.setattr("engine.trade_plan.select_top", lambda cands, n=8: cands)
        monkeypatch.setattr("engine.trade_plan.get_vpin_gate", lambda conn, date_str: None)
        monkeypatch.setattr("config.edge_mode", lambda: "off")
        monkeypatch.setattr(
            "engine.trade_plan.rank_approved",
            lambda top, decisions: [dict(t, agent_decision="approve") for t in top],
        )

        import engine.agent_firm as _pkg
        with patch.object(_pkg, "firm", mock_firm), \
             patch.object(_pkg, "config", mock_cfg), \
             patch.dict(sys.modules, {
                 "engine.agent_firm.firm": mock_firm,
                 "engine.agent_firm.config": mock_cfg,
             }), \
             patch.object(jobs_mod, "send_telegram", lambda *a, **k: None):
            jobs_mod.run_eod_trade_plan()

        assert len(capture) == 1
        cand = capture[0][0]
        assert cand.ticker == "MDKA"
        assert cand.technical is not None
        assert cand.technical.mechanical_direction == "BULLISH"
        assert cand.flow is not None
        assert cand.market is not None
