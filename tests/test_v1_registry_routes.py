"""Tests for routes/v1/registry.py -- GET /api/v1/registry/status, a
read-only summary of the Edge Registry's admission state (approved/shadow
counts + entries), for the frontend Production Panel (Decision Center).

Never touches the real registry/edge_registry.yaml -- monkeypatches
engine.registry_loader.get_registry to return a controlled fixture, the
same seam engine/registry_loader.py itself exposes for this purpose
(admission_path(), startup_summary() etc. all read through it too).
"""
import pytest
from flask import Flask

from routes.v1 import api_v1_bp


@pytest.fixture
def client():
    app = Flask(__name__)
    app.register_blueprint(api_v1_bp)
    return app.test_client()


def _fake_registry(entries=(), skipped=(), violations=(), debt=(), hash_="abc1234"):
    return {
        "entries": list(entries),
        "skipped": list(skipped),
        "violations": list(violations),
        "debt": list(debt),
        "hash": hash_,
    }


class TestRegistryStatusEndpoint:
    def test_counts_approved_and_shadow_entries(self, client, monkeypatch):
        entries = [
            {"id": "NR7_BULL", "version": 2, "status": "SHADOW",
             "strategy_fn": "NR7 Breakout", "regimes": ["BULL_MODERATE", "BULL_STRONG"]},
        ]
        monkeypatch.setattr(
            "engine.registry_loader.get_registry",
            lambda: _fake_registry(entries=entries, debt=[("NR7_BULL_v2", "reason")]),
        )

        resp = client.get("/api/v1/registry/status")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["approved"] == 0
        assert data["shadow"] == 1

    def test_lists_entry_summaries_without_internal_fields(self, client, monkeypatch):
        entries = [
            {"id": "NR7_BULL", "version": 2, "status": "SHADOW",
             "strategy_fn": "NR7 Breakout", "regimes": ["BULL_MODERATE", "BULL_STRONG"],
             "universe": {"BBCA", "BRPT"}, "requires": {"exit_kernel": 1},
             "manifest": "manifests/NR7_BULL_v2.yaml"},
        ]
        monkeypatch.setattr(
            "engine.registry_loader.get_registry",
            lambda: _fake_registry(entries=entries),
        )

        resp = client.get("/api/v1/registry/status")
        data = resp.get_json()["data"]
        assert data["entries"] == [
            {"id": "NR7_BULL", "version": 2, "status": "SHADOW",
             "strategy_fn": "NR7 Breakout", "regimes": ["BULL_MODERATE", "BULL_STRONG"]},
        ]

    def test_zero_entries_is_a_valid_empty_state_not_an_error(self, client, monkeypatch):
        monkeypatch.setattr(
            "engine.registry_loader.get_registry",
            lambda: _fake_registry(entries=[]),
        )

        resp = client.get("/api/v1/registry/status")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["approved"] == 0
        assert data["shadow"] == 0
        assert data["entries"] == []

    def test_includes_registry_hash_and_skip_debt_violation_counts(self, client, monkeypatch):
        monkeypatch.setattr(
            "engine.registry_loader.get_registry",
            lambda: _fake_registry(
                entries=[], skipped=[("X_v1", "bad")], violations=[("Y_v1", "bad")],
                debt=[("Z_v1", "bad")], hash_="deadbeef",
            ),
        )

        resp = client.get("/api/v1/registry/status")
        data = resp.get_json()["data"]
        assert data["hash"] == "deadbeef"
        assert data["skipped_count"] == 1
        assert data["violation_count"] == 1
        assert data["debt_count"] == 1
