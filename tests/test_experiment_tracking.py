"""Experiment tracking + dataset fingerprinting (audit R-4, Phase A 3+4).

Contract: every research batch run lands one append-only row in research_runs
carrying run_id, git commit, dataset fingerprint, params, timings, status and
metrics. Finalizing a run touches only its own row; previous experiments are
never overwritten. Research outputs (wf_scores/wf_edge/backtest_cache rows)
reference the run that produced them via run_id.
"""
import os
import sqlite3
import tempfile
import time

import numpy as np
import pandas as pd
import pytest

from research.tracking import (
    dataset_fingerprint,
    ensure_research_runs_table,
    git_commit,
    track_run,
)


def _mkdb(path):
    conn = sqlite3.connect(path)
    conn.execute("""CREATE TABLE ohlcv (
        id INTEGER PRIMARY KEY AUTOINCREMENT, ticker TEXT NOT NULL,
        date TEXT NOT NULL, open REAL, high REAL, low REAL, close REAL,
        volume REAL, is_final INTEGER DEFAULT 1, UNIQUE(ticker, date))""")
    conn.execute("""CREATE TABLE corporate_actions (
        ticker TEXT NOT NULL, date TEXT NOT NULL, action TEXT NOT NULL,
        value REAL, source TEXT, updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (ticker, date, action))""")
    conn.execute(
        "INSERT INTO ohlcv (ticker,date,open,high,low,close,volume) "
        "VALUES ('AAAA','2025-01-01',100,110,90,100,1000)")
    conn.commit()
    return conn


# ─── Dataset fingerprint (Phase 4) ───────────────────────────────────────────

def test_fingerprint_is_stable_and_carries_metadata():
    with tempfile.TemporaryDirectory() as tmp:
        conn = _mkdb(os.path.join(tmp, "t.db"))
        fp1 = dataset_fingerprint(conn)
        fp2 = dataset_fingerprint(conn)
        conn.close()
    assert fp1 == fp2
    assert fp1["max_date"] == "2025-01-01"
    assert fp1["total_rows"] == 1
    assert len(fp1["sha256"]) == 64


def test_fingerprint_changes_when_data_changes():
    with tempfile.TemporaryDirectory() as tmp:
        conn = _mkdb(os.path.join(tmp, "t.db"))
        fp1 = dataset_fingerprint(conn)
        conn.execute(
            "INSERT INTO ohlcv (ticker,date,open,high,low,close,volume) "
            "VALUES ('AAAA','2025-01-02',101,111,91,101,1000)")
        conn.commit()
        fp2 = dataset_fingerprint(conn)
        conn.close()
    assert fp1["sha256"] != fp2["sha256"]
    assert fp2["total_rows"] == 2
    assert fp2["max_date"] == "2025-01-02"


def test_fingerprint_covers_corporate_actions():
    """Research input = prices AND the split table that adjusts them."""
    with tempfile.TemporaryDirectory() as tmp:
        conn = _mkdb(os.path.join(tmp, "t.db"))
        fp1 = dataset_fingerprint(conn)
        conn.execute(
            "INSERT INTO corporate_actions (ticker,date,action,value,source) "
            "VALUES ('AAAA','2025-01-01','split',2.0,'t')")
        conn.commit()
        fp2 = dataset_fingerprint(conn)
        conn.close()
    assert fp1["sha256"] != fp2["sha256"]


def test_fingerprint_fail_soft_without_corporate_actions_table():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT, open REAL, "
                 "high REAL, low REAL, close REAL, volume REAL)")
    conn.execute("INSERT INTO ohlcv VALUES ('AAAA','2025-01-01',1,1,1,1,1)")
    fp = dataset_fingerprint(conn)
    conn.close()
    assert len(fp["sha256"]) == 64


# ─── track_run (Phase 3) ─────────────────────────────────────────────────────

def test_track_run_records_success():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "t.db")
        _mkdb(db).close()
        with track_run("wf-refresh", params={"final_only": True},
                       db_path=db) as run:
            assert run.run_id
            run.metrics["tickers_updated"] = 7
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT run_id, kind, git_commit, dataset_fingerprint, params_json,"
            " started_at, finished_at, duration_s, status, metrics_json "
            "FROM research_runs").fetchone()
        conn.close()
    assert row[0] == run.run_id
    assert row[1] == "wf-refresh"
    assert row[3] and len(row[3]) == 64          # fingerprint recorded
    assert '"final_only": true' in row[4]
    assert row[5] and row[6]                     # started + finished
    assert row[7] >= 0                           # duration
    assert row[8] == "DONE"
    assert '"tickers_updated": 7' in row[9]


