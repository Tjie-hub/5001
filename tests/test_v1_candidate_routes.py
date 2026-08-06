"""Tests for routes/v1/candidates.py -- /api/v1/candidates/* (Production
Engine Phase 2, Workstream 2C Task 2C-4).

Five sources: candidate_watchlist_snapshot (current/{date}, via
engine.watchlist_report), daily_screen (screening, via screener.db),
reversal_watchlist / live scan (reversal-watchlist, via
screener.reversal_filter -- migrated from the removed legacy
/api/screener/reversal), and the premover watchlist table (premover-
watchlist, via engine.premover_detector -- migrated from the removed
legacy /api/premover/watchlist). Seeded via the real writer functions.
"""
import sqlite3

import pytest

from routes.v1 import api_v1_bp


@pytest.fixture
def env(tmp_path, monkeypatch):
    db = tmp_path / "wf.db"
    conn = sqlite3.connect(str(db))
    conn.executescript("""
        CREATE TABLE daily_screen (date TEXT, ticker TEXT, close INTEGER,
            volume INTEGER, avg_vol_20d INTEGER, vol_ratio REAL, delta INTEGER);
        CREATE TABLE stockbit_flow (ticker TEXT, trade_date TEXT, smart_money TEXT,
            verdict TEXT, net_value INTEGER);
        CREATE TABLE idx_tickers (ticker TEXT, in_lq45 INTEGER, in_idx30 INTEGER, in_idx80 INTEGER);
        CREATE TABLE ohlcv (ticker TEXT, date TEXT, high REAL, low REAL, close REAL);
    """)
    conn.commit()
    conn.close()

    import config
    monkeypatch.setattr(config, "DB_PATH", str(db))

    # screener.db captured its own copy of DB_PATH at import time
    # (`from config import DB_PATH`), so patching config.DB_PATH alone
    # doesn't reach it -- screener.db.get_screen_results() would otherwise
    # silently read the real default DB.
    import screener.db as screener_db_mod
    monkeypatch.setattr(screener_db_mod, "DB_PATH", str(db))

    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(api_v1_bp)
    return app.test_client(), str(db)


@pytest.fixture
def client(env):
    c, _ = env
    return c


def _cands(*tickers):
    return [{"ticker": t, "sources": ["R"], "conviction": 50.0,
             "vol_ratio": 0.0, "reason": ""} for t in tickers]


def _seed_universe(db, date_str, *tickers):
    from engine.watchlist_report import record_snapshot
    conn = sqlite3.connect(db)
    record_snapshot(conn, date_str, _cands(*tickers))
    conn.close()


def _seed_screening(db, date_str, ticker, vol_ratio=1.5):
    conn = sqlite3.connect(db)
    conn.execute("INSERT INTO daily_screen (date, ticker, close, volume, "
                 "avg_vol_20d, vol_ratio, delta) VALUES (?,?,100,1000,800,?,0)",
                 (date_str, ticker, vol_ratio))
    conn.commit()
    conn.close()


def _seed_premover(db, ticker, score=75, pattern_type="CONTINUATION"):
    from engine.premover_detector import _init_table
    conn = sqlite3.connect(db)
    _init_table(conn)
    conn.execute(
        "INSERT INTO watchlist_premover (ticker, score, pattern_type, detected_at, fired) "
        "VALUES (?,?,?,date('now'),0)",
        (ticker, score, pattern_type),
    )
    conn.commit()
    conn.close()


