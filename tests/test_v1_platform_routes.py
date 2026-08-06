"""Tests for routes/v1/platform.py -- /api/v1/version, /api/v1/capabilities,
/api/v1/resources (Production Engine Phase 2, Workstream 2D). The existing
GET /api/v1/ root (Workstream A Task 1) is untouched -- not covered here.
"""
import pytest
from flask import Flask

from routes.v1 import api_v1_bp


@pytest.fixture
def client():
    app = Flask(__name__)
    app.register_blueprint(api_v1_bp)
    return app.test_client()


class TestVersionEndpoint:
    def test_returns_version_info_via_envelope(self, client):
        resp = client.get("/api/v1/version")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["api_version"] == "v1"
        assert data["openapi_url"] == "/api/v1/openapi.json"
        assert "release_version" in data


class TestCapabilitiesEndpoint:
    def test_returns_capabilities_via_envelope(self, client, monkeypatch):
        monkeypatch.setenv("AUTH_MODE", "shadow")

        resp = client.get("/api/v1/capabilities")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["auth_mode"] == "shadow"
        assert "resource_groups" in data
        assert "scheduler" in data["resource_groups"]


class TestResourcesEndpoint:
    def test_returns_resource_catalog_via_envelope(self, client):
        resp = client.get("/api/v1/resources")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert "resources" in data
        names = {g["name"] for g in data["resources"]}
        assert "watchlists" in names
        assert "candidates" in names


class TestExistingRootUntouched:
    def test_root_still_returns_original_shape(self, client):
        resp = client.get("/api/v1/")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data == {"name": "idx-walkforward-5001 API", "version": "v1", "status": "ok"}
