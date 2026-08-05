"""Scheduler integration for the existing Stockbit screener collector
(screener/stockbit_screener.py). Mirrors the style of
tests/test_pipeline_health_jobs.py and tests/test_scheduler_job_error_alert.py.

The collector itself (fetch_template/run_screener) is not touched — only
scheduler.jobs.run_stockbit_screener_fetch(), which is new, and
scheduler/__init__.py's registration of it.
"""
from unittest.mock import MagicMock

import scheduler.jobs as jobs


def test_holiday_skip_prevents_fetch(monkeypatch):
    monkeypatch.setattr(jobs, "_holiday_skip", lambda name: True)
    called = MagicMock()
    monkeypatch.setattr("screener.stockbit_screener.run_and_persist_screener", called)

    jobs.run_stockbit_screener_fetch()

    called.assert_not_called()


def test_success_calls_run_and_persist_for_every_guru_template(monkeypatch):
    monkeypatch.setattr(jobs, "_holiday_skip", lambda name: False)
    from screener.stockbit_screener import GURU_TEMPLATES

    calls = []

    def _fake(name, db_path=None):
        calls.append(name)
        return {"template_id": 1, "template_name": name, "fetch_date": "2026-08-04", "count": 3}

    monkeypatch.setattr("screener.stockbit_screener.run_and_persist_screener", _fake)
    alerts = []
    monkeypatch.setattr(jobs, "send_telegram", lambda text: alerts.append(text))

    jobs.run_stockbit_screener_fetch()

    assert set(calls) == set(GURU_TEMPLATES)
    assert alerts == []  # no alert on success


def test_one_template_failure_does_not_block_the_others(monkeypatch):
    monkeypatch.setattr(jobs, "_holiday_skip", lambda name: False)
    from screener.stockbit_screener import GURU_TEMPLATES
    assert len(GURU_TEMPLATES) >= 2, "test assumes at least 2 registered templates"
    first_name = next(iter(GURU_TEMPLATES))

    calls = []

    def _fake(name, db_path=None):
        calls.append(name)
        if name == first_name:
            raise RuntimeError("token expired")
        return {"template_id": 1, "template_name": name, "fetch_date": "2026-08-04", "count": 2}

    monkeypatch.setattr("screener.stockbit_screener.run_and_persist_screener", _fake)
    alerts = []
    monkeypatch.setattr(jobs, "send_telegram", lambda text: alerts.append(text))

    jobs.run_stockbit_screener_fetch()  # must not raise

    assert set(calls) == set(GURU_TEMPLATES)  # every template still attempted
    assert len(alerts) == 1
    assert "token expired" in alerts[0] or first_name in alerts[0]


def test_all_templates_failing_never_raises(monkeypatch):
    monkeypatch.setattr(jobs, "_holiday_skip", lambda name: False)

    def _fail(name, db_path=None):
        raise RuntimeError("boom")

    monkeypatch.setattr("screener.stockbit_screener.run_and_persist_screener", _fail)
    monkeypatch.setattr(jobs, "send_telegram", lambda text: None)

    jobs.run_stockbit_screener_fetch()  # must complete without raising, so the
    # scheduler process (and every other scheduled job) keeps running