class TestCandidatesCurrentAndByDate:
    def test_current_returns_latest(self, env):
        c, db = env
        _seed_universe(db, "2026-08-01", "AKRA")
        _seed_universe(db, "2026-08-05", "CPIN")

        resp = c.get("/api/v1/candidates")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["date"] == "2026-08-05"
        assert [r["ticker"] for r in data["candidates"]] == ["CPIN"]

    def test_current_404_when_nothing_ever_snapshotted(self, client):
        resp = client.get("/api/v1/candidates")
        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "NO_CANDIDATE_DATA"

    def test_by_date_returns_that_dates_snapshot(self, env):
        c, db = env
        _seed_universe(db, "2026-08-01", "AKRA")
        resp = c.get("/api/v1/candidates/2026-08-01")
        assert resp.status_code == 200
        assert [r["ticker"] for r in resp.get_json()["data"]["candidates"]] == ["AKRA"]

    def test_by_date_404_when_no_snapshot(self, env):
        c, db = env
        _seed_universe(db, "2026-08-01", "AKRA")
        resp = c.get("/api/v1/candidates/2020-01-01")
        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "NO_CANDIDATE_DATA"


class TestCandidatesScreening:
    def test_returns_screen_results_for_date(self, env):
        c, db = env
        _seed_screening(db, "2026-08-05", "CPIN", vol_ratio=2.5)

        resp = c.get("/api/v1/candidates/screening?date=2026-08-05")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["date"] == "2026-08-05"
        assert data["count"] == 1
        assert data["results"][0]["ticker"] == "CPIN"

    def test_empty_list_not_404(self, client):
        resp = client.get("/api/v1/candidates/screening?date=2020-01-01")
        assert resp.status_code == 200
        assert resp.get_json()["data"]["results"] == []


class TestCandidatesReversalWatchlist:
    def test_explicit_date_runs_fresh_scan(self, env):
        c, db = env
        conn = sqlite3.connect(db)
        conn.executemany("INSERT INTO daily_screen (date, ticker, close, delta) VALUES (?,?,?,?)",
                         [("2026-06-08", "BRPT", 1390, -506_000_000),
                          ("2026-06-09", "BRPT", 1580, +567_000_000)])
        conn.executemany("INSERT INTO stockbit_flow VALUES (?,?,?,?,?)",
                         [("BRPT", "2026-06-09", "ACCUMULATION", "BULLISH", 79_000_000_000)])
        conn.executemany("INSERT INTO idx_tickers VALUES (?,?,?,?)", [("BRPT", 1, 0, 1)])
        conn.executemany("INSERT INTO ohlcv VALUES (?,?,?,?,?)",
                         [("BRPT", "2026-05-12", 2310, 1375, 2000),
                          ("BRPT", "2026-06-09", 1600, 1375, 1580)])
        conn.commit()
        conn.close()

        resp = c.get("/api/v1/candidates/reversal-watchlist?date=2026-06-09")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["scan_date"] == "2026-06-09"
        assert [r["ticker"] for r in data["results"]] == ["BRPT"]
        assert data["long"] == 1 and data["short"] == 0

    def test_no_data_returns_empty_not_error(self, client):
        resp = client.get("/api/v1/candidates/reversal-watchlist")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["results"] == [] and data["scan_date"] is None


class TestCandidatesPremoverWatchlist:
    def test_returns_watchlist_entries(self, env):
        c, db = env
        _seed_premover(db, "GOTO", score=80)

        resp = c.get("/api/v1/candidates/premover-watchlist")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["count"] == 1
        assert data["watchlist"][0]["ticker"] == "GOTO"

    def test_min_score_filters(self, env):
        c, db = env
        _seed_premover(db, "GOTO", score=30)

        resp = c.get("/api/v1/candidates/premover-watchlist?min_score=50")
        assert resp.get_json()["data"]["count"] == 0

    def test_empty_list_not_404(self, client):
        resp = client.get("/api/v1/candidates/premover-watchlist")
        assert resp.status_code == 200
        assert resp.get_json()["data"]["watchlist"] == []


class TestNoPresentationFormatting:
    def test_response_has_no_html_or_console_output(self, env):
        c, db = env
        _seed_universe(db, "2026-08-05", "CPIN")
        body = c.get("/api/v1/candidates").get_data(as_text=True)
        assert "<b>" not in body and "\x1b[" not in body
