"""Tests for GET /api/v1/ -- the API v1 root/metadata endpoint (Production
Engine Phase 2, Workstream A Task 1).
"""
import pytest
from flask import Flask

from routes.v1 import api_v1_bp


@pytest.fixture
def client():
    app = Flask(__name__)
    app.register_blueprint(api_v1_bp)
    return app.test_client()


class TestApiRoot:
    def test_returns_api_metadata_via_standard_envelope(self, client):
        resp = client.get("/api/v1/")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert data["data"]["name"]
        assert data["data"]["version"] == "v1"
        assert data["data"]["status"] == "ok"
        assert data["meta"]["api_version"] == "v1"

    def test_wrong_method_uses_the_v1_error_envelope(self, client):
        resp = client.post("/api/v1/")
        assert resp.status_code == 405
        data = resp.get_json()
        assert data["ok"] is False
        assert data["error"]["code"] == "METHOD_NOT_ALLOWED"
