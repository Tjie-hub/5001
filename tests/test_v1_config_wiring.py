"""Wiring checks for the config API (Production Engine Phase 2, Workstream
2B Task 2B-3): routes registered on the real app, VIEWER-classified,
documented in the OpenAPI spec, and -- the most important check here -- no
secret value from the real environment leaks through the real app+security
stack. Mirrors tests/test_v1_metrics_wiring.py.
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
    monkeypatch.setenv("TELEGRAM_TOKEN", "sekret-telegram-token-in-real-app")
    monkeypatch.setenv("FLASK_SECRET_KEY", "sekret-flask-key-in-real-app")

    import app as app_module
    importlib.reload(app_module)
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def test_config_routes_present_in_real_app(make_client):
    c = make_client
    assert c.get("/api/v1/config").status_code == 200
    assert c.get("/api/v1/config/runtime").status_code == 200


def test_config_routes_classified_viewer():
    from security.auth import VIEWER
    from security.route_policy import required_level
    assert required_level("/api/v1/config", "GET") == VIEWER
    assert required_level("/api/v1/config/runtime", "GET") == VIEWER


def test_config_endpoints_documented_in_openapi(make_client):
    c = make_client
    paths = c.get("/api/v1/openapi.json").get_json()["data"]["paths"]
    for p in ("/api/v1/config", "/api/v1/config/runtime"):
        assert p in paths, f"missing from openapi spec: {p}"
        assert "get" in paths[p]


def test_no_secrets_leak_through_the_real_app(make_client):
    c = make_client
    body = (c.get("/api/v1/config").get_data(as_text=True)
            + c.get("/api/v1/config/runtime").get_data(as_text=True))
    assert "sekret-telegram-token-in-real-app" not in body
    assert "sekret-flask-key-in-real-app" not in body
