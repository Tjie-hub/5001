"""Regression tests: /api/v1/* authentication/authorization denials use the
standard API v1 envelope (Production Engine Phase 2, Workstream A.5).

Follows tests/security/test_middleware.py's fixture pattern (temp DB + real
app reload per AUTH_MODE). The 403 case needs a v1 route that requires more
than VIEWER, which doesn't exist yet -- POLICY is monkeypatched to elevate
one existing v1 rule's required level for the duration of that one test
only; the shipped classification is untouched (route_policy.POLICY is a
live, session-wide dict, so monkeypatch.setitem's auto-revert is what keeps
this from leaking into other tests).
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

    def _make(mode="enforce"):
        monkeypatch.setenv("AUTH_MODE", mode)
        import app as app_module
        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        return app_module.app.test_client()
    return _make


def _assert_v1_error_envelope(resp, expected_status, expected_code):
    assert resp.status_code == expected_status
    data = resp.get_json()
    assert data["ok"] is False
    assert data["error"]["code"] == expected_code
    assert "message" in data["error"]
    assert "details" in data["error"]
    assert data["meta"]["api_version"] == "v1"
    assert "request_id" in data["meta"]
    assert "timestamp" in data["meta"]


class TestUnauthorizedV1:
    def test_no_token_returns_v1_envelope_401(self, make_client):
        c = make_client("enforce")
        resp = c.get("/api/v1/status/summary")
        _assert_v1_error_envelope(resp, 401, "UNAUTHORIZED")

    def test_bad_token_returns_v1_envelope_401(self, make_client):
        c = make_client("enforce")
        resp = c.get("/api/v1/status/summary",
                      headers={"Authorization": "Bearer not-a-real-token"})
        _assert_v1_error_envelope(resp, 401, "UNAUTHORIZED")


class TestForbiddenV1:
    def test_insufficient_role_returns_v1_envelope_403(self, make_client, monkeypatch):
        import security.route_policy as route_policy
        from security.auth import ADMIN
        monkeypatch.setitem(route_policy.POLICY, "/api/v1/status/summary", ADMIN)

        c = make_client("enforce")
        resp = c.get("/api/v1/status/summary",
                      headers={"Authorization": f"Bearer {VIEW_TOK}"})
        _assert_v1_error_envelope(resp, 403, "FORBIDDEN")


class TestAuthorizedV1:
    def test_sufficient_role_passes_through_unaffected(self, make_client):
        c = make_client("enforce")
        resp = c.get("/api/v1/status/summary",
                      headers={"Authorization": f"Bearer {VIEW_TOK}"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert data["meta"]["api_version"] == "v1"


class TestLegacyRoutesUnaffected:
    def test_legacy_denial_shape_unchanged(self, make_client):
        """Non-API-v1 routes must keep the pre-existing {"error", "required"}
        shape -- this task changes /api/v1/* serialization only."""
        c = make_client("enforce")
        resp = c.get("/api/signals/today")
        assert resp.status_code == 401
        data = resp.get_json()
        assert data == {"error": "unauthorized", "required": "viewer"}
        assert "ok" not in data

    def test_legacy_forbidden_shape_unchanged(self, make_client):
        # /api/scheduler/run is ADMIN-classified (2026-08-19 incident) --
        # still exercises the same 403 shape, just a different required level.
        c = make_client("enforce")
        resp = c.post("/api/scheduler/run",
                       headers={"Authorization": f"Bearer {VIEW_TOK}"})
        assert resp.status_code == 403
        data = resp.get_json()
        assert data == {"error": "forbidden", "required": "admin"}
        assert "ok" not in data

    def test_html_route_denial_shape_unchanged(self, make_client):
        c = make_client("enforce")
        resp = c.get("/dashboard")
        assert resp.status_code == 401
        data = resp.get_json()
        assert data == {"error": "unauthorized", "required": "viewer"}
