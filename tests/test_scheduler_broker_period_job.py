"""Scheduler integration for the new broker-period-summary collector
(stockbit_broker_period.py). Mirrors run_broker_flow_fetch()'s existing
per-ticker try/except loop and Telegram-on-failure contract — see
tests/test_pipeline_health_jobs.py / test_scheduler_stockbit_screener_job.py
for the same house style used here.
"""
from unittest.mock import MagicMock

import scheduler.jobs as jobs


def test_holiday_skip_prevents_fetch(monkeypatch):
    monkeypatch.setattr(jobs, "_holiday_skip", lambda name: True)
    called = MagicMock()
    monkeypatch.setattr("stockbit_broker_period.run_and_persist_broker_period", called)

    jobs.run_broker_period_summary_fetch()

    called.assert_not_called()


def test_no_token_aborts_without_raising(monkeypatch):
    monkeypatch.setattr(jobs, "_holiday_skip", lambda name: False)
    monkeypatch.setattr("stockbit_fetcher.extract_token_from_chrome", lambda: None)
    called = MagicMock()
    monkeypatch.setattr("stockbit_broker_period.run_and_persist_broker_period", called)
    alerts = []
    monkeypatch.setattr(jobs, "send_telegram", lambda text: alerts.append(text))

    jobs.run_broker_period_summary_fetch()  # must not raise

    called.assert_not_called()
    assert len(alerts) == 1
    assert "Token" in alerts[0] or "token" in alerts[0]


def test_success_calls_run_and_persist_for_every_ticker_and_period(monkeypatch):
    monkeypatch.setattr(jobs, "_holiday_skip", lambda name: False)
    monkeypatch.setattr("stockbit_fetcher.extract_token_from_chrome", lambda: "tok")
    monkeypatch.setattr("stockbit_fetcher.verify_token", lambda tok: True)
    monkeypatch.setattr("stockbit_fetcher.get_tickers", lambda cat: ["BBCA", "TLKM"])

    calls = []

    def _fake(ticker, period_name, token, db_path=None):
        calls.append((ticker, period_name))
        return {"ticker": ticker, "period": period_name, "fetch_date": "2026-08-04", "count": 3}

    monkeypatch.setattr("stockbit_broker_period.run_and_persist_broker_period", _fake)
    alerts = []
    monkeypatch.setattr(jobs, "send_telegram", lambda text: alerts.append(text))

    jobs.run_broker_period_summary_fetch()

    from stockbit_broker_period import PERIODS
    expected = {(t, p) for t in ("BBCA", "TLKM") for p in PERIODS}
    assert set(calls) == expected
    assert alerts == []  # no alert on full success


def test_one_ticker_failure_does_not_block_the_rest(monkeypatch):
    monkeypatch.setattr(jobs, "_holiday_skip", lambda name: False)
    monkeypatch.setattr("stockbit_fetcher.extract_token_from_chrome", lambda: "tok")
    monkeypatch.setattr("stockbit_fetcher.verify_token", lambda tok: True)
    monkeypatch.setattr("stockbit_fetcher.get_tickers", lambda cat: ["BBCA", "TLKM", "GOTO"])

    calls = []

    def _fake(ticker, period_name, token, db_path=None):
        calls.append((ticker, period_name))
        if ticker == "TLKM":
            raise RuntimeError("429 rate limited")
        return {"ticker": ticker, "period": period_name, "fetch_date": "2026-08-04", "count": 1}

    monkeypatch.setattr("stockbit_broker_period.run_and_persist_broker_period", _fake)
    alerts = []
    monkeypatch.setattr(jobs, "send_telegram", lambda text: alerts.append(text))

    jobs.run_broker_period_summary_fetch()  # must not raise

    from stockbit_broker_period import PERIODS
    expected = {(t, p) for t in ("BBCA", "TLKM", "GOTO") for p in PERIODS}
    assert set(calls) == expected  # every ticker x period still attempted
    assert len(alerts) == 1
    assert "TLKM" in alerts[0]


def test_all_tickers_failing_never_raises(monkeypatch):
    monkeypatch.setattr(jobs, "_holiday_skip", lambda name: False)
    monkeypatch.setattr("stockbit_fetcher.extract_token_from_chrome", lambda: "tok")
    monkeypatch.setattr("stockbit_fetcher.verify_token", lambda tok: True)
    monkeypatch.setattr("stockbit_fetcher.get_tickers", lambda cat: ["BBCA"])

    def _fail(ticker, period_name, token, db_path=None):
        raise RuntimeError("boom")

    monkeypatch.setattr("stockbit_broker_period.run_and_persist_broker_period", _fail)
    monkeypatch.setattr(jobs, "send_telegram", lambda text: None)

    jobs.run_broker_period_summary_fetch()  # must complete without raising
