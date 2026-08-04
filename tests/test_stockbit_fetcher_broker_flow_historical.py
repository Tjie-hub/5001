"""Regression tests for historical broker_flow backfill support.

Investigation (docs/audit/BROKER_FLOW_BACKFILL_REPORT.md, 2026-08-04) proved
the marketdetectors endpoint DOES serve historical broker data, but
only when BOTH `from` and `to` query params are supplied together — either
one alone is silently ignored and the server returns today's data instead.
fetch_broker_flow() previously sent neither param and run_flow() assumed
backfill was impossible for broker data (`bf = fetch_broker_flow(...) if not
date else None`). Both are fixed here.
"""
import sqlite3
from unittest.mock import patch, MagicMock

import stockbit_fetcher as sf


def _mock_response(brokers_buy=None, brokers_sell=None, to="2026-07-31"):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "data": {
            "to": to,
            "broker_summary": {
                "brokers_buy": brokers_buy or [],
                "brokers_sell": brokers_sell or [],
            },
            "bandar_detector": {},
        }
    }
    return resp


def test_live_fetch_sends_no_date_params():
    """date=None (the default / live path) must not add from/to at all —
    existing live behavior is preserved exactly."""
    with patch("stockbit_fetcher.requests.get", return_value=_mock_response()) as mock_get:
        sf.fetch_broker_flow("tok", "BBCA")

    params = mock_get.call_args.kwargs["params"]
    assert "from" not in params
    assert "to" not in params


def test_historical_fetch_sends_both_from_and_to():
    """The core fix: date="2026-07-31" must set BOTH from and to to that date."""
    with patch("stockbit_fetcher.requests.get", return_value=_mock_response(to="2026-07-31")) as mock_get:
        sf.fetch_broker_flow("tok", "BBCA", "2026-07-31")

    params = mock_get.call_args.kwargs["params"]
    assert params["from"] == "2026-07-31"
    assert params["to"] == "2026-07-31"


def test_never_sends_only_one_of_from_or_to():
    """Sending only one param is silently ignored by the server (proven in
    investigation) — the implementation must never do this for any date value,
    including falsy-looking ones."""
    for date in ["2026-07-31", "2020-01-02"]:
        with patch("stockbit_fetcher.requests.get", return_value=_mock_response(to=date)) as mock_get:
            sf.fetch_broker_flow("tok", "BBCA", date)
        params = mock_get.call_args.kwargs["params"]
        assert ("from" in params) == ("to" in params), (
            f"date={date}: from/to must both be present or both absent"
        )
        if "from" in params:
            assert params["from"] == params["to"] == date


def test_historical_fetch_returns_data_tagged_with_requested_date():
    with patch("stockbit_fetcher.requests.get",
               return_value=_mock_response(
                   brokers_buy=[{"netbs_broker_code": "DX", "blot": "235510", "blotv": "0",
                                 "bval": "0", "bvalv": "0", "netbs_buy_avg_price": "0",
                                 "freq": "1", "type": ""}],
                   to="2026-07-31")):
        result = sf.fetch_broker_flow("tok", "BBCA", "2026-07-31")

    assert result["trade_date"] == "2026-07-31"
    assert result["broker_rows"][0]["broker_code"] == "DX"
    assert result["broker_rows"][0]["lot"] == 235510


def _seed_schema(db_path):
    """run_flow() creates broker_flow/bandar_detector/stockbit_flow_bars via
    init_flow_db(), but stockbit_flow itself needs composite_score/verdict/
    smart_money/foreign_score too — those are added by a separate migration
    path elsewhere in the app (unrelated to this task), not init_flow_db().
    Mirror production's actual schema here rather than chase that path."""
    sf.init_flow_db().close()
    conn = sqlite3.connect(db_path)
    for col, coltype in [("composite_score", "INTEGER"), ("verdict", "TEXT"),
                          ("smart_money", "TEXT"), ("foreign_score", "REAL")]:
        conn.execute(f"ALTER TABLE stockbit_flow ADD COLUMN {col} {coltype}")
    conn.commit()
    conn.close()


def _flow_result(ticker, trade_date):
    return {
        "ticker": ticker, "trade_date": trade_date,
        "buy_lot": 100, "sell_lot": 50, "net_lot": 50,
        "buy_freq": 5, "sell_freq": 3, "net_value": 1000,
        "last_price": 9000, "_raw_data": {},
    }


