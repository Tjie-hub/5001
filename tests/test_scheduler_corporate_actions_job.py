"""Scheduler integration for the new corporate actions collector
(stockbit_corporate_actions.py). Mirrors run_broker_flow_fetch()'s /
run_broker_period_summary_fetch()'s existing per-ticker try/except loop and
Telegram-on-failure contract."""
from unittest.mock import MagicMock

import scheduler.jobs as jobs


def test_holiday_skip_prevents_fetch(monkeypatch):
    monkeypatch.setattr(jobs, "_holiday_skip", lambda name: True)
    called = MagicMock()
    monkeypatch.setattr("stockbit_corporate_actions.run_and_persist_corporate_actions", called)

    jobs.run_corporate_actions_fetch()

    called.assert_not_called()


def test_no_token_aborts_without_raising(monkeypatch):
    monkeypatch.setattr(jobs, "_holiday_skip", lambda name: False)
    monkeypatch.setattr("stockbit_fetcher.extract_token_from_chrome", lambda: None)
    called = MagicMock()
    monkeypatch.setattr("stockbit_corporate_actions.run_and_persist_corporate_actions", called)
    alerts = []
    monkeypatch.setattr(jobs, "send_telegram", lambda text: alerts.append(text))

    jobs.run_corporate_actions_fetch()  # must not raise

    called.assert_not_called()
    assert len(alerts) == 1
    assert "oken" in alerts[0]


def test_success_calls_run_and_persist_for_every_ticker(monkeypatch):
    monkeypatch.setattr(jobs, "_holiday_skip", lambda name: False)
    monkeypatch.setattr("stockbit_fetcher.extract_token_from_chrome", lambda: "tok")
    monkeypatch.setattr("stockbit_fetcher.verify_token", lambda tok: True)
    monkeypatch.setattr("stockbit_fetcher.get_tickers", lambda cat: ["BBCA", "TLKM"])

    calls = []

    def _fake(ticker, token, db_path=None):
        calls.append(ticker)
        return {"ticker": ticker, "fetch_date": "2026-08-05", "count": 3}

    monkeypatch.setattr("stockbit_corporate_actions.run_and_persist_corporate_actions", _fake)
    alerts = []
    monkeypatch.setattr(jobs, "send_telegram", lambda text: alerts.append(text))

    jobs.run_corporate_actions_fetch()

    assert calls == ["BBCA", "TLKM"]
    assert alerts == []  # no alert on full success


def test_one_ticker_failure_does_not_block_the_rest(monkeypatch):
    monkeypatch.setattr(jobs, "_holiday_skip", lambda name: False)
    monkeypatch.setattr("stockbit_fetcher.extract_token_from_chrome", lambda: "tok")
    monkeypatch.setattr("stockbit_fetcher.verify_token", lambda tok: True)
    monkeypatch.setattr("stockbit_fetcher.get_tickers", lambda cat: ["BBCA", "TLKM", "GOTO"])

    calls = []

    def _fake(ticker, token, db_path=None):
        calls.append(ticker)
        if ticker == "TLKM":
            raise RuntimeError("429 rate limited")
        return {"ticker": ticker, "fetch_date": "2026-08-05", "count": 1}

    monkeypatch.setattr("stockbit_corporate_actions.run_and_persist_corporate_actions", _fake)
    alerts = []
    monkeypatch.setattr(jobs, "send_telegram", lambda text: alerts.append(text))

    jobs.run_corporate_actions_fetch()  # must not raise

    assert calls == ["BBCA", "TLKM", "GOTO"]  # every ticker still attempted
    assert len(alerts) == 1
    assert "TLKM" in alerts[0]


def test_all_tickers_failing_never_raises(monkeypatch):
    monkeypatch.setattr(jobs, "_holiday_skip", lambda name: False)
    monkeypatch.setattr("stockbit_fetcher.extract_token_from_chrome", lambda: "tok")
    monkeypatch.setattr("stockbit_fetcher.verify_token", lambda tok: True)
    monkeypatch.setattr("stockbit_fetcher.get_tickers", lambda cat: ["BBCA"])

    def _fail(ticker, token, db_path=None):
        raise RuntimeError("boom")

    monkeypatch.setattr("stockbit_corporate_actions.run_and_persist_corporate_actions", _fail)
    monkeypatch.setattr(jobs, "send_telegram", lambda text: None)

    jobs.run_corporate_actions_fetch()  # must complete without raising
