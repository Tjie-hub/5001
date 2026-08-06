"""Wiring checks for the Platform/Integration API (Production Engine Phase
2, Workstream 2D): routes registered on the real app, VIEWER-classified,
documented in the OpenAPI spec. Mirrors tests/test_v1_health_wiring.py.
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


def test_platform_routes_present_in_real_app(make_client):
    c = make_client
    assert c.get("/api/v1/version").status_code == 200
    assert c.get("/api/v1/capabilities").status_code == 200
    assert c.get("/api/v1/resources").status_code == 200


def test_platform_routes_classified_viewer():
    from security.auth import VIEWER
    from security.route_policy import required_level
    assert required_level("/api/v1/version", "GET") == VIEWER
    assert required_level("/api/v1/capabilities", "GET") == VIEWER
    assert required_level("/api/v1/resources", "GET") == VIEWER


def test_platform_endpoints_documented_in_openapi(make_client):
    paths = make_client.get("/api/v1/openapi.json").get_json()["data"]["paths"]
    for p in ("/api/v1/version", "/api/v1/capabilities", "/api/v1/resources"):
        assert p in paths, f"missing from openapi spec: {p}"
        assert "get" in paths[p]


def test_resource_catalog_reflects_the_real_registered_app(make_client):
    data = make_client.get("/api/v1/resources").get_json()["data"]
    names = {g["name"] for g in data["resources"]}
    assert {"scheduler", "watchlists", "candidates", "reports", "snapshots"} <= names
