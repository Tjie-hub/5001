"""Tests for routes/v1/watchlists.py -- /api/v1/watchlists/* (Production
Engine Phase 2, Workstream 2C Task 2C-1).

Seeds via the real writer functions (engine.trade_plan.record_snapshot,
engine.persistent_watchlist.update_watchlist) rather than raw INSERTs, so
these tests exercise the actual persisted shape those functions produce.
"""
import sqlite3

import pytest

from routes.v1 import api_v1_bp


def _ranked(*rows):
    """rows: (ticker, confidence, conviction, sources)"""
    return [{"ticker": t, "confidence": conf, "conviction": conv,
             "confluence": len(src), "sources": src}
            for t, conf, conv, src in rows]


@pytest.fixture
def env(tmp_path, monkeypatch):
    db = tmp_path / "wf.db"
    sqlite3.connect(str(db)).close()

    import config
    monkeypatch.setattr(config, "DB_PATH", str(db))

    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(api_v1_bp)
    return app.test_client(), str(db)


@pytest.fixture
def client(env):
    c, _ = env
    return c


def _seed_snapshot(db, date_str, strategy, *rows):
    from engine.trade_plan import record_snapshot
    conn = sqlite3.connect(db)
    record_snapshot(conn, date_str, strategy, _ranked(*rows))
    conn.close()


def _seed_persistent(db, date_str, tickers):
    from engine.persistent_watchlist import update_watchlist
    conn = sqlite3.connect(db)
    update_watchlist(conn, date_str, tickers)
    conn.close()


class TestCurrent:
    def test_returns_latest_snapshot(self, env):
        c, db = env
        _seed_snapshot(db, "2026-08-01", "eod", ("AKRA", 0.8, 40.0, ["R"]))
        _seed_snapshot(db, "2026-08-05", "eod", ("CPIN", 0.6, 78.1, ["R", "S"]))

        resp = c.get("/api/v1/watchlists/current")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["strategy"] == "eod"
        assert data["date"] == "2026-08-05"
        assert [r["ticker"] for r in data["watchlist"]] == ["CPIN"]

    def test_strategy_param_selects_premarket(self, env):
        c, db = env
        _seed_snapshot(db, "2026-08-05", "eod", ("CPIN", 0.6, 78.1, ["R"]))
        _seed_snapshot(db, "2026-08-05", "premarket", ("AKRA", 0.8, 40.0, ["R"]))

        resp = c.get("/api/v1/watchlists/current?strategy=premarket")
        data = resp.get_json()["data"]
        assert [r["ticker"] for r in data["watchlist"]] == ["AKRA"]

    def test_404_when_strategy_has_no_data(self, client):
        resp = client.get("/api/v1/watchlists/current")
        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "NO_WATCHLIST_DATA"


class TestHistory:
    def test_lists_dates_newest_first(self, env):
        c, db = env
        _seed_snapshot(db, "2026-08-01", "eod", ("AKRA", 0.8, 40.0, ["R"]))
        _seed_snapshot(db, "2026-08-05", "eod", ("CPIN", 0.6, 78.1, ["R"]))

        resp = c.get("/api/v1/watchlists/history")
        data = resp.get_json()["data"]
        assert data["strategy"] == "eod"
        assert data["dates"] == ["2026-08-05", "2026-08-01"]
        assert data["count"] == 2

    def test_empty_list_not_404(self, client):
        resp = client.get("/api/v1/watchlists/history")
        assert resp.status_code == 200
        assert resp.get_json()["data"] == {"strategy": "eod", "dates": [], "count": 0}


class TestByDate:
    def test_returns_that_dates_watchlist(self, env):
        c, db = env
        _seed_snapshot(db, "2026-08-01", "eod", ("AKRA", 0.8, 40.0, ["R"]))
        _seed_snapshot(db, "2026-08-05", "eod", ("CPIN", 0.6, 78.1, ["R"]))

        resp = c.get("/api/v1/watchlists/2026-08-01")
        data = resp.get_json()["data"]
        assert [r["ticker"] for r in data["watchlist"]] == ["AKRA"]

    def test_404_when_that_date_has_no_snapshot(self, env):
        c, db = env
        _seed_snapshot(db, "2026-08-01", "eod", ("AKRA", 0.8, 40.0, ["R"]))

        resp = c.get("/api/v1/watchlists/2020-01-01")
        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "NO_WATCHLIST_DATA"


class TestDiff:
    def test_diff_against_most_recent_prior(self, env):
        c, db = env
        _seed_snapshot(db, "2026-08-01", "eod", ("AKRA", 0.8, 40.0, ["R"]))
        _seed_snapshot(db, "2026-08-05", "eod", ("CPIN", 0.6, 78.1, ["R"]))

        resp = c.get("/api/v1/watchlists/diff?date=2026-08-05")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["diff"]["prior_date"] == "2026-08-01"
        assert data["diff"]["added"] == ["CPIN"]
        assert data["diff"]["removed"] == ["AKRA"]

    def test_diff_null_when_no_prior_snapshot(self, env):
        c, db = env
        _seed_snapshot(db, "2026-08-05", "eod", ("CPIN", 0.6, 78.1, ["R"]))

        resp = c.get("/api/v1/watchlists/diff?date=2026-08-05")
        assert resp.status_code == 200
        assert resp.get_json()["data"]["diff"] is None

    def test_400_when_date_missing(self, client):
        resp = client.get("/api/v1/watchlists/diff")
        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "MISSING_DATE"

    def test_404_when_date_itself_has_no_snapshot(self, env):
        c, db = env
        _seed_snapshot(db, "2026-08-01", "eod", ("AKRA", 0.8, 40.0, ["R"]))

        resp = c.get("/api/v1/watchlists/diff?date=2020-01-01")
        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "NO_WATCHLIST_DATA"


class TestPersistent:
    def test_defaults_to_active(self, env):
        c, db = env
        _seed_persistent(db, "2026-08-04", ["BBCA", "TLKM"])
        _seed_persistent(db, "2026-08-05", ["BBCA"])

        resp = c.get("/api/v1/watchlists/persistent")
        data = resp.get_json()["data"]
        assert [r["ticker"] for r in data["watchlist"]] == ["BBCA"]
        assert data["status"] == "active"
        assert data["count"] == 1

    def test_status_all(self, env):
        c, db = env
        _seed_persistent(db, "2026-08-04", ["BBCA", "TLKM"])
        _seed_persistent(db, "2026-08-05", ["BBCA"])

        resp = c.get("/api/v1/watchlists/persistent?status=all")
        tickers = {r["ticker"] for r in resp.get_json()["data"]["watchlist"]}
        assert tickers == {"BBCA", "TLKM"}

    def test_empty_list_not_404(self, client):
        resp = client.get("/api/v1/watchlists/persistent")
        assert resp.status_code == 200
        assert resp.get_json()["data"]["watchlist"] == []


class TestNoPresentationFormatting:
    def test_response_contains_no_html_or_emoji_markup(self, env):
        c, db = env
        _seed_snapshot(db, "2026-08-05", "eod", ("CPIN", 0.6, 78.1, ["R"]))
        body = c.get("/api/v1/watchlists/current").get_data(as_text=True)
        assert "<b>" not in body and "📈" not in body
