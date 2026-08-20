"""Phase 2 freeze guard (Production Engine). The capstone regression test
spanning every /api/v1 endpoint built across Workstream A / Phase 2A (API
Foundation), Workstream 2B (Operational APIs), Workstream 2C (Business
APIs), and Workstream 2D (Integration APIs) as one set: registered on the
real app, correctly authorized, documented in the OpenAPI spec, and
returning the standard envelope with full v1 request metadata.

This supersedes nothing -- tests/test_v1_operational_apis_freeze.py (2B)
and tests/test_v1_business_apis_freeze.py (2C) stay as their own
per-workstream regression guards. This file is the whole-surface view: if
Phase 2's API contract is ever broken, this is the file that catches it.

Post-freeze addition (2026-08-19, Production Panel fix): /api/v1/registry/
status was added after the 2026-08-06 freeze date to back the Decision
Center Executive Summary (routes/v1/registry.py) -- deliberately extending
this inventory rather than treating the freeze as closed to new read-only
endpoints, same pattern as any future v1 addition should follow.

Post-freeze addition (2026-08-20, Production OS Slice 4): /api/v1/market/
summary was added to back the Market Workspace's Executive Market Summary
region (routes/v1/market.py), wrapping the pre-existing
engine.dashboard.get_risk_dashboard() aggregator -- same pattern as the
registry/status addition above.
"""
import importlib
import sqlite3

import pytest

from security.auth import PUBLIC, VIEWER

# (path, required auth level) for every endpoint on api_v1_bp, as of the
# Phase 2 freeze (2026-08-06). PUBLIC entries: none currently -- every v1
# endpoint is VIEWER, including /api/v1/openapi.json (Task 1 decision:
# not PUBLIC, unlike /health).
API_V1_ENDPOINTS = [
    ("/api/v1/", VIEWER),
    ("/api/v1/openapi.json", VIEWER),
    ("/api/v1/version", VIEWER),
    ("/api/v1/capabilities", VIEWER),
    ("/api/v1/resources", VIEWER),
    ("/api/v1/status/jobs/running", VIEWER),
    ("/api/v1/status/jobs/latest", VIEWER),
    ("/api/v1/status/jobs/failed", VIEWER),
    ("/api/v1/status/jobs/history", VIEWER),
    ("/api/v1/status/summary", VIEWER),
    ("/api/v1/scheduler", VIEWER),
    ("/api/v1/scheduler/jobs", VIEWER),
    ("/api/v1/scheduler/jobs/<job_id>", VIEWER),
    ("/api/v1/metrics", VIEWER),
    ("/api/v1/metrics/jobs", VIEWER),
    ("/api/v1/metrics/engine", VIEWER),
    ("/api/v1/config", VIEWER),
    ("/api/v1/config/runtime", VIEWER),
    ("/api/v1/health", VIEWER),
    ("/api/v1/watchlists/current", VIEWER),
    ("/api/v1/watchlists/history", VIEWER),
    ("/api/v1/watchlists/<date_str>", VIEWER),
    ("/api/v1/watchlists/diff", VIEWER),
    ("/api/v1/watchlists/persistent", VIEWER),
    ("/api/v1/snapshots", VIEWER),
    ("/api/v1/snapshots/<date_str>", VIEWER),
    ("/api/v1/reports", VIEWER),
    ("/api/v1/reports/<date_str>", VIEWER),
    ("/api/v1/candidates", VIEWER),
    ("/api/v1/candidates/<date_str>", VIEWER),
    ("/api/v1/candidates/screening", VIEWER),
    ("/api/v1/candidates/reversal-watchlist", VIEWER),
    ("/api/v1/candidates/premover-watchlist", VIEWER),
    ("/api/v1/registry/status", VIEWER),
    ("/api/v1/market/summary", VIEWER),
]

# GET-able paths only (excludes dynamic <param> rules, which aren't
# real HTTP-callable without a concrete value) for the live-request checks.
CONCRETE_GET_ENDPOINTS = [p for p, _ in API_V1_ENDPOINTS if "<" not in p]

# OpenAPI uses {param} templating, not Flask's <param>.
OPENAPI_PATH_KEYS = [
    p.replace("<date_str>", "{date}").replace("<job_id>", "{job_id}")
    for p, _ in API_V1_ENDPOINTS
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


class TestEveryV1RouteIsRegisteredExactlyOnce:
    def test_url_map_matches_the_known_inventory(self, make_client):
        rules = {
            r.rule for r in make_client.application.url_map.iter_rules()
            if r.rule.startswith("/api/v1")
        }
        known = {p for p, _ in API_V1_ENDPOINTS}
        assert rules == known, (
            f"drift between the real app and this freeze file's inventory -- "
            f"only in app: {rules - known}, only in inventory: {known - rules}"
        )


class TestEveryV1EndpointUsesTheStandardEnvelope:
    def test_success_or_structured_error_with_full_meta(self, make_client):
        for path in CONCRETE_GET_ENDPOINTS:
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


class TestEveryV1RouteHasTheExpectedAuthorization:
    def test_all_match_the_known_inventory(self):
        from security.route_policy import required_level
        for path, expected in API_V1_ENDPOINTS:
            assert required_level(path, "GET") == expected, f"{path} auth mismatch"

    def test_no_v1_route_is_public(self):
        """Every v1 endpoint requires at least a VIEWER credential (in
        enforce mode) -- unlike legacy /health, nothing under /api/v1 is
        PUBLIC. If this ever changes it must be a deliberate decision, not
        a classification slip caught only by the fail-closed default."""
        assert all(level != PUBLIC for _, level in API_V1_ENDPOINTS)


class TestEveryV1EndpointDocumented:
    def test_all_present_in_openapi_with_get(self, make_client):
        paths = make_client.get("/api/v1/openapi.json").get_json()["data"]["paths"]
        for key in OPENAPI_PATH_KEYS:
            assert key in paths, f"{key} missing from openapi spec"
            assert "get" in paths[key], f"{key} missing GET in openapi spec"

    def test_openapi_spec_has_no_stale_or_missing_entries(self, make_client):
        paths = set(make_client.get("/api/v1/openapi.json").get_json()["data"]["paths"])
        assert paths == set(OPENAPI_PATH_KEYS), (
            f"openapi.py._PATHS drifted from the real inventory -- "
            f"only in spec: {paths - set(OPENAPI_PATH_KEYS)}, "
            f"only in inventory: {set(OPENAPI_PATH_KEYS) - paths}"
        )


class TestErrorHandlingConsistentAcrossTheWholeV1Prefix:
    def test_unmatched_v1_path_returns_the_v1_error_envelope(self, make_client):
        resp = make_client.get("/api/v1/this-resource-does-not-exist")
        assert resp.status_code == 404
        body = resp.get_json()
        assert body["ok"] is False
        assert body["error"]["code"] == "NOT_FOUND"
        assert body["meta"]["api_version"] == "v1"
