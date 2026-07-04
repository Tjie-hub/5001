"""Phase 2C — live selection gates on pooled wf_edge expectancy, not
per-ticker wf_scores consistency (audit C-6, reframed by the 2026-07-04
re-baseline that showed the consistency gate selects money-losers)."""
import sqlite3

import pytest


@pytest.fixture()
def edge_db(tmp_path, monkeypatch):
    import scheduler.scanner as scanner
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


def test_edge_selectable_none_candidates_scans_all(edge_db):
    from scheduler.scanner import _edge_selectable
    conn = sqlite3.connect(edge_db)
    got = _edge_selectable(conn, "BBCA", None)
    conn.close()
    assert got == ["NR7 Breakout", "Volume Profile POC"]


def test_edge_selectable_unknown_ticker_empty(edge_db):
    from scheduler.scanner import _edge_selectable
    conn = sqlite3.connect(edge_db)
    assert _edge_selectable(conn, "NOPE", None) == []
    conn.close()


def test_get_ticker_best_strategies_uses_edge(edge_db, monkeypatch):
    """Only positive-expectancy strategies, disabled ones stripped."""
    import scheduler.scanner as scanner
    monkeypatch.setattr(scanner, "_get_disabled_strategies",
                        lambda: {"Volume Profile POC"})
    from scheduler.scanner import get_ticker_best_strategies
    got = get_ticker_best_strategies("BBCA")
    assert got == ["NR7 Breakout"]          # positive edge, not disabled


def test_get_ticker_best_strategies_empty_when_no_edge(edge_db):
    from scheduler.scanner import get_ticker_best_strategies
    assert get_ticker_best_strategies("NOPE") == []
