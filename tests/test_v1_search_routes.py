"""Tests for routes/v1/search.py -- GET /api/v1/search/instruments, the
Search Workspace's instrument search (Production OS Slice 5).

Monkeypatches routes.v1.search.search_instruments (the same aggregator
already tested in isolation by tests/test_instrument_search.py), matching
tests/test_v1_registry_routes.py's / tests/test_v1_market_routes.py's
convention.
"""
import pytest
from flask import Flask

from routes.v1 import api_v1_bp


@pytest.fixture
def client():
    app = Flask(__name__)
    app.register_blueprint(api_v1_bp)
    return app.test_client()


class TestSearchInstrumentsEndpoint:
    def test_returns_matches_for_a_query(self, client, monkeypatch):
        fake_results = [
            {"ticker": "BBCA", "in_idx30": True, "in_lq45": True, "in_idx80": True},
            {"ticker": "BBRI", "in_idx30": True, "in_lq45": True, "in_idx80": True},
        ]
        captured = {}

        def _fake(db_path, query, limit=20):
            captured["query"] = query
            captured["limit"] = limit
            return fake_results

        monkeypatch.setattr("routes.v1.search.search_instruments", _fake)

        resp = client.get("/api/v1/search/instruments?q=BB")

        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["query"] == "BB"
        assert data["count"] == 2
        assert data["results"] == fake_results
        assert captured["query"] == "BB"
        assert captured["limit"] == 20

    def test_forwards_an_explicit_limit(self, client, monkeypatch):
        captured = {}
        monkeypatch.setattr(
            "routes.v1.search.search_instruments",
            lambda db_path, query, limit=20: captured.update(limit=limit) or [],
        )

        client.get("/api/v1/search/instruments?q=B&limit=5")

        assert captured["limit"] == 5

    def test_missing_query_is_a_400_not_a_500(self, client):
        resp = client.get("/api/v1/search/instruments")

        assert resp.status_code == 400
        body = resp.get_json()
        assert body["ok"] is False
        assert body["error"]["code"] == "MISSING_QUERY"

    def test_blank_query_is_also_missing(self, client):
        resp = client.get("/api/v1/search/instruments?q=%20%20")

        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "MISSING_QUERY"

    def test_zero_results_is_a_valid_200_empty_state_not_an_error(self, client, monkeypatch):
        monkeypatch.setattr(
            "routes.v1.search.search_instruments",
            lambda db_path, query, limit=20: [],
        )

        resp = client.get("/api/v1/search/instruments?q=ZZZNOPE")

        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["results"] == []
        assert data["count"] == 0
