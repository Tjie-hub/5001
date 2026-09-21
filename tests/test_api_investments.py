"""Tests for the canonical investment store + its v1 API (consolidation
2026-09-03, ex-5003 Investment Dashboard ledger).

Store tests run against a real tmp SQLite file; route tests follow the repo
convention of monkeypatching the store module (see test_v1_market_routes.py)
to keep HTTP wiring isolated from storage behavior.
"""
import json
import os

import pytest
from flask import Flask

from data import investments
from routes.v1 import api_v1_bp


@pytest.fixture()
def store_db(tmp_path):
    db = str(tmp_path / "inv.db")
    investments.init_investment_tables(db)
    investments.init_investment_tables(db)  # idempotent by contract
    return db


@pytest.fixture()
def client():
    app = Flask(__name__)
    app.register_blueprint(api_v1_bp)
    app.config["TESTING"] = True
    return app.test_client()


SNAPSHOT = {
    "txns": [
        {"id": 1, "date": "2020-12-31T17:00:00.000Z", "ticker": "INDR", "type": "BUY",
         "price": 7200, "qty": 1000, "notes": ""},
        {"id": 2, "date": "2021-01-04T17:00:00.000Z", "ticker": "INDR", "type": "BUY",
         "price": 7200, "qty": 1000, "notes": ""},  # same-day-equal fill is legitimate
    ],
    "CEQ": [
        {"entryDate": "2026-01-27T17:00:00.000Z", "exitDate": "2026-02-03T17:00:00.000Z",
         "ticker": "BBCA", "entryPrice": 7300, "exitPrice": 7750, "qty": 100,
         "netPL": 40000, "plPct": 5.4},
    ],
    "mfOpen": [
        {"id": "f1", "name": "Test Fund", "entryDate": "2026-01-05T17:00:00.000Z",
         "entryNav": 1000.0, "units": 10000.0, "costBasis": 10_000_000},
    ],
    "CMF": [
        {"id": "f0", "name": "Old Fund", "entryDate": "2025-12-22T17:00:00.000Z",
         "exitDate": "2026-01-20T17:00:00.000Z", "entryNav": 1883.55, "exitNav": 1879.63,
         "units": 5309.12, "costBasis": 10_000_000, "totalReturn": 9_979_188.18,
         "netPL": -20_811.76, "plPct": -0.2},
    ],
    "divs": [
        {"id": 1, "date": "2026-02-10T17:00:00.000Z", "ticker": "INDR", "perShare": 60,
         "qty": 2000, "taxPct": 10, "notes": ""},
    ],
    "eqPrices": {"INDR": 8000},
    "nextId": 3,
    "nextDivId": 2,
}


class TestStoreImport:
    def test_import_counts_and_idempotency(self, store_db):
        first = investments.import_snapshot(SNAPSHOT, db_path=store_db)
        assert first == {"transactions": 2, "closed_equity": 1, "funds": 2,
                         "dividends": 1, "prices": 1}
        second = investments.import_snapshot(SNAPSHOT, db_path=store_db)
        assert second["transactions"] == 0
        assert second["closed_equity"] == 0
        assert second["dividends"] == 0
        assert len(investments.list_transactions(store_db)) == 2

    def test_utc_instant_becomes_wib_calendar_date(self, store_db):
        investments.import_snapshot(SNAPSHOT, db_path=store_db)
        dates = [t["date"] for t in investments.list_transactions(store_db)]
        assert "2021-01-01" in dates  # 2020-12-31T17:00Z == 2021-01-01 WIB
        assert "2021-01-05" in dates