def test_track_run_records_error_and_reraises():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "t.db")
        _mkdb(db).close()
        with pytest.raises(ValueError):
            with track_run("study", db_path=db):
                raise ValueError("boom")
        conn = sqlite3.connect(db)
        status, error = conn.execute(
            "SELECT status, error FROM research_runs").fetchone()
        conn.close()
    assert status == "ERROR"
    assert "boom" in error


def test_runs_are_append_only():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "t.db")
        _mkdb(db).close()
        with track_run("study", db_path=db) as r1:
            r1.metrics["x"] = 1
        with track_run("study", db_path=db) as r2:
            r2.metrics["x"] = 2
        conn = sqlite3.connect(db)
        rows = conn.execute(
            "SELECT run_id, status, metrics_json FROM research_runs "
            "ORDER BY started_at").fetchall()
        conn.close()
    assert len(rows) == 2
    assert rows[0][0] == r1.run_id and rows[1][0] == r2.run_id
    assert '"x": 1' in rows[0][2] and '"x": 2' in rows[1][2]


def test_git_commit_returns_hash_or_none():
    c = git_commit()
    assert c is None or (isinstance(c, str) and len(c) >= 7)


# ─── Job integration: outputs reference their run ────────────────────────────

def _seed_wf_corpus(db):
    """~450 bars of a synthetic ticker — enough for >=1 WF window."""
    conn = _mkdb(db)
    conn.execute("DELETE FROM ohlcv")
    i = np.arange(450)
    close = 1000.0 + 2.0 * i + 20.0 * np.sin(i / 7.0)
    dates = pd.bdate_range("2023-06-01", periods=450).strftime("%Y-%m-%d")
    rows = [("SYNT", d, c - 3, c + 6, c - 6, c, 1_000_000 * (3.0 if k % 7 == 0 else 1.0))
            for k, (d, c) in enumerate(zip(dates, close))]
    conn.executemany(
        "INSERT INTO ohlcv (ticker,date,open,high,low,close,volume) "
        "VALUES (?,?,?,?,?,?,?)", rows)
    conn.commit()
    conn.close()


def test_refresh_wf_scores_stamps_run_id(monkeypatch):
    import research.jobs as jobs
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "t.db")
        _seed_wf_corpus(db)
        monkeypatch.setattr(jobs, "DB_PATH", db)
        monkeypatch.setattr("data.loaders.DB_PATH", db)
        monkeypatch.setattr(jobs, "send_telegram", lambda *a, **k: None)
        jobs.refresh_wf_scores()
        conn = sqlite3.connect(db)
        run = conn.execute(
            "SELECT run_id, status, dataset_fingerprint FROM research_runs "
            "WHERE kind='wf-refresh'").fetchone()
        wf_run_ids = {r[0] for r in conn.execute(
            "SELECT DISTINCT run_id FROM wf_scores").fetchall()}
        edge_run_ids = {r[0] for r in conn.execute(
            "SELECT DISTINCT run_id FROM wf_edge").fetchall()}
        conn.close()
    assert run is not None and run[1] == "DONE" and len(run[2]) == 64
    assert wf_run_ids == {run[0]}
    assert edge_run_ids <= {run[0]}   # empty allowed if no strategy clears N_MIN


def test_refresh_backtest_cache_stamps_run_id(monkeypatch):
    import research.jobs as jobs
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "t.db")
        _seed_wf_corpus(db)
        monkeypatch.setattr(jobs, "DB_PATH", db)
        monkeypatch.setattr("data.loaders.DB_PATH", db)
        jobs._refresh_backtest_cache()
        conn = sqlite3.connect(db)
        run = conn.execute(
            "SELECT run_id, status FROM research_runs "
            "WHERE kind='backtest-cache'").fetchone()
        cache_run_ids = {r[0] for r in conn.execute(
            "SELECT DISTINCT run_id FROM backtest_cache").fetchall()}
        conn.close()
    assert run is not None and run[1] == "DONE"
    assert cache_run_ids == {run[0]}
