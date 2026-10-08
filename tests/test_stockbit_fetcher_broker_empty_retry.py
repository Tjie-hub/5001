"""run_flow() retries empty broker summaries after the main loop.

Under load Stockbit's marketdetectors endpoint answers 200 with an EMPTY
broker list (no 429), and run_flow() used to drop that silently: coverage fell
from ~825 to 623-706 tickers/day from 2026-10-05 and a held position (TOWR)
had no broker rows for 3 sessions, while the same call succeeded the next
morning. Empty results on tickers that traded are now logged and retried in
slower passes after the main loop; untraded tickers (empty is genuine) are not.
"""
import sqlite3

import stockbit_fetcher as sf
from tests.test_stockbit_fetcher_broker_flow_historical import (
    _broker_result, _flow_result, _seed_schema,
)


def _empty(ticker, trade_date):
    r = _broker_result(ticker, trade_date)
    r["broker_rows"] = []
    return r


def _setup(tmp_path, monkeypatch, broker_fn, flow_fn=None):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(sf, "WALKFORWARD_DB", db_path)
    _seed_schema(db_path)
    logs = []
    monkeypatch.setattr(sf, "log", lambda m: logs.append(m))
    monkeypatch.setattr(sf, "send_telegram", lambda *a, **k: None)
    monkeypatch.setattr(sf, "fetch_flow", flow_fn or (lambda token, ticker, date=None: _flow_result(ticker, date)))
    monkeypatch.setattr(sf, "fetch_broker_flow", broker_fn)
    monkeypatch.setattr(sf.time, "sleep", lambda *a, **k: None)
    return db_path, logs


def _brokers(db_path):
    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT DISTINCT ticker FROM broker_flow ORDER BY ticker").fetchall()
    conn.close()
    return [r[0] for r in rows]


def test_empty_then_full_is_recovered_in_retry_pass(tmp_path, monkeypatch):
    calls = {}

    def broker(token, ticker, date=None):
        calls[ticker] = calls.get(ticker, 0) + 1
        if ticker == "TOWR" and calls[ticker] == 1:
            return _empty(ticker, date)
        return _broker_result(ticker, date)

    db_path, logs = _setup(tmp_path, monkeypatch, broker)
    sf.run_flow("tok", ["BBCA", "TOWR"], "2026-10-07")
    assert _brokers(db_path) == ["BBCA", "TOWR"]
    assert calls == {"BBCA": 1, "TOWR": 2}
    assert any("broker summary empty" in m for m in logs)
    assert any("recovered 1/1" in m for m in logs)


def test_untraded_ticker_is_not_retried(tmp_path, monkeypatch):
    calls = []

    def flow(token, ticker, date=None):
        f = _flow_result(ticker, date)
        f["buy_lot"] = f["sell_lot"] = 0
        return f

    def broker(token, ticker, date=None):
        calls.append(ticker)
        return _empty(ticker, date)

    db_path, logs = _setup(tmp_path, monkeypatch, broker, flow)
    sf.run_flow("tok", ["ZBRA"], "2026-10-07")
    assert calls == ["ZBRA"]
    assert not any("broker summary empty" in m for m in logs)


def test_still_empty_after_all_passes_is_counted(tmp_path, monkeypatch):
    calls = []

    def broker(token, ticker, date=None):
        calls.append(ticker)
        return _empty(ticker, date)

    db_path, logs = _setup(tmp_path, monkeypatch, broker)
    sf.run_flow("tok", ["TOWR"], "2026-10-07")
    assert len(calls) == 1 + sf.BROKER_RETRY_PASSES
    assert _brokers(db_path) == []
    assert any("Broker coverage" in m and "1 still empty" in m and "TOWR" in m for m in logs)


def test_exception_in_main_pass_is_retried(tmp_path, monkeypatch):
    calls = []

    def broker(token, ticker, date=None):
        calls.append(ticker)
        if len(calls) == 1:
            raise sf.RateLimitExceeded("stayed 429")
        return _broker_result(ticker, date)

    db_path, logs = _setup(tmp_path, monkeypatch, broker)
    sf.run_flow("tok", ["TOWR"], "2026-10-07")
    assert _brokers(db_path) == ["TOWR"]
