"""Tests for GET /api/v1/openapi.json -- spec content and shape only.
Authorization (VIEWER-gated, per the approved design) is exercised where the
blueprint is wired into the real app with the security middleware active
(tests/test_v1_wiring.py), since a standalone blueprint app here has no auth
middleware to test against.
"""
import pytest
from flask import Flask

from routes.v1 import api_v1_bp


@pytest.fixture
def client():
    app = Flask(__name__)
    app.register_blueprint(api_v1_bp)
    return app.test_client()


class TestOpenApiSpec:
    def test_returns_spec_via_standard_envelope(self, client):
        resp = client.get("/api/v1/openapi.json")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert data["meta"]["api_version"] == "v1"

        spec = data["data"]
        assert spec["openapi"].startswith("3.")
        assert spec["info"]["version"] == "v1"
        assert "/api/v1/" in spec["paths"]

    def test_spec_documents_the_migrated_status_endpoints(self, client):
        resp = client.get("/api/v1/openapi.json")
        paths = resp.get_json()["data"]["paths"]
        for p in (
            "/api/v1/status/jobs/running",
            "/api/v1/status/jobs/latest",
            "/api/v1/status/jobs/failed",
            "/api/v1/status/jobs/history",
            "/api/v1/status/summary",
        ):
            assert p in paths, f"missing from openapi spec: {p}"
            assert "get" in paths[p]
