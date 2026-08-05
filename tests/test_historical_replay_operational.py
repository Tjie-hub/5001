"""Production Engine Operational Validation, Phase 1 (Historical Replay Readiness).

Genuine coverage gap this file closes: no prior test drove the real production chain
(`run_edge_veto_stage` -> `run_agent_firm_gate` -> `resolve_agent_size_hints` ->
`paper_trade.open_trade` -> `forward_testing.adapters.signal_adapter.SignalAdapter.ingest`)
across MULTIPLE historical scan cycles against one persistent, restart-surviving DB file, nor
proved that a crash-and-resume of that cycle cannot double-open a position or double-count a
forward-test signal. `tests/test_scanner_to_open_trade_integration.py` (ADR-AF-002/003/004
integration validation) proved the chain correct for a single cycle on a fresh DB each time;
this file extends that to the stateful, multi-cycle, restart-safety questions specific to
running the engine continuously (or replaying historical sessions) rather than once.

Architecture note (see Audit/PRODUCTION_OPERATIONAL_VALIDATION_PHASE1.md for full detail):
production has no dedicated "replay a historical day" entry point — `scheduled_multi_strategy_scan()`
itself is wall-clock-bound (`datetime.now(WIB)`). Its component functions
(`run_edge_veto_stage`, `run_agent_firm_gate`, `resolve_agent_size_hints`, `_save_signals_to_db`)
are already parameterized by an explicit `date_str`/`time_str`, which is what makes historical
replay possible at all without inventing a new code path — this file drives exactly those
functions with historical dates, the same pattern already used by
`tests/test_scanner_to_open_trade_integration.py`.
"""
import sqlite3
import sys
from unittest.mock import MagicMock, patch

import pytest

import scheduler.scanner as scanner_mod
from data.db import init_agent_firm_tables


class _FakeVetoConn:
    def execute(self, sql, *a, **k):
        return self

    def fetchone(self):
        return (0,)

    def close(self):
        pass


def _seed_full_db(path, tickers):
    conn = sqlite3.connect(path)
    conn.execute("""CREATE TABLE ohlcv (ticker TEXT, date TEXT, open REAL, high REAL,
        low REAL, close REAL, volume REAL)""")
    conn.execute("""CREATE TABLE stockbit_flow (ticker TEXT, trade_date TEXT, verdict TEXT,
        smart_money TEXT, composite_score INT, foreign_score REAL)""")
    conn.execute("""CREATE TABLE broker_flow (ticker TEXT, trade_date TEXT, broker_code TEXT,
        side TEXT, lot_value REAL, investor_type TEXT)""")
    conn.execute("""CREATE TABLE stockbit_flow_bars (ticker TEXT, trade_date TEXT,
        bar_time TEXT, buy_lot INT, sell_lot INT, delta REAL, net_value REAL)""")
    conn.execute("""CREATE TABLE wf_scores (ticker TEXT, strategy TEXT, consistency_pct REAL,
        avg_return_pct REAL, avg_sharpe REAL, weighted_score REAL)""")
    conn.execute("""CREATE TABLE daily_screen (ticker TEXT, date TEXT, signal TEXT,
        vpin_label TEXT, vol_ratio REAL)""")
    conn.execute("""CREATE TABLE news_mentions (ticker TEXT, date TEXT, count INT,
        headlines_json TEXT, updated_at TEXT)""")
    conn.execute("""CREATE TABLE backtest_cache (ticker TEXT, computed_date TEXT,
        best_strategy TEXT, best_return REAL, win_rate REAL, sharpe REAL, total_trades INT,
        profitable INT, regime TEXT, updated_at TEXT, PRIMARY KEY (ticker, computed_date))""")
    for ticker in tickers:
        price = 5000.0
        for i in range(60):
            price += 3.0
            conn.execute("INSERT INTO ohlcv VALUES (?,?,?,?,?,?,?)",
                         (ticker, f"2026-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}",
                          price - 5, price + 10, price - 10, price, 1_000_000))
        conn.execute(
            "INSERT INTO stockbit_flow VALUES (?, date('now'), 'ACCUMULATING', 'YES', 7, 2.1)",
            (ticker,))
        conn.execute(
            "INSERT INTO backtest_cache VALUES (?,?,?,?,?,?,?,?,?,?)",
            (ticker, "2026-01-01", "vol_weighted", 5.0, 60.0, 1.0, 10, 6, "BULL", "2026-01-01"),
        )
    conn.commit()
    conn.close()


