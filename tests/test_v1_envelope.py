"""Tests for routes/v1/envelope.py -- the standard API v1 response envelope,
ApiError, and blueprint-level error handlers (Production Engine Phase 2,
Workstream A Task 1).

Uses a minimal standalone Flask app + a throwaway blueprint (registered
through routes.v1.envelope.register_error_handlers) so this file doesn't
depend on routes/v1/status.py or app.py's own request lifecycle -- except
where a test explicitly simulates app.py's before_request correlation-id
assignment.
"""
import re
import uuid

import pytest
from flask import Blueprint, Flask, g

from routes.v1.envelope import ApiError, err, ok, register_error_handlers

ISO8601_UTC = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?\+00:00$"
)


def _build_app():
    app = Flask(__name__)
    bp = Blueprint("t", __name__, url_prefix="/api/v1")
    register_error_handlers(bp)

    @bp.route("/ok")
    def ok_route():
        return ok({"hello": "world"})

    @bp.route("/err")
    def err_route():
        return err("SOMETHING_BAD", "it broke", details={"x": 1}, status=422)

    @bp.route("/raise-api-error")
    def raise_api_error():
        raise ApiError("BAD_LIMIT", 400, "limit must be positive", details={"limit": -5})

    @bp.route("/raise-generic-exception")
    def raise_generic_exception():
        raise RuntimeError("boom, should never leak")

    @bp.route("/only-get", methods=["GET"])
    def only_get():
        return ok({})

    app.register_blueprint(bp)
    return app


@pytest.fixture
def client():
    return _build_app().test_client()


class TestOkEnvelope:
    def test_shape(self, client):
        resp = client.get("/api/v1/ok")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert data["data"] == {"hello": "world"}
        assert data["meta"]["api_version"] == "v1"
        assert "request_id" in data["meta"]
        assert ISO8601_UTC.match(data["meta"]["timestamp"])

    def test_request_id_is_generated_when_absent(self, client):
        resp = client.get("/api/v1/ok")
        request_id = resp.get_json()["meta"]["request_id"]
        # must be a valid uuid4-shaped string when nothing was supplied upstream
        uuid.UUID(request_id)

    def test_request_id_reuses_existing_correlation_id(self):
        app = _build_app()

        @app.before_request
        def _fake_correlation():
            g.correlation_id = "fixed-correlation-id-123"

        resp = app.test_client().get("/api/v1/ok")
        assert resp.get_json()["meta"]["request_id"] == "fixed-correlation-id-123"


class TestErrEnvelope:
    def test_shape_and_status(self, client):
        resp = client.get("/api/v1/err")
        assert resp.status_code == 422
        data = resp.get_json()
        assert data["ok"] is False
        assert data["error"]["code"] == "SOMETHING_BAD"
        assert data["error"]["message"] == "it broke"
        assert data["error"]["details"] == {"x": 1}
        assert data["meta"]["api_version"] == "v1"


class TestApiErrorHandler:
    def test_api_error_becomes_error_envelope_with_its_status(self, client):
        resp = client.get("/api/v1/raise-api-error")
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["ok"] is False
        assert data["error"]["code"] == "BAD_LIMIT"
        assert data["error"]["message"] == "limit must be positive"
        assert data["error"]["details"] == {"limit": -5}


class TestFrameworkErrorHandlers:
    def test_404_on_unmatched_v1_route_is_enveloped(self, client):
        resp = client.get("/api/v1/does-not-exist")
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["ok"] is False
        assert data["error"]["code"] == "NOT_FOUND"
        assert "meta" in data

    def test_405_on_wrong_method_is_enveloped(self, client):
        resp = client.post("/api/v1/only-get")
        assert resp.status_code == 405
        data = resp.get_json()
        assert data["ok"] is False
        assert data["error"]["code"] == "METHOD_NOT_ALLOWED"

    def test_uncaught_exception_returns_generic_500_envelope(self, client):
        resp = client.get("/api/v1/raise-generic-exception")
        assert resp.status_code == 500
        data = resp.get_json()
        assert data["ok"] is False
        assert data["error"]["code"] == "INTERNAL_ERROR"
        # never leak the real exception text to the HTTP boundary
        assert "boom" not in data["error"]["message"]
