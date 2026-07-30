"""P0.E2.S3.T3 -- calendar-year-missing alarm (L-5).

Audit L-5: the IDX holiday calendar (engine/calendar_filter.py) is
hand-curated per year and hardcoded through 2026 only. From 2027-01-01,
is_trading_day() would silently treat every weekday as a trading day with
no holidays, and BI Rate/FOMC blackout windows for 2027 would not exist
either. check_calendar_year_coverage() cannot fix the gap -- the calendar
can't be derived programmatically, only hand-updated -- so it surfaces the
gap in December, before it becomes a live problem on Jan 1.
scheduler/jobs.py's run_calendar_coverage_check wires this into a
December-only daily cron job (scheduler/__init__.py).
"""
from datetime import date

import scheduler.jobs as jobs
from engine.calendar_filter import check_calendar_year_coverage, is_trading_day


# ── check_calendar_year_coverage() -- pure function ─────────────────────────

def test_no_alarm_outside_december():
    """Normal operation: any month but December returns None -- nothing
    actionable that early, regardless of next year's coverage state."""
    assert check_calendar_year_coverage(date(2026, 6, 15)) is None
    assert check_calendar_year_coverage(date(2026, 11, 30)) is None


def test_no_alarm_in_december_when_next_year_present():
    """Normal operation: December 2025 checks 2026 coverage, which exists
    in this repo's real calendar data -- no alarm."""
    assert check_calendar_year_coverage(date(2025, 12, 15)) is None


def test_alarm_in_december_when_next_year_missing():
    """The regression case the audit describes: December 2026 checks 2027
    coverage, which does not exist in this repo's real calendar data --
    returns a non-empty warning naming the missing year."""
    msg = check_calendar_year_coverage(date(2026, 12, 1))
    assert msg is not None
    assert "2027" in msg


def test_alarm_message_names_the_missing_dict():
    """Actionable, not just 'something is wrong': names the exact
    constant a maintainer needs to add."""
    msg = check_calendar_year_coverage(date(2026, 12, 1))
    assert "IDX_MARKET_HOLIDAYS_2027" in msg


def test_check_is_deterministic_same_input_same_output():
    """Duplicate-alarm-prevention control: the check is a pure function of
    `today` -- calling it twice with the same date always returns the same
    result, so nothing internal could cause repeated evaluations to drift
    or double-fire."""
    d = date(2026, 12, 1)
    assert check_calendar_year_coverage(d) == check_calendar_year_coverage(d)


def test_december_31_still_checks_next_year():
    """Boundary: the alarm window is the whole month, not just Dec 1."""
    msg = check_calendar_year_coverage(date(2026, 12, 31))
    assert msg is not None and "2027" in msg


def test_january_1_of_missing_year_no_longer_triggers_this_alarm():
    """Boundary: once the missing year actually arrives, this December-
    warning check no longer applies (is_trading_day()'s existing,
    unrelated fail-open behavior for un-covered years is out of this
    task's scope -- L-5 is the advance-warning alarm, not a runtime
    enforcement mechanism)."""
    assert check_calendar_year_coverage(date(2027, 1, 1)) is None


# ── run_calendar_coverage_check() -- scheduled job ──────────────────────────

def test_job_sends_telegram_when_calendar_missing(monkeypatch):
    monkeypatch.setattr(
        "engine.calendar_filter.check_calendar_year_coverage",
        lambda today=None: "IDX market holiday calendar for 2027 is not populated",
    )
    sent = []
    monkeypatch.setattr(jobs, "send_telegram", lambda msg: sent.append(msg))

    jobs.run_calendar_coverage_check()

    assert len(sent) == 1
    assert "2027" in sent[0]


def test_job_sends_nothing_when_calendar_present(monkeypatch):
    """False-positive / duplicate-alarm-prevention control: no Telegram
    call at all when the check returns None."""
    monkeypatch.setattr(
        "engine.calendar_filter.check_calendar_year_coverage",
        lambda today=None: None,
    )
    sent = []
    monkeypatch.setattr(jobs, "send_telegram", lambda msg: sent.append(msg))

    jobs.run_calendar_coverage_check()

    assert sent == []


def test_job_sends_at_most_one_message_per_invocation(monkeypatch):
    """Duplicate-alarm-prevention: the job body has no loop or retry that
    could fire multiple alerts from a single scheduled run."""
    monkeypatch.setattr(
        "engine.calendar_filter.check_calendar_year_coverage",
        lambda today=None: "IDX market holiday calendar for 2027 is not populated",
    )
    sent = []
    monkeypatch.setattr(jobs, "send_telegram", lambda msg: sent.append(msg))

    jobs.run_calendar_coverage_check()

    assert len(sent) == 1


def test_job_does_not_crash_scheduler_on_unexpected_error(monkeypatch):
    """Startup/runtime-edge-case control: an unexpected exception inside
    the check (e.g. a future refactor breaking the import) is caught and
    logged, not raised -- matching every other job in this file's
    'never let this crash the scheduler' convention."""
    def _boom(today=None):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr("engine.calendar_filter.check_calendar_year_coverage", _boom)
    sent = []
    monkeypatch.setattr(jobs, "send_telegram", lambda msg: sent.append(msg))

    jobs.run_calendar_coverage_check()  # must not raise

    assert sent == []


# ── Regression: existing calendar behavior unchanged ────────────────────────

def test_existing_2026_holiday_detection_unaffected():
    """Regression: is_trading_day()'s real, already-covered 2026 holiday
    data is untouched by this task -- New Year's Day 2026 is still
    correctly detected as a non-trading day."""
    is_open, reason = is_trading_day(date(2026, 1, 1))
    assert is_open is False
    assert "Tahun Baru" in reason


def test_existing_2026_trading_day_unaffected():
    """Regression: an ordinary 2026 weekday still resolves as a trading
    day, unchanged."""
    is_open, reason = is_trading_day(date(2026, 6, 15))  # Monday
    assert is_open is True
