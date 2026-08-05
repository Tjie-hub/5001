"""Tests for engine/agent_firm_context.py — the Production-Engine-owned Tier 1 context
builders (docs/agent_firm/ADR-AF-002-CONTEXT_OWNERSHIP.md).

WP1 scope: these builders are not called from any live path yet (docs/agent_firm/
AF2_ARCHITECTURE_CERTIFICATION.md, Work Package 1) — these tests exercise them directly,
against hermetic in-memory/temp SQLite DBs, matching tests/test_edge_enrich.py's existing
pattern for the sibling module engine/edge_enrich.py.
"""
import os
import sqlite3
import tempfile

import pytest

import engine.agent_firm_context as afc
from engine.agent_firm.schemas import (
    ExecutionContext, FlowContext, MarketContext, NewsContext, PortfolioContext,
    RegimeContext, RiskContext, SessionContext, TechnicalContext,
)


def _ohlcv_rows(ticker: str, n: int = 60, start_price: float = 100.0, trend: float = 0.5):
    """Ascending-price synthetic bars, inserted DESC (matching real ohlcv storage) —
    builders must reverse them internally (verified separately below)."""
    rows = []
    price = start_price
    for i in range(n):
        price += trend
        rows.append((ticker, f"2026-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}",
                     price - 1, price + 2, price - 2, price, 1_000_000 + i * 1000))
    return rows  # chronological; caller inserts as-is, builder queries DESC


class TestTechnicalContext:
    def _db(self, ticker="BBRI", n=60, trend=0.5):
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT, open REAL, high REAL, "
                     "low REAL, close REAL, volume REAL)")
        for r in _ohlcv_rows(ticker, n, trend=trend):
            conn.execute("INSERT INTO ohlcv VALUES (?,?,?,?,?,?,?)", r)
        return conn

    def test_returns_typed_object_with_computed_indicators(self):
        conn = self._db()
        ctx = afc.build_technical_context(conn, "BBRI")
        assert isinstance(ctx, TechnicalContext)
        assert ctx.sma20 is not None
        assert ctx.sma50 is not None
        assert ctx.mechanical_direction in ("BULLISH", "BEARISH", "NEUTRAL")

    def test_uptrend_produces_bullish_mechanical_direction(self):
        # Strong, consistent uptrend over 60 bars — engine.technicals.tech_direction()'s
        # own MA(20)>=MA(50) + close>MA(20) rule should read BULLISH.
        conn = self._db(trend=2.0)
        ctx = afc.build_technical_context(conn, "BBRI")
        assert ctx.mechanical_direction == "BULLISH"

    def test_insufficient_data_returns_empty_context_not_an_error(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT, open REAL, high REAL, "
                     "low REAL, close REAL, volume REAL)")
        ctx = afc.build_technical_context(conn, "NODATA")
        assert isinstance(ctx, TechnicalContext)
        assert ctx.sma20 is None
        assert ctx.mechanical_direction == "NEUTRAL"

    def test_pattern_flags_scoped_to_recent_bars_only(self):
        # 60 bars produce many historical patterns; the builder must not return the
        # full-history list (a UX/noise concern found during implementation, not a
        # correctness one — see engine/agent_firm_context.py's comment).
        conn = self._db(n=60)
        ctx = afc.build_technical_context(conn, "BBRI")
        assert len(ctx.pattern_flags) <= 5


