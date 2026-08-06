"""Workstream 2B freeze guard (Production Engine Phase 2). Asserts every
Operational API endpoint built across 2B-1 (scheduler), 2B-2 (metrics),
2B-3 (config), and 2B-4 (health) shares one consistent contract: registered
on the real app, VIEWER-classified, documented in the OpenAPI spec, and
returns the standard envelope with full v1 meta. This is the freeze
checkpoint itself -- if a future change to any of these endpoints breaks
this file, it has broken the frozen Workstream 2B contract.
"""
import importlib
import sqlite3

import pytest

OPERATIONAL_GET_ENDPOINTS = [
    "/api/v1/scheduler",
    "/api/v1/scheduler/jobs",
    "/api/v1/metrics",
    "/api/v1/metrics/jobs",
    "/api/v1/metrics/engine",
    "/api/v1/config",
    "/api/v1/config/runtime",
    "/api/v1/health",
]

OPERATIONAL_POLICY_RULES = OPERATIONAL_GET_ENDPOINTS + ["/api/v1/scheduler/jobs/<job_id>"]

OPENAPI_PATH_KEYS = OPERATIONAL_GET_ENDPOINTS + ["/api/v1/scheduler/jobs/{job_id}"]


@pytest.fixture()
def make_client(tmp_path, monkeypatch):
    db = tmp_path / "t.db"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE scheduled_signals (scan_time TEXT, signal_direction TEXT)")
    conn.execute("CREATE TABLE paper_trades (ticker TEXT, status TEXT)")
    conn.execute("CREATE TABLE agent_decisions (scan_time TEXT)")
    conn.execute("CREATE TABLE ohlcv (ticker TEXT, date TEXT)")
    conn.execute("CREATE TABLE market_risk_log (score REAL, created_at TIMESTAMP)")
    conn.execute("CREATE TABLE daily_screen (date TEXT, ticker TEXT, vpin REAL)")
    conn.commit()
    conn.close()
    monkeypatch.setenv("DB_PATH", str(db))
    monkeypatch.setenv("AUTH_MODE", "off")

    import app as app_module
    importlib.reload(app_module)
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


class TestEveryOperationalEndpointRespondsWithStandardEnvelope:
    def test_200_ok_true_and_full_meta(self, make_client):
        for path in OPERATIONAL_GET_ENDPOINTS:
            resp = make_client.get(path)
            assert resp.status_code == 200, f"{path} -> {resp.status_code}"
            body = resp.get_json()
            assert body["ok"] is True, f"{path}: ok != True"
            assert "data" in body, f"{path}: missing data"
            assert body["meta"]["api_version"] == "v1", f"{path}: bad api_version"
            assert "request_id" in body["meta"], f"{path}: missing request_id"
            assert "timestamp" in body["meta"], f"{path}: missing timestamp"


class TestEveryOperationalRouteClassifiedViewer:
    def test_all_viewer(self):
        from security.auth import VIEWER
        from security.route_policy import required_level
        for rule in OPERATIONAL_POLICY_RULES:
            assert required_level(rule, "GET") == VIEWER, f"{rule} is not VIEWER"


class TestEveryOperationalEndpointDocumented:
    def test_all_present_in_openapi_with_get(self, make_client):
        paths = make_client.get("/api/v1/openapi.json").get_json()["data"]["paths"]
        for key in OPENAPI_PATH_KEYS:
            assert key in paths, f"{key} missing from openapi spec"
            assert "get" in paths[key], f"{key} missing GET in openapi spec"


class TestErrorHandlingConsistentAcrossOperationalPrefix:
    def test_unmatched_operational_style_path_returns_v1_error_envelope(self, make_client):
        resp = make_client.get("/api/v1/scheduler/does-not-exist-xyz")
        assert resp.status_code == 404
        body = resp.get_json()
        assert body["ok"] is False
        assert body["error"]["code"] == "NOT_FOUND"
        assert body["meta"]["api_version"] == "v1"
