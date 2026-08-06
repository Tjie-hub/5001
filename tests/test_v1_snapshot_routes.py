"""Tests for routes/v1/snapshots.py -- /api/v1/snapshots, /snapshots/{date}
(Production Engine Phase 2, Workstream 2C Task 2C-2).

Metadata/inventory layer across both snapshot-producing tables
(watchlist_snapshot via engine.trade_plan, candidate_watchlist_snapshot via
engine.watchlist_report) -- seeded via the real writer functions, not raw
INSERTs.
"""
import sqlite3

import pytest

from routes.v1 import api_v1_bp


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


def _ranked(*tickers):
    return [{"ticker": t, "confidence": 0.6, "conviction": 50.0,
             "confluence": 1, "sources": ["R"]} for t in tickers]


def _cands(*tickers):
    return [{"ticker": t, "sources": ["R"], "conviction": 50.0,
             "vol_ratio": 0.0, "reason": ""} for t in tickers]


def _seed_watchlist(db, date_str, strategy, *tickers):
    from engine.trade_plan import record_snapshot
    conn = sqlite3.connect(db)
    record_snapshot(conn, date_str, strategy, _ranked(*tickers))
    conn.close()


def _seed_candidates(db, date_str, *tickers):
    from engine.watchlist_report import record_snapshot
    conn = sqlite3.connect(db)
    record_snapshot(conn, date_str, _cands(*tickers))
    conn.close()


class TestSnapshotsIndex:
    def test_combines_both_sources(self, env):
        c, db = env
        _seed_watchlist(db, "2026-08-05", "eod", "CPIN", "AKRA")
        _seed_candidates(db, "2026-08-05", "CPIN", "AKRA", "TLKM")

        resp = c.get("/api/v1/snapshots")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["count"] == 2
        by_type = {s["type"]: s for s in data["snapshots"]}
        assert by_type["watchlist"] == {"type": "watchlist", "strategy": "eod",
                                        "date": "2026-08-05", "ticker_count": 2}
        assert by_type["candidate_universe"] == {"type": "candidate_universe",
                                                  "strategy": None, "date": "2026-08-05",
                                                  "ticker_count": 3}

    def test_empty_list_not_404(self, client):
        resp = client.get("/api/v1/snapshots")
        assert resp.status_code == 200
        assert resp.get_json()["data"] == {"snapshots": [], "count": 0}

    def test_filter_by_type(self, env):
        c, db = env
        _seed_watchlist(db, "2026-08-05", "eod", "CPIN")
        _seed_candidates(db, "2026-08-05", "CPIN")

        resp = c.get("/api/v1/snapshots?type=watchlist")
        data = resp.get_json()["data"]
        assert data["count"] == 1
        assert data["snapshots"][0]["type"] == "watchlist"

    def test_filter_by_strategy(self, env):
        c, db = env
        _seed_watchlist(db, "2026-08-05", "eod", "CPIN")
        _seed_watchlist(db, "2026-08-05", "premarket", "AKRA")

        resp = c.get("/api/v1/snapshots?strategy=premarket")
        data = resp.get_json()["data"]
        assert data["count"] == 1
        assert data["snapshots"][0]["strategy"] == "premarket"

    def test_newest_first_across_sources(self, env):
        c, db = env
        _seed_watchlist(db, "2026-08-01", "eod", "OLD")
        _seed_candidates(db, "2026-08-05", "NEW")

        resp = c.get("/api/v1/snapshots")
        dates = [s["date"] for s in resp.get_json()["data"]["snapshots"]]
        assert dates == ["2026-08-05", "2026-08-01"]


class TestSnapshotsByDate:
    def test_returns_snapshots_for_that_date_only(self, env):
        c, db = env
        _seed_watchlist(db, "2026-08-01", "eod", "OLD")
        _seed_watchlist(db, "2026-08-05", "eod", "CPIN")
        _seed_candidates(db, "2026-08-05", "CPIN", "AKRA")

        resp = c.get("/api/v1/snapshots/2026-08-05")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["date"] == "2026-08-05"
        assert data["count"] == 2

    def test_404_when_no_snapshot_of_any_type_that_date(self, env):
        c, db = env
        _seed_watchlist(db, "2026-08-01", "eod", "OLD")

        resp = c.get("/api/v1/snapshots/2020-01-01")
        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "NO_SNAPSHOT_DATA"


class TestNoPresentationFormatting:
    def test_response_has_no_html_or_emoji_markup(self, env):
        c, db = env
        _seed_watchlist(db, "2026-08-05", "eod", "CPIN")
        body = c.get("/api/v1/snapshots").get_data(as_text=True)
        assert "<b>" not in body and "📈" not in body
