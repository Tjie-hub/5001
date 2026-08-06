"""Wiring checks for the health API (Production Engine Phase 2, Workstream
2B Task 2B-4): route registered on the real app, VIEWER-classified, and
documented in the OpenAPI spec. Mirrors tests/test_v1_config_wiring.py.
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


def test_health_route_present_in_real_app(make_client):
    assert make_client.get("/api/v1/health").status_code == 200


def test_health_route_classified_viewer():
    from security.auth import VIEWER
    from security.route_policy import required_level
    assert required_level("/api/v1/health", "GET") == VIEWER


def test_health_documented_in_openapi(make_client):
    paths = make_client.get("/api/v1/openapi.json").get_json()["data"]["paths"]
    assert "/api/v1/health" in paths
    assert "get" in paths["/api/v1/health"]
