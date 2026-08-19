"""Wiring checks for GET /api/v1/registry/status: registered on the real
app, VIEWER-classified, documented in the OpenAPI spec, resource catalog
picks it up automatically. Mirrors tests/test_v1_platform_wiring.py.
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


def test_registry_status_present_in_real_app(make_client):
    resp = make_client.get("/api/v1/registry/status")
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert "approved" in data and "shadow" in data


def test_registry_status_classified_viewer():
    from security.auth import VIEWER
    from security.route_policy import required_level
    assert required_level("/api/v1/registry/status", "GET") == VIEWER


def test_registry_status_documented_in_openapi(make_client):
    paths = make_client.get("/api/v1/openapi.json").get_json()["data"]["paths"]
    assert "/api/v1/registry/status" in paths
    assert "get" in paths["/api/v1/registry/status"]


def test_resource_catalog_picks_up_registry_group(make_client):
    data = make_client.get("/api/v1/resources").get_json()["data"]
    names = {g["name"] for g in data["resources"]}
    assert "registry" in names
