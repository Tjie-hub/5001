"""Tests for routes/v1/market.py -- GET /api/v1/market/summary, the
Market Workspace's Executive Market Summary read model (Production OS
Slice 4).

Monkeypatches routes.v1.market.get_risk_dashboard (the same aggregator
already tested in isolation by tests/test_dashboard_risk.py) rather than
building a real DB fixture here, matching tests/test_v1_registry_routes.py's
convention of isolating route wiring from engine-level behavior.
"""
import pytest
from flask import Flask

from routes.v1 import api_v1_bp


@pytest.fixture
def client():
    app = Flask(__name__)
    app.register_blueprint(api_v1_bp)
    return app.test_client()


def _fake_dashboard(date="2026-08-20"):
    return {
        "date": date,
        "risk_score": 14.0,
        "tier": "GREEN",
        "components": {
            "vpin": 0.0, "accdist": 40.0, "breadth": 0.0,
            "technicals": 0.0, "foreign_flow": 40.0,
        },
        "ihsg": {
            "close": 7250.5, "ma5": 7230.1, "ma20": 7190.4,
            "death_cross": False, "lower_high": False,
            "support_breaks": [], "ytd_pct": 3.2,
        },
        "breadth": {
            "date": date, "advancers": 210, "decliners": 150, "unchanged": 30,
            "adv_dec_ratio": 1.4, "pct_advancing": 52.5, "pct_above_ma20": 61.0,
            "label": "BULL_MARKET",
        },
        "foreign_flow": {"today": 1.2e9, "net_5d": 5.3e9, "net_20d": -2.1e9, "trend": "INFLOW"},
        "vpin": {"tickers_with_vpin": 340, "avg_vpin": 0.31, "pct_above_08": 0.0,
                  "pct_above_095": 0.0, "label": "GREEN"},
        "accdist": {"date": date, "total": 390, "dist_count": 80, "acc_count": 160,
                     "neutral_count": 150, "dist_pct": 20.5, "acc_pct": 41.0,
                     "avg_numeric_score": 0.4, "label": "NEUTRAL"},
    }


class TestMarketSummaryEndpoint:
    def test_returns_the_aggregator_payload_verbatim(self, client, monkeypatch):
        payload = _fake_dashboard()
        monkeypatch.setattr(
            "routes.v1.market.get_risk_dashboard",
            lambda db_path, date: payload,
        )

        resp = client.get("/api/v1/market/summary")

        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data == payload

    def test_default_date_is_today(self, client, monkeypatch):
        from datetime import date as date_cls

        captured = {}

        def _fake(db_path, date):
            captured["date"] = date
            return _fake_dashboard(date)

        monkeypatch.setattr("routes.v1.market.get_risk_dashboard", _fake)

        resp = client.get("/api/v1/market/summary")

        assert resp.status_code == 200
        assert captured["date"] == date_cls.today().isoformat()

    def test_date_query_param_is_forwarded(self, client, monkeypatch):
        captured = {}

        def _fake(db_path, date):
            captured["date"] = date
            return _fake_dashboard(date)

        monkeypatch.setattr("routes.v1.market.get_risk_dashboard", _fake)

        resp = client.get("/api/v1/market/summary?date=2026-07-01")

        assert resp.status_code == 200
        assert captured["date"] == "2026-07-01"
        assert resp.get_json()["data"]["date"] == "2026-07-01"

    def test_insufficient_data_is_a_valid_200_not_an_error(self, client, monkeypatch):
        """The aggregator never raises/404s for missing data -- it degrades
        to INSUFFICIENT_DATA/NEUTRAL labels (engine/dashboard.py's _empty_*
        helpers). The route must pass that straight through as 200, not
        invent an error for a legitimate empty state."""
        empty_payload = {
            "date": "2026-08-20", "risk_score": 0.0, "tier": "GREEN",
            "components": {"vpin": 0.0, "accdist": 0.0, "breadth": 0.0,
                            "technicals": 0.0, "foreign_flow": 0.0},
            "ihsg": {"close": None, "ma5": None, "ma20": None,
                      "death_cross": False, "lower_high": False,
                      "support_breaks": [], "ytd_pct": None},
            "breadth": {"date": "2026-08-20", "advancers": 0, "decliners": 0,
                         "unchanged": 0, "adv_dec_ratio": 0.0, "pct_advancing": 0.0,
                         "pct_above_ma20": 0.0, "label": "INSUFFICIENT_DATA"},
            "foreign_flow": {"today": None, "net_5d": None, "net_20d": None, "trend": "NEUTRAL"},
            "vpin": {"avg_vpin": 0.0, "pct_above_08": 0.0, "pct_above_095": 0.0,
                      "label": "INSUFFICIENT_DATA"},
            "accdist": {"date": "2026-08-20", "total": 0, "dist_count": 0, "acc_count": 0,
                         "neutral_count": 0, "dist_pct": 0.0, "acc_pct": 0.0,
                         "avg_numeric_score": 0.0, "label": "NEUTRAL"},
        }
        monkeypatch.setattr(
            "routes.v1.market.get_risk_dashboard",
            lambda db_path, date: empty_payload,
        )

        resp = client.get("/api/v1/market/summary")

        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert data["breadth"]["label"] == "INSUFFICIENT_DATA"
        assert data["ihsg"]["close"] is None
