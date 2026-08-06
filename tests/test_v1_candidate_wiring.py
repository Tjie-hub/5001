"""Wiring checks for the Candidate Universe API (Production Engine Phase 2,
Workstream 2C Task 2C-4): routes registered on the real app,
VIEWER-classified, documented in the OpenAPI spec, and -- the migration
behavior this task specifically changes -- the two legacy routes with no
active consumer are gone (404, not just unclassified), while
POST /api/premover/run (kept, out of scope) and the still-consumed
GET /api/screener/results (kept, active consumer) remain exactly as they
were.
"""
import importlib
import sqlite3

import pytest


@pytest.fixture()
def make_client(tmp_path, monkeypatch):
    db = tmp_path / "t.db"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE scheduled_signals (scan_time TEXT, signal_direction TEXT)")
    conn.execute("CREATE TABLE paper_trades (ticker TEXT, status TEXT)")
    conn.execute("CREATE TABLE daily_screen (date TEXT, ticker TEXT, vol_ratio REAL)")
    conn.commit()
    conn.close()
    monkeypatch.setenv("DB_PATH", str(db))
    monkeypatch.setenv("AUTH_MODE", "off")

    import app as app_module
    importlib.reload(app_module)
    app_module.app.config["TESTING"] = True

    import config
    monkeypatch.setattr(config, "DB_PATH", str(db))
    import screener.db as screener_db_mod
    monkeypatch.setattr(screener_db_mod, "DB_PATH", str(db))

    return app_module.app.test_client()


def test_candidate_routes_present_in_real_app(make_client):
    c = make_client
    assert c.get("/api/v1/candidates").status_code == 404  # no data yet, not 500
    assert c.get("/api/v1/candidates/screening").status_code == 200
    assert c.get("/api/v1/candidates/reversal-watchlist").status_code == 200
    assert c.get("/api/v1/candidates/premover-watchlist").status_code == 200


def test_candidate_routes_classified_viewer():
    from security.auth import VIEWER
    from security.route_policy import required_level
    assert required_level("/api/v1/candidates", "GET") == VIEWER
    assert required_level("/api/v1/candidates/<date_str>", "GET") == VIEWER
    assert required_level("/api/v1/candidates/screening", "GET") == VIEWER
    assert required_level("/api/v1/candidates/reversal-watchlist", "GET") == VIEWER
    assert required_level("/api/v1/candidates/premover-watchlist", "GET") == VIEWER


def test_candidate_endpoints_documented_in_openapi(make_client):
    paths = make_client.get("/api/v1/openapi.json").get_json()["data"]["paths"]
    for p in ("/api/v1/candidates", "/api/v1/candidates/{date}",
              "/api/v1/candidates/screening", "/api/v1/candidates/reversal-watchlist",
              "/api/v1/candidates/premover-watchlist"):
        assert p in paths, f"missing from openapi spec: {p}"
        assert "get" in paths[p]


class TestLegacyMigrationBehavior:
    def test_migrated_routes_are_gone(self, make_client):
        c = make_client
        assert c.get("/api/screener/reversal").status_code == 404
        assert c.get("/api/premover/watchlist").status_code == 404

    def test_migrated_routes_removed_from_policy(self):
        from security.route_policy import POLICY
        assert "/api/screener/reversal" not in POLICY
        assert "/api/premover/watchlist" not in POLICY

    def test_out_of_scope_write_route_untouched(self):
        from security.auth import OPERATOR
        from security.route_policy import required_level
        assert required_level("/api/premover/run", "POST") == OPERATOR

    def test_still_consumed_legacy_route_untouched(self, make_client):
        from security.auth import VIEWER
        from security.route_policy import required_level
        c = make_client
        assert c.get("/api/screener/results").status_code == 200
        assert required_level("/api/screener/results", "GET") == VIEWER
