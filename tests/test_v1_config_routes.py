"""Tests for routes/v1/config.py -- /api/v1/config, /api/v1/config/runtime
(Production Engine Phase 2, Workstream 2B Task 2B-3).
"""
import pytest
from flask import Flask

from routes.v1 import api_v1_bp


@pytest.fixture
def client():
    app = Flask(__name__)
    app.register_blueprint(api_v1_bp)
    return app.test_client()


class TestConfigEndpoint:
    def test_returns_config_summary_via_envelope(self, client):
        resp = client.get("/api/v1/config")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["database_backend"] == "sqlite"
        assert data["timezone"] == "Asia/Jakarta"
        assert "version" in data
        assert "logging_level" in data


class TestConfigRuntimeEndpoint:
    def test_returns_runtime_config_via_envelope(self, client, monkeypatch):
        monkeypatch.setenv("AUTH_MODE", "shadow")
        monkeypatch.setenv("EDGE_SCORE_MODE", "off")

        resp = client.get("/api/v1/config/runtime")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["auth_mode"] == "shadow"
        assert data["edge_score_mode"] == "off"
        assert "agent_firm_enabled" in data


class TestNoSecretsAtHttpLayer:
    """Belt-and-suspenders on top of tests/engine/test_config_info.py's unit
    coverage: assert the guarantee holds through the actual HTTP response
    body too, not just the service function's return value."""

    def test_no_secret_values_in_either_response_body(self, client, monkeypatch):
        secrets = {
            "TELEGRAM_TOKEN": "sekret-telegram-token-value",
            "FLASK_SECRET_KEY": "sekret-flask-key-value",
            "AUTH_TOKEN_ADMIN": "sekret-admin-token-0123456789",
            "STOCKBIT_PASS": "sekret-stockbit-password",
        }
        for var, val in secrets.items():
            monkeypatch.setenv(var, val)

        body = (client.get("/api/v1/config").get_data(as_text=True)
                 + client.get("/api/v1/config/runtime").get_data(as_text=True))
        for var, val in secrets.items():
            assert val not in body, f"{var} leaked into the HTTP response body"