class TestStoreHoldingsMath:
    def test_avg_cost_includes_buy_fee_and_breakeven_covers_sell_fee(self, store_db):
        investments.add_transaction("2026-01-02", "BBRI", "BUY", 5000, 1000, db_path=store_db)
        investments.set_price("BBRI", 5000, db_path=store_db)
        h = investments.compute_holdings(store_db)["holdings"][0]
        assert h["qty"] == 1000
        assert h["avg_price"] == pytest.approx(5000 * 1.0015)          # buy fee loaded
        assert h["breakeven"] == pytest.approx(h["avg_price"] / (1 - 0.0025))
        # flat price: fee drag is the whole unrealized loss
        assert h["unrealized_pl"] == pytest.approx(1000 * 5000 - h["cost_basis"])
        assert h["cost_basis"] == pytest.approx(1000 * 5000 * 1.0015)

    def test_sell_reduces_holdings_at_running_average(self, store_db):
        investments.add_transaction("2026-01-02", "BBRI", "BUY", 5000, 1000, db_path=store_db)
        investments.add_transaction("2026-01-03", "BBRI", "SELL", 6000, 400, db_path=store_db)
        holdings = investments.compute_holdings(store_db)["holdings"]
        assert len(holdings) == 1  # 400 of 1000 sold — 600 shares remain
        row = holdings[0]
        assert row["qty"] == 600
        # cost basis reduced by sellQty * running avg (5007.5 = 5000*1.0015)
        assert row["cost_basis"] == pytest.approx(600 * 5007.5)
        # full exit leaves nothing open
        investments.add_transaction("2026-01-04", "BBRI", "SELL", 6000, 600, db_path=store_db)
        assert investments.compute_holdings(store_db)["holdings"] == []

    def test_summary_realized_is_closed_journals_only(self, store_db):
        investments.import_snapshot(SNAPSHOT, db_path=store_db)
        s = investments.summary(store_db)
        assert s["realized_equity_pl"] == pytest.approx(40000)
        assert s["realized_fund_pl"] == pytest.approx(-20811.76)
        assert s["realized_pl"] == pytest.approx(40000 - 20811.76)
        assert s["dividends_net"] == pytest.approx(60 * 2000 * 0.9)
        assert s["open_positions"] == 1  # INDR
        assert s["allocation"][0]["ticker"] == "INDR"
        assert s["allocation"][0]["pct"] == pytest.approx(100.0)

    def test_fund_redeem_moves_open_to_closed(self, store_db):
        investments.import_snapshot(SNAPSHOT, db_path=store_db)
        result = investments.redeem_fund("f1", "2026-02-05", 1050.0, db_path=store_db)
        assert result["net_pl"] == pytest.approx(500_000)
        assert result["pl_pct"] == pytest.approx(5.0)
        assert [f["id"] for f in investments.list_funds("OPEN", db_path=store_db)] == []
        assert [f["id"] for f in investments.list_funds("CLOSED", db_path=store_db)] == ["f0", "f1"]

    def test_export_round_trips_the_snapshot(self, store_db):
        investments.import_snapshot(SNAPSHOT, db_path=store_db)
        ex = investments.export_snapshot(store_db)
        assert len(ex["txns"]) == 2
        assert len(ex["CEQ"]) == 1
        assert len(ex["mfOpen"]) == 1
        assert len(ex["CMF"]) == 1
        assert len(ex["divs"]) == 1
        assert ex["eqPrices"] == {"INDR": 8000}
        # and the export re-imports as a no-op
        counts = investments.import_snapshot(ex, db_path=store_db)
        assert counts["transactions"] == 0
        assert counts["closed_equity"] == 0
        assert counts["dividends"] == 0

    def test_add_transaction_validates(self, store_db):
        with pytest.raises(ValueError):
            investments.add_transaction("2026-01-02", "BBRI", "HOLD", 5000, 100, db_path=store_db)
        with pytest.raises(ValueError):
            investments.add_transaction("2026-01-02", "BBRI", "BUY", 0, 100, db_path=store_db)


class TestRoutes:
    def test_summary_envelope(self, client, monkeypatch):
        monkeypatch.setattr(
            "routes.v1.investments.investments.summary",
            lambda db_path=None: {"portfolio_value": 123.0},
        )
        resp = client.get("/api/v1/investments/summary")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["ok"] is True
        assert body["data"] == {"portfolio_value": 123.0}
        assert body["meta"]["api_version"] == "v1"

    def test_post_transaction_validates(self, client):
        resp = client.post("/api/v1/investments/transactions", json={"ticker": "BBRI"})
        assert resp.status_code == 400
        assert resp.get_json()["ok"] is False

    def test_post_transaction_returns_201(self, client, monkeypatch):
        captured = {}

        def _fake(date, ticker, txn_type, price, qty, notes="", db_path=None, external_id=None):
            captured.update(ticker=ticker, type=txn_type)
            return 42

        monkeypatch.setattr("routes.v1.investments.investments.add_transaction", _fake)
        resp = client.post("/api/v1/investments/transactions", json={
            "date": "2026-02-01", "ticker": "bbri", "type": "BUY",
            "price": 5000, "qty": 100,
        })
        assert resp.status_code == 201
        assert resp.get_json()["data"] == {"id": 42}
        # route passes the body through verbatim; the store uppercases
        assert captured["ticker"] == "bbri"
        assert captured["type"] == "BUY"

    def test_delete_unknown_transaction_is_404(self, client, monkeypatch):
        monkeypatch.setattr(
            "routes.v1.investments.investments.delete_transaction", lambda txn_id, db_path=None: 0)
        resp = client.delete("/api/v1/investments/transactions/999")
        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "NOT_FOUND"

    def test_import_rejects_non_object_body(self, client):
        resp = client.post("/api/v1/investments/import", data="[]",
                           content_type="application/json")
        assert resp.status_code == 400

    def test_price_refresh_rejects_bad_tickers(self, client):
        resp = client.post("/api/v1/investments/prices/refresh", json={"tickers": "BBRI"})
        assert resp.status_code == 400

    def test_export_envelope(self, client, monkeypatch):
        monkeypatch.setattr(
            "routes.v1.investments.investments.export_snapshot",
            lambda db_path=None: {"txns": [], "CEQ": [], "mfOpen": [], "CMF": [],
                                  "divs": [], "eqPrices": {}},
        )
        resp = client.get("/api/v1/investments/export")
        assert resp.status_code == 200
        assert resp.get_json()["data"]["txns"] == []