def _broker_result(ticker, trade_date):
    return {
        "broker_rows": [{
            "ticker": ticker, "trade_date": trade_date, "broker_code": "DX",
            "side": "BUY", "lot": 235510, "lot_value": 0, "value": 0,
            "value_total": 0, "avg_price": 0.0, "freq": 1, "investor_type": "",
        }],
        "bandar": {
            "ticker": ticker, "trade_date": trade_date, "avg_price": None,
            "total_buyer": None, "total_seller": None, "net_broker_count": None,
            "broker_accdist": None, "value": None, "volume": None,
            "top1_accdist": None, "top3_accdist": None, "top5_accdist": None,
            "top10_accdist": None, "avg_accdist": None, "updated_at": "2026-08-04T00:00:00",
        },
        "trade_date": trade_date,
    }


def test_run_flow_writes_broker_flow_for_historical_date(tmp_path, monkeypatch):
    """The core regression this task fixes: historical (date-set) run_flow()
    calls must populate broker_flow exactly like live runs, not skip it."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(sf, "WALKFORWARD_DB", db_path)
    _seed_schema(db_path)
    monkeypatch.setattr(sf, "send_telegram", lambda *a, **k: None)
    monkeypatch.setattr(sf, "fetch_flow", lambda token, ticker, date=None: _flow_result(ticker, date))
    monkeypatch.setattr(sf, "fetch_broker_flow", lambda token, ticker, date=None: _broker_result(ticker, date))
    monkeypatch.setattr(sf.time, "sleep", lambda *a, **k: None)

    sf.run_flow("tok", ["BBCA"], "2026-07-31")

    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT ticker, trade_date, broker_code, side, lot FROM broker_flow"
    ).fetchall()
    conn.close()

    assert rows == [("BBCA", "2026-07-31", "DX", "BUY", 235510)]


def test_run_flow_live_path_unchanged(tmp_path, monkeypatch):
    """date=None must still populate broker_flow (the pre-existing live path)."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(sf, "WALKFORWARD_DB", db_path)
    _seed_schema(db_path)
    monkeypatch.setattr(sf, "send_telegram", lambda *a, **k: None)
    monkeypatch.setattr(sf, "fetch_flow", lambda token, ticker, date=None: _flow_result(ticker, "2026-08-04"))
    monkeypatch.setattr(sf, "fetch_broker_flow", lambda token, ticker, date=None: _broker_result(ticker, "2026-08-04"))
    monkeypatch.setattr(sf.time, "sleep", lambda *a, **k: None)

    sf.run_flow("tok", ["BBCA"])

    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT ticker, trade_date FROM broker_flow").fetchall()
    conn.close()

    assert rows == [("BBCA", "2026-08-04")]


def test_cli_flow_date_writes_all_three_tables(tmp_path, monkeypatch):
    """`stockbit_fetcher.py flow --date YYYY-MM-DD` must write stockbit_flow,
    stockbit_flow_bars, and broker_flow for the requested historical date."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(sf, "WALKFORWARD_DB", db_path)
    _seed_schema(db_path)
    monkeypatch.setattr(sf, "send_telegram", lambda *a, **k: None)
    monkeypatch.setattr(sf, "ensure_valid_token", lambda manual: "tok")
    monkeypatch.setattr(sf.time, "sleep", lambda *a, **k: None)

    raw_bars = {
        "buy": [{"time": "09:00", "lot": {"raw": "100"}, "frequency": {"raw": "1"},
                  "value": {"raw": "1000"}}],
        "sell": [{"time": "09:00", "lot": {"raw": "40"}, "frequency": {"raw": "1"},
                   "value": {"raw": "400"}}],
        "net_values": [{"value": {"raw": "500"}}],
        "prices": [{"value": {"raw": "9000"}}], "date": "2026-07-31",
    }

    def fake_fetch_flow(token, ticker, date=None):
        r = _flow_result(ticker, date)
        r["_raw_data"] = raw_bars
        return r

    monkeypatch.setattr(sf, "fetch_flow", fake_fetch_flow)
    monkeypatch.setattr(sf, "fetch_broker_flow", lambda token, ticker, date=None: _broker_result(ticker, date))

    sf._run_flow_cmd(["BBCA", "--date", "2026-07-31"])

    conn = sqlite3.connect(db_path)
    flow_rows = conn.execute("SELECT COUNT(*) FROM stockbit_flow WHERE trade_date='2026-07-31'").fetchone()[0]
    bars_rows = conn.execute("SELECT COUNT(*) FROM stockbit_flow_bars WHERE trade_date='2026-07-31'").fetchone()[0]
    broker_rows = conn.execute("SELECT COUNT(*) FROM broker_flow WHERE trade_date='2026-07-31'").fetchone()[0]
    conn.close()

    assert flow_rows == 1, "stockbit_flow not written"
    assert bars_rows >= 1, "stockbit_flow_bars not written"
    assert broker_rows == 1, "broker_flow not written"
