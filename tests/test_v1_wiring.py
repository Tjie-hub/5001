"""End-to-end wiring: api_v1_bp registered on the real app, legacy
/api/status/* blueprint gone, and /api/v1/openapi.json's VIEWER gate enforced
through the real security middleware (Production Engine Phase 2, Workstream
A Task 1). Follows tests/security/test_middleware.py's fixture pattern.
"""
import importlib
import sqlite3

import pytest

VIEW_TOK = "viewer-token-0123456789abcdef"


@pytest.fixture()
def make_client(tmp_path, monkeypatch):
    db = tmp_path / "t.db"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE scheduled_signals (scan_time TEXT, signal_direction TEXT)")
    conn.execute("CREATE TABLE paper_trades (ticker TEXT, status TEXT)")
    conn.commit()
    conn.close()
    monkeypatch.setenv("DB_PATH", str(db))
    monkeypatch.setenv("AUTH_TOKEN_VIEWER", VIEW_TOK)

    def _make(mode="off"):
        monkeypatch.setenv("AUTH_MODE", mode)
        import app as app_module
        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        return app_module.app.test_client()
    return _make


class TestBlueprintRegistered:
    def test_v1_routes_present(self, make_client):
        c = make_client()
        assert c.get("/api/v1/").status_code == 200
        assert c.get("/api/v1/status/summary").status_code == 200
        assert c.get("/api/v1/openapi.json").status_code == 200

    def test_legacy_status_routes_removed(self, make_client):
        c = make_client()
        for legacy in (
            "/api/status/jobs/running", "/api/status/jobs/latest",
            "/api/status/jobs/failed", "/api/status/jobs/history",
            "/api/status/summary",
        ):
            assert c.get(legacy).status_code == 404, legacy


class TestRoutePolicyClassification:
    def test_v1_routes_classified_viewer(self):
        from security.auth import VIEWER
        from security.route_policy import required_level
        assert required_level("/api/v1/", "GET") == VIEWER
        assert required_level("/api/v1/openapi.json", "GET") == VIEWER
        assert required_level("/api/v1/status/jobs/running", "GET") == VIEWER
        assert required_level("/api/v1/status/jobs/latest", "GET") == VIEWER
        assert required_level("/api/v1/status/jobs/failed", "GET") == VIEWER
        assert required_level("/api/v1/status/jobs/history", "GET") == VIEWER
        assert required_level("/api/v1/status/summary", "GET") == VIEWER

    def test_legacy_status_entries_removed_from_policy(self):
        from security.route_policy import POLICY
        for legacy in (
            "/api/status/jobs/running", "/api/status/jobs/latest",
            "/api/status/jobs/failed", "/api/status/jobs/history",
            "/api/status/summary",
        ):
            assert legacy not in POLICY


class TestOpenApiAuthEnforced:
    def test_anonymous_blocked_in_enforce_mode(self, make_client):
        c = make_client("enforce")
        assert c.get("/api/v1/openapi.json").status_code == 401

    def test_viewer_token_allowed_in_enforce_mode(self, make_client):
        c = make_client("enforce")
        h = {"Authorization": f"Bearer {VIEW_TOK}"}
        resp = c.get("/api/v1/openapi.json", headers=h)
        assert resp.status_code == 200
        assert resp.get_json()["ok"] is True

    def test_shadow_mode_never_blocks(self, make_client):
        c = make_client("shadow")
        assert c.get("/api/v1/openapi.json").status_code == 200
