"""Regression tests for the refresh_wf_scores DB-lock fix (incident 2026-06-25).

The old implementation held one write transaction open across the entire
~35-minute walk-forward compute loop, locking out every other writer (the EOD
scans). These tests pin the fix:
  1. during the compute phase the DB stays writable by another connection
  2. results still land in wf_scores
  3. a concurrent refresh (live pid holding _job_lock) is skipped, a stale one is not
"""
import os
import sqlite3
import pandas as pd
import pytest

import scheduler.jobs as jobs
import research.walkforward_multi as wfm


def _mini_df(n=80):
    return pd.DataFrame({
        "date": [f"2026-01-{i%28+1:02d}" for i in range(n)],
        "open": [100.0] * n, "high": [101.0] * n,
        "low": [99.0] * n, "close": [100.0] * n, "volume": [1000] * n,
    })


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db = str(tmp_path / "wf_test.db")
    # seed a probe table so the concurrent-writer check has somewhere to write
    with sqlite3.connect(db) as c:
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("CREATE TABLE _probe (n INTEGER)")
        # pre-create wf_scores so a regression to the long-held-txn pattern would
        # actually take the write lock during compute (faithful red).
        c.execute("CREATE TABLE wf_scores (ticker TEXT NOT NULL, strategy TEXT NOT NULL, "
                  "consistency_pct REAL, avg_return_pct REAL, avg_sharpe REAL, "
                  "weighted_score REAL, windows_tested INTEGER, updated_at TEXT, "
                  "PRIMARY KEY(ticker,strategy))")
    monkeypatch.setattr(jobs, "DB_PATH", db)
    monkeypatch.setattr(jobs, "get_all_tickers", lambda: ["AAA", "BBB"])
    monkeypatch.setattr(jobs, "_load_ohlcv_bulk", lambda final_only=False: {"AAA": _mini_df(), "BBB": _mini_df()})
    monkeypatch.setattr(jobs, "send_telegram", lambda *a, **k: None)
    return db


def _ranked():
    return {"ranked": [{
        "strategy": "TFB", "consistency_pct": 50.0, "avg_return_pct": 1.2,
        "avg_sharpe": 0.5, "score": 10.0, "windows_tested": 4, "windows": [],
    }]}


def test_db_writable_during_compute(tmp_db, monkeypatch):
    """The core regression: refresh must NOT hold a write lock while computing."""
    probe_results = []

    def fake_wf(df):
        # simulate a concurrent writer (an EOD scan) trying to write mid-compute
        try:
            with sqlite3.connect(tmp_db, timeout=1) as c:
                c.execute("PRAGMA busy_timeout=1000")
                c.execute("BEGIN IMMEDIATE")
                c.execute("INSERT INTO _probe VALUES (1)")
                c.commit()
            probe_results.append("ok")
        except sqlite3.OperationalError as e:
            probe_results.append(f"locked: {e}")
        return _ranked()

    monkeypatch.setattr(wfm, "run_walk_forward", fake_wf)
    jobs.refresh_wf_scores()

    assert probe_results, "compute never ran"
    locked = [r for r in probe_results if r != "ok"]
    assert not locked, f"DB was locked during compute (old bug): {locked}"


def test_scores_written(tmp_db, monkeypatch):
    monkeypatch.setattr(wfm, "run_walk_forward", lambda df: _ranked())
    jobs.refresh_wf_scores()
    with sqlite3.connect(tmp_db) as c:
        rows = c.execute("SELECT ticker, strategy FROM wf_scores ORDER BY ticker").fetchall()
    assert rows == [("AAA", "TFB"), ("BBB", "TFB")]


def test_concurrent_refresh_skipped(tmp_db, monkeypatch):
    """A live pid holding the lock blocks a second run; results stay empty."""
    with sqlite3.connect(tmp_db) as c:
        c.execute("CREATE TABLE IF NOT EXISTS _job_lock "
                  "(job TEXT PRIMARY KEY, pid INTEGER, started_at TEXT)")
        c.execute("INSERT OR REPLACE INTO _job_lock VALUES ('refresh_wf_scores', ?, '2026-01-01')",
                  (os.getpid(),))  # our own pid = guaranteed alive
    called = []
    monkeypatch.setattr(wfm, "run_walk_forward", lambda df: called.append(1) or _ranked())
    jobs.refresh_wf_scores()
    assert not called, "refresh ran despite a live concurrent lock"


def test_stale_lock_ignored(tmp_db, monkeypatch):
    """A dead pid in the lock must not block a new run."""
    with sqlite3.connect(tmp_db) as c:
        c.execute("CREATE TABLE IF NOT EXISTS _job_lock "
                  "(job TEXT PRIMARY KEY, pid INTEGER, started_at TEXT)")
        c.execute("INSERT OR REPLACE INTO _job_lock VALUES ('refresh_wf_scores', 999999999, '2026-01-01')")
    monkeypatch.setattr(wfm, "run_walk_forward", lambda df: _ranked())
    jobs.refresh_wf_scores()
    with sqlite3.connect(tmp_db) as c:
        n = c.execute("SELECT COUNT(*) FROM wf_scores").fetchone()[0]
    assert n == 2, "stale lock wrongly blocked the run"
