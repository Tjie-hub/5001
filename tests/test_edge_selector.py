"""Phase 2C — live selection gates on pooled wf_edge expectancy, not
per-ticker wf_scores consistency (audit C-6, reframed by the 2026-07-04
re-baseline that showed the consistency gate selects money-losers)."""
import sqlite3

import pytest


@pytest.fixture()
def edge_db(tmp_path, monkeypatch):
    import scheduler.scanner as scanner
    import engine.registry_loader as rl
    # This suite tests the LEGACY (ungoverned) wf_edge path; isolate it from
    # the real Edge Registry so M1 governance doesn't apply here.
    monkeypatch.setattr(rl, "registry_governance", lambda s: None)
    db = str(tmp_path / "e.db")
    monkeypatch.setattr(scanner, "DB_PATH", db)
    conn = sqlite3.connect(db)
    conn.execute("""CREATE TABLE wf_edge (
        ticker TEXT, strategy TEXT, expectancy_pct REAL, expectancy_rp REAL,
        win_rate REAL, consistency_pct REAL, sharpe REAL, n_trades INTEGER,
        windows_tested INTEGER, last_computed TEXT, PRIMARY KEY(ticker,strategy))""")
    rows = [
        ("BBCA", "NR7 Breakout",  1.70, 0, 56.0, 40.0, 0.5, 1061, 15, "x"),
        ("BBCA", "momentum",     -0.69, 0, 30.0, 20.0, -0.3, 500, 15, "x"),
        ("BBCA", "vwap_reversion",-0.86, 0, 29.0, 30.0, -0.4, 800, 15, "x"),
        ("BBCA", "Volume Profile POC", 0.9, 0, 51.0, 12.0, 0.2, 40, 15, "x"),
    ]
    conn.executemany("INSERT INTO wf_edge VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    conn.close()
    return db


def test_edge_selectable_returns_only_positive_expectancy(edge_db):
    from scheduler.scanner import _edge_selectable
    conn = sqlite3.connect(edge_db)
    got = _edge_selectable(conn, "BBCA",
                           ["NR7 Breakout", "momentum", "vwap_reversion",
                            "Volume Profile POC"])
    conn.close()
    # negatives excluded; positives ordered best-first
    assert got == ["NR7 Breakout", "Volume Profile POC"]


def test_edge_selectable_none_candidates_is_registry_only(edge_db):
    """D-031 Decision 1 (docs/roadmap/DECISION_LOG.md, ratified 2026-08-20):
    candidates=None has no legacy wf_edge exception -- unlike the explicit-
    candidates branch (test_edge_selectable_returns_only_positive_expectancy
    above), a strategy with no registry entry is NOT selectable through this
    path, even with positive wf_edge expectancy. This fixture's
    registry_governance stub always returns None (see edge_db above), so
    every wf_edge row here is "unregistered" and none should be selected --
    this is the exact scan-all/no-registry-check behavior that used to leak
    through before the fix; it must now return empty."""
    from scheduler.scanner import _edge_selectable
    conn = sqlite3.connect(edge_db)
    got = _edge_selectable(conn, "BBCA", None)
    conn.close()
    assert got == []


def test_edge_selectable_unknown_ticker_empty(edge_db):
    from scheduler.scanner import _edge_selectable
    conn = sqlite3.connect(edge_db)
    assert _edge_selectable(conn, "NOPE", None) == []
    conn.close()


def test_get_ticker_best_strategies_registry_only_no_admission(edge_db, monkeypatch):
    """D-031 Decision 1: get_ticker_best_strategies() (the candidates=None
    caller) is Registry-only -- with this fixture's registry_governance
    stub always returning None, nothing here has a registry entry, so
    nothing is selectable regardless of positive wf_edge expectancy or the
    disabled-strategies filter (which runs after selection and so is now
    moot -- selection is already empty)."""
    import scheduler.scanner as scanner
    monkeypatch.setattr(scanner, "_get_disabled_strategies",
                        lambda: {"Volume Profile POC"})
    from scheduler.scanner import get_ticker_best_strategies
    got = get_ticker_best_strategies("BBCA")
    assert got == []


def test_get_ticker_best_strategies_selects_approved_strategy(edge_db, monkeypatch):
    """D-031 Decision 1 positive path: a strategy that IS Registry-APPROVED
    (ticker in its frozen universe) is still selectable through
    candidates=None -- the fix is Registry-only, not Registry-blind."""
    import scheduler.scanner as scanner
    import engine.registry_loader as rl
    monkeypatch.setattr(
        rl, "registry_governance",
        lambda s: {"BBCA"} if s == "NR7 Breakout" else None,
    )
    monkeypatch.setattr(scanner, "_get_disabled_strategies", lambda: set())
    from scheduler.scanner import get_ticker_best_strategies
    got = get_ticker_best_strategies("BBCA")
    assert got == ["NR7 Breakout"]


def test_get_ticker_best_strategies_empty_when_no_edge(edge_db):
    from scheduler.scanner import get_ticker_best_strategies
    assert get_ticker_best_strategies("NOPE") == []


import numpy as np
import pandas as pd


def _bull_df(n=90):
    dates = pd.date_range("2026-01-01", periods=n, freq="D")
    close = 1000 + np.arange(n) * 8.0      # steady uptrend -> BULL
    return pd.DataFrame({"date": dates, "open": close - 2, "high": close + 6,
                         "low": close - 6, "close": close,
                         "volume": np.full(n, 1e6)})


def test_adaptive_selector_uses_edge(edge_db, monkeypatch):
    """BULL regime: momentum is a candidate but has NEGATIVE edge -> excluded;
    a positive-edge BULL candidate is selected. Uses wf_edge, not wf_scores."""
    import scheduler.scanner as scanner
    import engine.regime_filter as rf
    monkeypatch.setattr(rf, "detect_regime", lambda df: "BULL")  # imported locally in selector
    monkeypatch.setattr(scanner, "_get_disabled_strategies", lambda: set())
    monkeypatch.setattr(scanner, "_macro_panic_state", lambda: False)
    monkeypatch.setattr(scanner, "_event_guard_active", lambda: (False, 1.0))
    conn = sqlite3.connect(edge_db)
    conn.execute("INSERT INTO wf_edge VALUES ('BBCA','Trend Following Breakout',"
                 "1.2,0,55,40,0.4,60,15,'x')")
    # Swing Trend has positive edge but is NOT in the BULL regime map — it must
    # be excluded, proving the PRIMARY regime-filtered block (not the unfiltered
    # fallback) drove selection.
    conn.execute("INSERT INTO wf_edge VALUES ('BBCA','Swing Trend',"
                 "2.0,0,60,45,0.6,80,15,'x')")
    conn.commit()
    conn.close()
    from scheduler.scanner import adaptive_strategy_selector
    got = adaptive_strategy_selector("BBCA", _bull_df())
    assert "Trend Following Breakout" in got
    assert "momentum" not in got            # negative edge -> not selected
    assert "vwap_reversion" not in got
    assert "Swing Trend" not in got         # positive edge but off-regime-map


def test_default_disabled_covers_negative_roster():
    """The 8 strategies the 2026-07-04 re-baseline proved lose money are
    disabled by default."""
    from scheduler.scanner import _DEFAULT_DISABLED
    disabled = {s.strip() for s in _DEFAULT_DISABLED.split(",")}
    for loser in ("vwap_reversion", "vol_weighted", "conservative", "momentum",
                  "Liquidity Sweep", "ORB", "Volume Profile POC",
                  "Inside Bar Breakout"):
        assert loser in disabled, loser
    assert "NR7 Breakout" not in disabled     # the one positive edge stays enabled


def test_momentum_scan_skips_when_momentum_disabled(monkeypatch):
    """scan_momentum_signals must not run when 'momentum' is disabled (it opens
    Momentum-Following trades directly, bypassing the adaptive selector)."""
    import scheduler.scanner as scanner
    monkeypatch.setattr(scanner, "_get_disabled_strategies", lambda: {"momentum"})
    monkeypatch.setattr(scanner, "get_all_tickers", lambda: [])
    out = scanner.scan_momentum_signals()
    assert out == []


def test_momentum_scan_skips_without_registry_admission(monkeypatch):
    """T7 production-execution-boundary audit: even when 'momentum' is NOT in
    the disabled list, scan_momentum_signals must not auto-open without real
    Edge Registry admission for the Momentum Following book -- defense in
    depth against silently re-enabling live trading by editing the disabled
    list alone. Today it has no registry entry at all, so this always blocks."""
    import engine.calendar_filter as cal
    import scheduler.scanner as scanner
    import engine.registry_loader as rl
    monkeypatch.setattr(cal, "is_trading_day", lambda: (True, "trading day"))
    monkeypatch.setattr(cal, "is_blackout_day", lambda: (False, ""))
    monkeypatch.setattr(scanner, "_get_disabled_strategies", lambda: set())   # NOT disabled
    monkeypatch.setattr(rl, "registry_governance", lambda s: None)           # no admission

    def _must_not_reach(*a, **k):
        raise AssertionError("scan proceeded past the registry admission gate")
    monkeypatch.setattr(scanner, "get_all_tickers", _must_not_reach)
    out = scanner.scan_momentum_signals()
    assert out == []