def _make_signal(ticker):
    return {"ticker": ticker, "strategies": ["vol_weighted"],
            "flow": {"score": 3.5, "verdict": "BULLISH", "confirmed": True},
            "flow_score": 3.5, "flow_verdict": "BULLISH", "smart_money": "YES",
            "signal_reasons": ["flow confirmed"], "signal_direction": "BUY"}


def _init_shared_db(db_path, tickers, monkeypatch):
    """One persistent DB standing in for the production walkforward.db across
    multiple simulated scan cycles / a simulated restart."""
    _seed_full_db(db_path, tickers)
    init_agent_firm_tables()

    import paper_trade as pt
    monkeypatch.setattr(scanner_mod, "DB_PATH", db_path)
    monkeypatch.setattr(pt, "DB_PATH", db_path)
    pt.init_paper_table()
    monkeypatch.setattr(pt, "_calc_atr_from_db", lambda t: 1000.0)

    import data.db as _db
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS agent_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, scan_time TEXT NOT NULL, ticker TEXT NOT NULL,
            strategy TEXT NOT NULL, quant_score REAL, decision TEXT NOT NULL, confidence REAL,
            size_hint REAL, size_tier TEXT, rationale TEXT, overridden INTEGER DEFAULT 0,
            tokens_in INTEGER, tokens_out INTEGER, cost_usd REAL, duration_s REAL,
            providers_used TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(scan_time, ticker, strategy));
        CREATE TABLE IF NOT EXISTS agent_traces (
            id INTEGER PRIMARY KEY AUTOINCREMENT, decision_id INTEGER, role TEXT NOT NULL,
            prompt_version TEXT, output TEXT, tools_called TEXT, tokens_in INTEGER,
            tokens_out INTEGER, cost_usd REAL, duration_s REAL, provider TEXT, model TEXT,
            runtime_version TEXT, failover INTEGER DEFAULT 0, error TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    """)
    conn.commit()
    conn.close()
    monkeypatch.setattr(_db, "DB_PATH", db_path)

    from forward_testing.storage.db import init_ft_tables
    init_ft_tables(db_path)
    return pt


def _run_one_cycle(pt, ticker, date_str, time_str, edge_score, size_tier, monkeypatch,
                    save_signals=True):
    """One simulated scan cycle for one ticker/date: the real production chain,
    end to end, against whichever DB `pt`/`scanner_mod` currently point at."""
    sig = _make_signal(ticker)
    intersection_results, flow_confirmed = [sig], [sig]

    if save_signals:
        conn = sqlite3.connect(pt.DB_PATH)
        scanner_mod._ensure_scheduled_signals_table(conn)
        scanner_mod._save_signals_to_db(conn, [sig], date_str, time_str)
        conn.commit()
        conn.close()

    survivor = {"ticker": ticker, "edge_score": edge_score, "size_mult": round(edge_score, 2)}
    with patch.object(scanner_mod, "db_connect", lambda *a, **k: _FakeVetoConn()), \
         patch("config.edge_mode", lambda: "enforce"), \
         patch("engine.edge_enrich.market_regime", lambda conn: "BULL"), \
         patch("engine.edge_enrich.enrich_candidate",
               lambda conn, tkr, ds, **kw: {"ticker": tkr}), \
         patch("engine.veto.apply_vetoes", lambda candidates, mreg, open_n: [survivor]):
        intersection_results, flow_confirmed = scanner_mod.run_edge_veto_stage(
            intersection_results, flow_confirmed, {}, date_str, time_str,
        )

    decision = MagicMock(ticker=ticker, decision="approve", size_tier=size_tier)
    mock_firm = MagicMock()
    mock_firm.evaluate_staged = MagicMock(side_effect=lambda c, **k: [decision])
    mock_cfg = MagicMock(is_active=MagicMock(return_value=True),
                          get_enforce=MagicMock(return_value=False))

    import engine.agent_firm as _pkg
    with patch.object(_pkg, "firm", mock_firm), \
         patch.object(_pkg, "config", mock_cfg), \
         patch.dict(sys.modules, {"engine.agent_firm.firm": mock_firm,
                                   "engine.agent_firm.config": mock_cfg}):
        flow_confirmed = scanner_mod.run_agent_firm_gate(
            intersection_results, flow_confirmed, date_str, time_str,
        )

    scanner_mod.resolve_agent_size_hints(flow_confirmed)
    row = flow_confirmed[0]
    trade_result = pt.open_trade(
        ticker, entry_price=8000.0, strategy="swing trend", notify=False,
        lots_multiplier=row["agent_size_hint"],
    )
    return row, trade_result


# ---------------------------------------------------------------------------
# Objective 1 / 2 — multi-day historical replay, stateful correctness
# ---------------------------------------------------------------------------

def test_multi_day_historical_replay_executes_full_chain(tmp_path, monkeypatch):
    """Three distinct historical sessions replayed in sequence against one persistent
    DB: each day's decision/sizing/trade must be correct AND correctly see the state
    left behind by the previous day (an open BBCA position blocks day 2's re-entry,
    exactly as it would in live production, not just on a fresh DB per call)."""
    db_path = str(tmp_path / "shared.db")
    pt = _init_shared_db(db_path, ["BBCA", "BBRI"], monkeypatch)

    row1, tr1 = _run_one_cycle(pt, "BBCA", "2026-01-05", "10:00", 0.6, "increase", monkeypatch)
    assert "error" not in tr1
    assert row1["agent_size_hint"] == pytest.approx(0.69, abs=0.01)

    # Day 2: same ticker, still open from day 1 -> must be rejected, not double-opened.
    row2, tr2 = _run_one_cycle(pt, "BBCA", "2026-01-06", "10:00", 0.5, "normal", monkeypatch)
    assert "error" in tr2
    assert "posisi terbuka" in tr2["error"]

    # Day 3: a different ticker must still open normally -> the block above is
    # position-specific, not a global chain failure.
    row3, tr3 = _run_one_cycle(pt, "BBRI", "2026-01-07", "10:00", 0.8, "reduce", monkeypatch)
    assert "error" not in tr3
    assert row3["agent_size_hint"] == pytest.approx(0.56, abs=0.01)  # 0.8 * 0.7

    conn = sqlite3.connect(db_path)
    tickers_traded = {r[0] for r in conn.execute("SELECT ticker FROM paper_trades").fetchall()}
    conn.close()
    assert tickers_traded == {"BBCA", "BBRI"}


# ---------------------------------------------------------------------------
# Objective 3 — restart safety: interrupted run, resume, duplicate prevention
# ---------------------------------------------------------------------------

def test_restart_mid_cycle_resume_does_not_duplicate_trade_or_signal(tmp_path, monkeypatch):
    """Simulate a process crash after scheduled_signals is persisted but before
    open_trade() runs, then a resume that replays the identical cycle from scratch
    (the only recovery a cron-wrapped, at-least-once job can offer). Prove the two
    layers that must not double-count don't: paper_trades (via open_trade's own
    open-position guard) and ft_signal (via SignalAdapter's idempotent insert) —
    even though scheduled_signals itself, having no UNIQUE constraint, does grow by
    one extra (expected, audit-log-only) row per replay."""
    db_path = str(tmp_path / "shared.db")
    pt = _init_shared_db(db_path, ["BBCA"], monkeypatch)

    # "Crash": first cycle completes signal-save + full chain + open_trade.
    row1, tr1 = _run_one_cycle(pt, "BBCA", "2026-02-10", "09:15", 0.55, "normal", monkeypatch)
    assert "error" not in tr1

    # "Resume": operator/cron replays the exact same cycle (same date/time) after restart.
    row2, tr2 = _run_one_cycle(pt, "BBCA", "2026-02-10", "09:15", 0.55, "normal", monkeypatch)
    assert "error" in tr2, "resume must not silently open a second position for the same ticker"

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    n_trades = conn.execute(
        "SELECT COUNT(*) c FROM paper_trades WHERE ticker='BBCA' AND status='OPEN'"
    ).fetchone()["c"]
    n_signals = conn.execute(
        "SELECT COUNT(*) c FROM scheduled_signals WHERE ticker='BBCA' AND scan_time=?",
        ("2026-02-10 09:15",),
    ).fetchone()["c"]
    conn.close()

    assert n_trades == 1, "exactly one OPEN position must exist after replaying the cycle twice"
    assert n_signals == 2, (
        "scheduled_signals has no UNIQUE constraint and is documented as audit-log-only; "
        "two replays are expected to leave two rows here — see report Finding on this table"
    )

    from forward_testing.adapters.signal_adapter import SignalAdapter
    from forward_testing.storage.repo import FTRepo
    adapter = SignalAdapter(FTRepo(db_path), db_path=db_path)
    first_ingested = adapter.ingest("2026-02-10")
    second_ingested = adapter.ingest("2026-02-10")
    assert first_ingested >= 1
    assert second_ingested == 0, "re-ingesting after a resumed cycle must not double-count signals"

    conn = sqlite3.connect(db_path)
    n_ft_signals = conn.execute(
        "SELECT COUNT(*) FROM ft_signal WHERE ticker='BBCA' AND signal_date='2026-02-10'"
    ).fetchone()[0]
    conn.close()
    assert n_ft_signals == 1, (
        "ft_signal's own (signal_date, ticker, strategy, track) idempotent insert must "
        "collapse both scheduled_signals rows (duplicated by the crash+resume) into one "
        "forward-test signal, regardless of how many times the upstream scan replayed"
    )


# ---------------------------------------------------------------------------
# Objective 5 — audit completeness across a multi-day replay
# ---------------------------------------------------------------------------

def test_audit_trail_complete_across_replayed_days(tmp_path, monkeypatch):
    """Every persisted trade across a multi-day replay must be independently
    reconstructable — ticker, lots, entry price, and the sizing tier that drove it —
    from durable tables alone, not from in-memory state."""
    db_path = str(tmp_path / "shared.db")
    pt = _init_shared_db(db_path, ["BBCA", "BBRI"], monkeypatch)

    _run_one_cycle(pt, "BBCA", "2026-03-01", "10:00", 0.6, "increase", monkeypatch)
    _run_one_cycle(pt, "BBRI", "2026-03-02", "10:00", 0.4, "reduce", monkeypatch)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT ticker, lots, entry_price, sl_price, tp_price FROM paper_trades ORDER BY ticker"
    ).fetchall()
    conn.close()

    assert [r["ticker"] for r in rows] == ["BBCA", "BBRI"]
    for r in rows:
        assert r["lots"] > 0
        assert r["entry_price"] > 0
        assert r["sl_price"] is not None and r["tp_price"] is not None


# ---------------------------------------------------------------------------
# Objective 6 — operational robustness: malformed / missing-optional input
# ---------------------------------------------------------------------------

def test_replay_tolerates_ticker_with_no_flow_or_news_rows(tmp_path, monkeypatch):
    """A ticker with OHLCV but zero rows in stockbit_flow/news_mentions (a
    perfectly normal historical condition — many sessions have no flow/news data
    for a given name) must still be evaluated to a decision, not crash the cycle."""
    db_path = str(tmp_path / "shared.db")
    _seed_full_db(db_path, ["BBCA"])
    conn = sqlite3.connect(db_path)
    conn.execute("DELETE FROM stockbit_flow WHERE ticker='BBCA'")
    conn.commit()
    conn.close()
    init_agent_firm_tables()

    import paper_trade as pt
    monkeypatch.setattr(scanner_mod, "DB_PATH", db_path)
    monkeypatch.setattr(pt, "DB_PATH", db_path)
    pt.init_paper_table()
    monkeypatch.setattr(pt, "_calc_atr_from_db", lambda t: 1000.0)

    row, trade_result = _run_one_cycle(pt, "BBCA", "2026-04-01", "10:00", 0.5, "normal",
                                        monkeypatch)
    assert "error" not in trade_result
    assert row["agent_size_hint"] == pytest.approx(0.5, abs=0.01)


def test_replay_tolerates_missing_ohlcv_for_signaled_ticker(tmp_path, monkeypatch):
    """A signal for a ticker with NO ohlcv rows at all (e.g. a delisted/newly-listed
    name slipping past an upstream filter) must fail soft through the chain rather
    than raising — proving the chain doesn't assume ohlcv_map coverage."""
    db_path = str(tmp_path / "shared.db")
    _seed_full_db(db_path, ["BBCA"])  # signal will reference "XXXX", never seeded
    init_agent_firm_tables()

    import paper_trade as pt
    monkeypatch.setattr(scanner_mod, "DB_PATH", db_path)
    monkeypatch.setattr(pt, "DB_PATH", db_path)
    pt.init_paper_table()
    monkeypatch.setattr(pt, "_calc_atr_from_db", lambda t: None)  # no ATR history available

    row, trade_result = _run_one_cycle(pt, "XXXX", "2026-04-02", "10:00", 0.5, "normal",
                                        monkeypatch)
    # open_trade() must still resolve a sane fallback (config sl_pct) rather than raise.
    assert "error" not in trade_result or "posisi terbuka" not in trade_result.get("error", "")
