"""Wiring checks for the scheduler API (Production Engine Phase 2, Workstream
2B Task 2B-1): routes registered on the real app, VIEWER-classified, and
documented in the OpenAPI spec. Mirrors tests/test_v1_wiring.py's pattern.
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
    conn.commit()
    conn.close()
    monkeypatch.setenv("DB_PATH", str(db))
    monkeypatch.setenv("AUTH_MODE", "off")

    import app as app_module
    importlib.reload(app_module)
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def test_scheduler_routes_present_in_real_app(make_client):
    c = make_client
    assert c.get("/api/v1/scheduler").status_code == 200
    assert c.get("/api/v1/scheduler/jobs").status_code == 200
    assert c.get("/api/v1/scheduler/jobs/no-such-job").status_code == 404


def test_scheduler_routes_classified_viewer():
    from security.auth import VIEWER
    from security.route_policy import required_level
    assert required_level("/api/v1/scheduler", "GET") == VIEWER
    assert required_level("/api/v1/scheduler/jobs", "GET") == VIEWER
    assert required_level("/api/v1/scheduler/jobs/<job_id>", "GET") == VIEWER


def test_scheduler_endpoints_documented_in_openapi(make_client):
    c = make_client
    paths = c.get("/api/v1/openapi.json").get_json()["data"]["paths"]
    for p in ("/api/v1/scheduler", "/api/v1/scheduler/jobs",
              "/api/v1/scheduler/jobs/{job_id}"):
        assert p in paths, f"missing from openapi spec: {p}"
        assert "get" in paths[p]
