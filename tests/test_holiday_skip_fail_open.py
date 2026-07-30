"""P0.E2.S3.T4 -- holiday fail-open note logged (L-4).

Audit L-4: `_holiday_skip` fails open -- a broken calendar check (import
error, or is_trading_day() raising for any other reason) is silently
swallowed by `except Exception: pass`, and the job runs as if today were
a normal trading day even though the check that would have proven that
never actually ran. Two independent copies of this function exist
(scheduler/jobs.py, scheduler/reports.py, confirmed by direct grep before
changing anything -- they are not imported from one another). This module
verifies both now log a warning naming the failing function and the
exception when the fail-open path is taken, without changing the
fail-open *behavior* itself: the job still runs.
"""
import logging

import scheduler.jobs as jobs
import scheduler.reports as reports


# ── scheduler.jobs._holiday_skip ────────────────────────────────────────────

def test_jobs_normal_trading_day_no_log_no_skip(monkeypatch, caplog):
    """Regression: normal operation on an ordinary trading day is
    unchanged -- no skip, no log at all."""
    monkeypatch.setattr("engine.calendar_filter.is_trading_day", lambda: (True, "trading day"))
    with caplog.at_level(logging.INFO):
        result = jobs._holiday_skip("some_job")
    assert result is False
    assert caplog.records == []


def test_jobs_normal_holiday_skips_and_logs_info(monkeypatch, caplog):
    """Regression: normal holiday behavior is unchanged -- still skips,
    still logs at INFO (the pre-existing line), not WARNING."""
    monkeypatch.setattr("engine.calendar_filter.is_trading_day",
                         lambda: (False, "Weekend (Saturday)"))
    with caplog.at_level(logging.INFO):
        result = jobs._holiday_skip("some_job")
    assert result is True
    assert len(caplog.records) == 1
    assert caplog.records[0].levelno == logging.INFO
    assert "Weekend (Saturday)" in caplog.records[0].message


def test_jobs_calendar_import_failure_fails_open_and_logs_warning(monkeypatch, caplog):
    """The regression case the audit describes: is_trading_day() raising
    (simulating a broken calendar import) still fails open (returns
    False, job runs) -- but now logs a warning naming the job and the
    exception, instead of silently passing."""
    def _boom():
        raise ImportError("simulated broken calendar_filter import")

    monkeypatch.setattr("engine.calendar_filter.is_trading_day", _boom)
    with caplog.at_level(logging.INFO):
        result = jobs._holiday_skip("run_premover_eod")

    assert result is False  # fail-open behavior preserved exactly
    assert len(caplog.records) == 1  # no duplicate logging
    rec = caplog.records[0]
    assert rec.levelno == logging.WARNING
    assert "run_premover_eod" in rec.message
    assert "simulated broken calendar_filter import" in rec.message


def test_jobs_unexpected_exception_type_also_fails_open_and_logs(monkeypatch, caplog):
    """Not just ImportError -- any exception from is_trading_day() itself
    (not just the import) takes the same fail-open-and-log path."""
    def _boom():
        raise RuntimeError("unexpected calendar failure")

    monkeypatch.setattr("engine.calendar_filter.is_trading_day", _boom)
    with caplog.at_level(logging.INFO):
        result = jobs._holiday_skip("run_eod_trade_plan")

    assert result is False
    assert len(caplog.records) == 1
    assert caplog.records[0].levelno == logging.WARNING


# ── scheduler.reports._holiday_skip (independent copy) ──────────────────────

def test_reports_normal_trading_day_no_log_no_skip(monkeypatch, caplog):
    monkeypatch.setattr("engine.calendar_filter.is_trading_day", lambda: (True, "trading day"))
    with caplog.at_level(logging.INFO):
        result = reports._holiday_skip("some_report")
    assert result is False
    assert caplog.records == []


def test_reports_normal_holiday_skips_and_logs_info(monkeypatch, caplog):
    monkeypatch.setattr("engine.calendar_filter.is_trading_day",
                         lambda: (False, "Tahun Baru 2026 Masehi"))
    with caplog.at_level(logging.INFO):
        result = reports._holiday_skip("daily_fetch_report")
    assert result is True
    assert len(caplog.records) == 1
    assert caplog.records[0].levelno == logging.INFO


def test_reports_calendar_import_failure_fails_open_and_logs_warning(monkeypatch, caplog):
    """Same regression case, verified independently against reports.py's
    own copy of _holiday_skip -- confirms the fix was applied to both,
    not just jobs.py."""
    def _boom():
        raise ImportError("simulated broken calendar_filter import")

    monkeypatch.setattr("engine.calendar_filter.is_trading_day", _boom)
    with caplog.at_level(logging.INFO):
        result = reports._holiday_skip("auto_trade_status_report")

    assert result is False
    assert len(caplog.records) == 1
    rec = caplog.records[0]
    assert rec.levelno == logging.WARNING
    assert "auto_trade_status_report" in rec.message
