"""Workstream 2C freeze guard (Production Engine Phase 2, Business APIs).
Asserts every Business API endpoint built across 2C-1 (watchlists), 2C-2
(snapshots), 2C-3 (reports), and 2C-4 (candidates) shares one consistent
contract: registered on the real app, VIEWER-classified, documented in the
OpenAPI spec, and returns the standard envelope (success or error shape)
with full v1 meta -- regardless of whether that particular call happens to
return 200 or a 404 for missing data, since both are equally part of the
frozen contract. Mirrors tests/test_v1_operational_apis_freeze.py's role
for Workstream 2B. If a future change to any endpoint below breaks this
file, it has broken the frozen Workstream 2C contract.
"""
import importlib
import sqlite3

import pytest

BUSINESS_GET_ENDPOINTS = [
    "/api/v1/watchlists/current",
    "/api/v1/watchlists/history",
    "/api/v1/watchlists/diff",
    "/api/v1/watchlists/persistent",
    "/api/v1/snapshots",
    "/api/v1/reports",
    "/api/v1/candidates",
    "/api/v1/candidates/screening",
    "/api/v1/candidates/reversal-watchlist",
    "/api/v1/candidates/premover-watchlist",
]

BUSINESS_POLICY_RULES = BUSINESS_GET_ENDPOINTS + [
    "/api/v1/watchlists/<date_str>",
    "/api/v1/snapshots/<date_str>",
    "/api/v1/reports/<date_str>",
    "/api/v1/candidates/<date_str>",
]

OPENAPI_PATH_KEYS = BUSINESS_GET_ENDPOINTS + [
    "/api/v1/watchlists/{date}",
    "/api/v1/snapshots/{date}",
    "/api/v1/reports/{date}",
    "/api/v1/candidates/{date}",
]


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

    from forward_testing.storage.db import init_ft_tables
    init_ft_tables(str(db))

    return app_module.app.test_client()


class TestEveryBusinessEndpointUsesTheStandardEnvelope:
    def test_success_or_structured_error_with_full_meta(self, make_client):
        # /watchlists/diff requires ?date= -- 400 MISSING_DATE without it,
        # same envelope family as a 404, just a different expected status.
        for path in BUSINESS_GET_ENDPOINTS:
            resp = make_client.get(path)
            assert resp.status_code in (200, 400, 404), f"{path} -> {resp.status_code}"
            body = resp.get_json()
            assert "meta" in body, f"{path}: missing meta"
            assert body["meta"]["api_version"] == "v1", f"{path}: bad api_version"
            assert "request_id" in body["meta"], f"{path}: missing request_id"
            assert "timestamp" in body["meta"], f"{path}: missing timestamp"
            if resp.status_code == 200:
                assert body["ok"] is True, f"{path}: 200 but ok != True"
                assert "data" in body, f"{path}: 200 but missing data"
            else:
                assert body["ok"] is False, f"{path}: {resp.status_code} but ok != False"
                assert "code" in body["error"], f"{path}: missing error.code"


class TestEveryBusinessRouteClassifiedViewer:
    def test_all_viewer(self):
        from security.auth import VIEWER
        from security.route_policy import required_level
        for rule in BUSINESS_POLICY_RULES:
            assert required_level(rule, "GET") == VIEWER, f"{rule} is not VIEWER"


class TestEveryBusinessEndpointDocumented:
    def test_all_present_in_openapi_with_get(self, make_client):
        paths = make_client.get("/api/v1/openapi.json").get_json()["data"]["paths"]
        for key in OPENAPI_PATH_KEYS:
            assert key in paths, f"{key} missing from openapi spec"
            assert "get" in paths[key], f"{key} missing GET in openapi spec"


class TestErrorHandlingConsistentAcrossBusinessPrefixes:
    def test_unmatched_business_style_paths_return_v1_error_envelope(self, make_client):
        for prefix in ("watchlists", "snapshots", "reports", "candidates"):
            resp = make_client.get(f"/api/v1/{prefix}/does-not-exist-xyz/nested")
            assert resp.status_code == 404, prefix
            body = resp.get_json()
            assert body["ok"] is False
            assert body["error"]["code"] == "NOT_FOUND"
            assert body["meta"]["api_version"] == "v1"
