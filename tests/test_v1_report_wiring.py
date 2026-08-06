"""Wiring checks for the Report API (Production Engine Phase 2, Workstream
2C Task 2C-3): routes registered on the real app, VIEWER-classified,
documented in the OpenAPI spec. Mirrors tests/test_v1_snapshot_wiring.py.
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

    import config
    monkeypatch.setattr(config, "DB_PATH", str(db))

    from forward_testing.storage.db import init_ft_tables
    init_ft_tables(str(db))

    return app_module.app.test_client()


def test_report_routes_present_in_real_app(make_client):
    c = make_client
    assert c.get("/api/v1/reports").status_code == 404  # no report ever ran, not 500
    assert c.get("/api/v1/reports/2026-08-05").status_code == 404


def test_report_routes_classified_viewer():
    from security.auth import VIEWER
    from security.route_policy import required_level
    assert required_level("/api/v1/reports", "GET") == VIEWER
    assert required_level("/api/v1/reports/<date_str>", "GET") == VIEWER


def test_report_endpoints_documented_in_openapi(make_client):
    paths = make_client.get("/api/v1/openapi.json").get_json()["data"]["paths"]
    for p in ("/api/v1/reports", "/api/v1/reports/{date}"):
        assert p in paths, f"missing from openapi spec: {p}"
        assert "get" in paths[p]