class TestFlowContext:
    def _db(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE stockbit_flow (ticker TEXT, trade_date TEXT, "
                     "verdict TEXT, smart_money TEXT, composite_score INT, foreign_score REAL)")
        conn.execute("CREATE TABLE broker_flow (ticker TEXT, trade_date TEXT, "
                     "broker_code TEXT, side TEXT, lot_value REAL, investor_type TEXT)")
        conn.execute("CREATE TABLE stockbit_flow_bars (ticker TEXT, trade_date TEXT, "
                     "bar_time TEXT, buy_lot INT, sell_lot INT, delta REAL, net_value REAL)")
        return conn

    def test_verdict_and_smart_money_are_passthrough_not_recomputed(self):
        conn = self._db()
        conn.execute(
            "INSERT INTO stockbit_flow VALUES ('BBRI', date('now'), 'BULLISH', "
            "'STRONG_BUY', 7, 2.1)")
        ctx = afc.build_flow_context(conn, "BBRI")
        assert isinstance(ctx, FlowContext)
        # Exact passthrough — ADR-AF-001's binding requirement: never re-derived.
        assert ctx.verdict == "BULLISH"
        assert ctx.smart_money == "STRONG_BUY"
        assert ctx.composite_score == 7
        assert ctx.foreign_score == 2.1

    def test_net_foreign_14d_is_buy_minus_sell(self):
        conn = self._db()
        conn.execute("INSERT INTO broker_flow VALUES ('BBRI', date('now'), 'BK', 'BUY', "
                     "1000, 'Asing')")
        conn.execute("INSERT INTO broker_flow VALUES ('BBRI', date('now'), 'BK', 'SELL', "
                     "300, 'Asing')")
        ctx = afc.build_flow_context(conn, "BBRI")
        assert ctx.net_foreign_14d == 700

    def test_no_flow_data_returns_defaults_not_an_error(self):
        conn = self._db()
        ctx = afc.build_flow_context(conn, "NODATA")
        assert ctx.verdict is None
        assert ctx.net_foreign_14d == 0
        assert ctx.trend_7d == "flat"


class TestRegimeContext:
    def _db(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT, open REAL, high REAL, "
                     "low REAL, close REAL, volume REAL)")
        conn.execute("CREATE TABLE wf_scores (ticker TEXT, strategy TEXT, "
                     "consistency_pct REAL, avg_return_pct REAL, avg_sharpe REAL, "
                     "weighted_score REAL)")
        conn.execute("CREATE TABLE daily_screen (ticker TEXT, date TEXT, signal TEXT, "
                     "vpin_label TEXT, vol_ratio REAL)")
        return conn

    def test_regime_call_is_unknown_without_price_history(self):
        conn = self._db()
        ctx = afc.build_regime_context(conn, "NODATA")
        assert isinstance(ctx, RegimeContext)
        assert ctx.regime_call == "UNKNOWN"

    def test_sector_tailwind_true_above_sharpe_threshold(self):
        conn = self._db()
        conn.execute("INSERT INTO wf_scores VALUES ('BBRI','conservative',60.0,1.2,0.95,5.0)")
        ctx = afc.build_regime_context(conn, "BBRI")
        assert ctx.sector_tailwind is True
        assert ctx.best_strategy == "conservative"
        assert ctx.ticker_consistency_pct == 60.0

    def test_sector_tailwind_false_below_sharpe_threshold(self):
        conn = self._db()
        conn.execute("INSERT INTO wf_scores VALUES ('BBRI','conservative',60.0,1.2,0.3,5.0)")
        ctx = afc.build_regime_context(conn, "BBRI")
        assert ctx.sector_tailwind is False

    def test_macro_risk_high_on_extreme_vpin_with_negative_signal(self):
        conn = self._db()
        for i in range(3):
            conn.execute(
                "INSERT INTO daily_screen VALUES ('BBRI', ?, 'BEARISH', 'EXTREME', 1.0)",
                (f"2026-07-{i+1:02d}",))
        ctx = afc.build_regime_context(conn, "BBRI")
        assert ctx.macro_risk == "HIGH"


class TestNewsContext:
    def _tempdb(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        conn = sqlite3.connect(path)
        conn.execute("CREATE TABLE news_mentions (ticker TEXT, date TEXT, count INT, "
                     "headlines_json TEXT)")
        conn.commit()
        return conn, path

    def test_has_catalyst_passthrough_and_mentions_present(self):
        conn, path = self._tempdb()
        try:
            conn.execute(
                "INSERT INTO news_mentions VALUES ('BBRI', date('now'), 2, '[\"h1\",\"h2\"]')")
            conn.commit()
            from engine.catalyst import add_catalyst
            add_catalyst(conn, "BBRI", "2026-07-29", "EARNINGS")
            ctx = afc.build_news_context(conn, "BBRI", "2026-07-29")
            assert isinstance(ctx, NewsContext)
            assert ctx.has_catalyst is True
            assert ctx.mentions_count_7d == 2
        finally:
            conn.close()
            os.unlink(path)

    def test_no_catalyst_returns_false_strict_default(self):
        conn, path = self._tempdb()
        try:
            ctx = afc.build_news_context(conn, "NODATA", "2026-07-29")
            assert ctx.has_catalyst is False
        finally:
            conn.close()
            os.unlink(path)


class TestMarketContext:
    def test_reuses_technical_context_builder_for_ihsg(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT, open REAL, high REAL, "
                     "low REAL, close REAL, volume REAL)")
        for r in _ohlcv_rows("IHSG", n=60):
            conn.execute("INSERT INTO ohlcv VALUES (?,?,?,?,?,?,?)", r)
        ctx = afc.build_market_context(conn)
        assert isinstance(ctx, MarketContext)
        assert isinstance(ctx.ihsg_trend, TechnicalContext)
        assert ctx.ihsg_trend.sma20 is not None

    def test_market_risk_score_is_injected_not_recomputed(self):
        # Dependency-injection point (AF2_WORK_PACKAGE_SEQUENCE.md WP8): this module never
        # re-derives the 4-sensor composite itself.
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT, open REAL, high REAL, "
                     "low REAL, close REAL, volume REAL)")
        ctx = afc.build_market_context(conn, market_risk_score=42.5)
        assert ctx.market_risk_score == 42.5

    def test_no_ihsg_data_is_fail_soft(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT, open REAL, high REAL, "
                     "low REAL, close REAL, volume REAL)")
        ctx = afc.build_market_context(conn)
        assert ctx.regime == "UNKNOWN"
        assert ctx.ihsg_trend is None


class TestPortfolioContext:
    def _db(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE paper_trades (ticker TEXT, entry_price REAL, lots INT, "
                     "tp_price REAL, sl_price REAL, capital_used REAL, status TEXT)")
        return conn

    def test_open_trades_and_position_check(self):
        conn = self._db()
        conn.execute("INSERT INTO paper_trades VALUES "
                     "('BBRI', 4500, 10, 4800, 4300, 45000000, 'OPEN')")
        conn.execute("INSERT INTO paper_trades VALUES "
                     "('TLKM', 3000, 5, 3200, 2900, 15000000, 'CLOSED')")
        ctx = afc.build_portfolio_context(conn)
        assert isinstance(ctx, PortfolioContext)
        assert ctx.open_position_count == 1
        assert ctx.has_open_position("BBRI") is True
        assert ctx.has_open_position("TLKM") is False  # CLOSED, not OPEN
        assert ctx.has_open_position("UNKNOWN") is False


class TestRiskContext:
    def test_returns_typed_object(self):
        # Exercises the real paper_trade.py/security.auth read paths — both are read-only
        # (verified during implementation: get_config()/is_entries_blocked()/
        # compute_drawdown() perform no writes, no Telegram calls).
        ctx = afc.build_risk_context()
        assert isinstance(ctx, RiskContext)
        assert isinstance(ctx.entries_blocked, bool)
        assert ctx.auth_mode in ("off", "shadow", "enforce")


class TestExecutionContext:
    def test_returns_typed_object_with_config_values(self):
        ctx = afc.build_execution_context()
        assert isinstance(ctx, ExecutionContext)
        assert ctx.max_position_pct_config == 0.30


class TestBatchContext:
    """AF-2 WP2: get_batch_context()/reset_batch_context() — the four batch-level Tier 1
    objects, cached once per scan cycle (ADR-AF-002's lifecycle rule, scoped to this module
    rather than firm.py's legacy _market_ctx cache)."""

    def _db(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT, open REAL, high REAL, "
                     "low REAL, close REAL, volume REAL)")
        conn.execute("CREATE TABLE paper_trades (ticker TEXT, entry_price REAL, lots INT, "
                     "tp_price REAL, sl_price REAL, capital_used REAL, status TEXT)")
        return conn

    def setup_method(self):
        afc.reset_batch_context()

    def teardown_method(self):
        afc.reset_batch_context()

    def test_returns_all_four_batch_objects(self):
        conn = self._db()
        batch = afc.get_batch_context(conn, market_risk_score=10.0)
        assert set(batch.keys()) == {"market", "portfolio", "risk_limits", "execution"}
        assert isinstance(batch["market"], MarketContext)
        assert isinstance(batch["portfolio"], PortfolioContext)
        assert isinstance(batch["risk_limits"], RiskContext)
        assert isinstance(batch["execution"], ExecutionContext)
        assert batch["market"].market_risk_score == 10.0

    def test_second_call_returns_cached_object_not_recomputed(self):
        conn = self._db()
        first = afc.get_batch_context(conn, market_risk_score=10.0)
        # A second call with a different market_risk_score must NOT overwrite the cache —
        # cached once per scan cycle until reset_batch_context() flushes it.
        second = afc.get_batch_context(conn, market_risk_score=99.0)
        assert first is second
        assert second["market"].market_risk_score == 10.0

    def test_reset_batch_context_flushes_cache(self):
        conn = self._db()
        first = afc.get_batch_context(conn, market_risk_score=10.0)
        afc.reset_batch_context()
        second = afc.get_batch_context(conn, market_risk_score=99.0)
        assert first is not second
        assert second["market"].market_risk_score == 99.0

    def test_broken_builder_degrades_to_default_not_raise(self):
        # No tables at all — every builder's query fails; _safe() must degrade each
        # to its typed default rather than propagate.
        conn = sqlite3.connect(":memory:")
        batch = afc.get_batch_context(conn)
        assert batch["market"] == MarketContext()
        assert batch["portfolio"] == PortfolioContext()


class TestBuildCandidateContext:
    """AF-2 WP2: build_candidate_context() — the per-candidate assembly function scanner.py
    calls at both SignalCandidate construction sites (run_agent_firm_gate,
    rank_bear_watchlist_and_notify)."""

    def _db(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT, open REAL, high REAL, "
                     "low REAL, close REAL, volume REAL)")
        conn.execute("CREATE TABLE stockbit_flow (ticker TEXT, trade_date TEXT, "
                     "verdict TEXT, smart_money TEXT, composite_score INT, foreign_score REAL)")
        conn.execute("CREATE TABLE broker_flow (ticker TEXT, trade_date TEXT, "
                     "broker_code TEXT, side TEXT, lot_value REAL, investor_type TEXT)")
        conn.execute("CREATE TABLE stockbit_flow_bars (ticker TEXT, trade_date TEXT, "
                     "bar_time TEXT, buy_lot INT, sell_lot INT, delta REAL, net_value REAL)")
        conn.execute("CREATE TABLE wf_scores (ticker TEXT, strategy TEXT, "
                     "consistency_pct REAL, avg_return_pct REAL, avg_sharpe REAL, "
                     "weighted_score REAL)")
        conn.execute("CREATE TABLE daily_screen (ticker TEXT, date TEXT, signal TEXT, "
                     "vpin_label TEXT, vol_ratio REAL)")
        conn.execute("CREATE TABLE paper_trades (ticker TEXT, entry_price REAL, lots INT, "
                     "tp_price REAL, sl_price REAL, capital_used REAL, status TEXT)")
        for r in _ohlcv_rows("BBRI", n=60, trend=2.0):
            conn.execute("INSERT INTO ohlcv VALUES (?,?,?,?,?,?,?)", r)
        conn.execute(
            "INSERT INTO stockbit_flow VALUES ('BBRI', date('now'), 'BULLISH', "
            "'STRONG_BUY', 7, 2.1)")
        return conn

    def setup_method(self):
        afc.reset_batch_context()

    def teardown_method(self):
        afc.reset_batch_context()

    def test_returns_exactly_signal_candidate_field_keys(self):
        # Keys must match SignalCandidate's eight new optional fields exactly (ADR-AF-004)
        # so callers can do SignalCandidate(**base, **build_candidate_context(...)).
        from engine.agent_firm.schemas import SignalCandidate
        conn = self._db()
        ctx = afc.build_candidate_context(conn, "BBRI", "2026-07-29")
        expected = {"technical", "flow", "regime_context", "news",
                    "market", "portfolio", "risk_limits", "execution"}
        assert set(ctx.keys()) == expected
        assert set(expected) <= set(SignalCandidate.model_fields.keys())

    def test_populates_real_technical_and_flow_data(self):
        conn = self._db()
        ctx = afc.build_candidate_context(conn, "BBRI", "2026-07-29")
        assert ctx["technical"].sma20 is not None
        assert ctx["technical"].mechanical_direction == "BULLISH"
        assert ctx["flow"].verdict == "BULLISH"
        assert ctx["flow"].composite_score == 7

    def test_candidate_context_attaches_cleanly_to_signal_candidate(self):
        from engine.agent_firm.schemas import SignalCandidate
        conn = self._db()
        ctx = afc.build_candidate_context(conn, "BBRI", "2026-07-29")
        cand = SignalCandidate(
            ticker="BBRI", strategy="vol_weighted", score=1.0,
            scan_time="2026-07-29 10:00", **ctx,
        )
        assert isinstance(cand.technical, TechnicalContext)
        assert cand.technical.mechanical_direction == "BULLISH"
        assert isinstance(cand.market, MarketContext)

    def test_batch_objects_shared_across_candidates_same_cycle(self):
        conn = self._db()
        ctx_a = afc.build_candidate_context(conn, "BBRI", "2026-07-29", market_risk_score=55.0)
        ctx_b = afc.build_candidate_context(conn, "OTHER", "2026-07-29", market_risk_score=99.0)
        # Same scan cycle (no reset_batch_context() in between) → same batch object,
        # first call's market_risk_score wins — matches firm.py's own _market_ctx pattern.
        assert ctx_a["market"] is ctx_b["market"]
        assert ctx_a["market"].market_risk_score == 55.0

    def test_missing_tables_degrade_to_defaults_not_raise(self):
        conn = sqlite3.connect(":memory:")
        ctx = afc.build_candidate_context(conn, "NODATA", "2026-07-29")
        assert ctx["technical"] == TechnicalContext()
        assert ctx["flow"] == FlowContext()
        assert ctx["regime_context"] == RegimeContext()
        assert ctx["news"] == NewsContext()


class TestSessionContext:
    @pytest.mark.parametrize("scan_time,expected", [
        ("2026-07-29 08:35", "premarket"),
        ("2026-07-29 10:00", "regular"),
        ("2026-07-29 16:40", "post-close"),
        ("2026-07-29 15:29", "regular"),
        ("2026-07-29 15:30", "post-close"),
        ("garbage input", "regular"),
    ])
    def test_wib_session_boundaries(self, scan_time, expected):
        ctx = afc.build_session_context(scan_time)
        assert isinstance(ctx, SessionContext)
        assert ctx.wib_session == expected
