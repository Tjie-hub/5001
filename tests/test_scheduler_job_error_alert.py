"""Tests for the EVENT_JOB_ERROR alert added 2026-07-28 — closes the gap where
an uncaught in-process APScheduler job exception was invisible except via log
grep (the heartbeat only proves the process, not any individual job, is alive).
"""
from unittest.mock import MagicMock

import scheduler as sched


def test_format_job_error_alert_uses_job_name_when_given():
    msg = sched.format_job_error_alert("eod_trade_plan", "EOD Trade Plan 16:40",
                                       ValueError("boom"))
    assert "EOD Trade Plan 16:40" in msg
    assert "eod_trade_plan" in msg
    assert "boom" in msg
    assert "Scheduler Job Failed" in msg


def test_format_job_error_alert_falls_back_to_job_id_when_no_name():
    msg = sched.format_job_error_alert("some_job", None, RuntimeError("x"))
    assert "some_job" in msg


def test_format_job_error_alert_truncates_long_exception_text():
    msg = sched.format_job_error_alert("j", "J", ValueError("x" * 500))
    assert len(msg) < 500 + 200   # exception body capped at 300 chars


def test_job_error_listener_sends_telegram_alert(monkeypatch):
    sent = []
    monkeypatch.setattr(sched, "send_telegram", lambda text: sent.append(text))

    fake_job = MagicMock()
    fake_job.name = "EOD Trade Plan 16:40"
    fake_scheduler = MagicMock()
    fake_scheduler.get_job.return_value = fake_job

    listener = sched._make_job_error_listener(fake_scheduler)
    event = MagicMock(job_id="eod_trade_plan", exception=ValueError("boom"))
    listener(event)

    assert len(sent) == 1
    assert "EOD Trade Plan 16:40" in sent[0]
    assert "boom" in sent[0]


def test_job_error_listener_survives_send_telegram_failure(monkeypatch):
    def _raise(text):
        raise ConnectionError("network down")
    monkeypatch.setattr(sched, "send_telegram", _raise)

    fake_scheduler = MagicMock()
    fake_scheduler.get_job.return_value = None
    listener = sched._make_job_error_listener(fake_scheduler)
    event = MagicMock(job_id="some_job", exception=RuntimeError("oops"))

    listener(event)   # must not raise — a broken alert must never crash the scheduler


def test_job_error_listener_handles_get_job_lookup_failure(monkeypatch):
    sent = []
    monkeypatch.setattr(sched, "send_telegram", lambda text: sent.append(text))

    fake_scheduler = MagicMock()
    fake_scheduler.get_job.side_effect = Exception("scheduler shutting down")
    listener = sched._make_job_error_listener(fake_scheduler)
    event = MagicMock(job_id="some_job", exception=RuntimeError("oops"))
    listener(event)

    assert len(sent) == 1
    assert "some_job" in sent[0]   # falls back to job_id when name lookup fails


def test_format_job_error_alert_omits_suppressed_line_by_default():
    msg = sched.format_job_error_alert("j", "J", ValueError("x"))
    assert "suppressed" not in msg


def test_format_job_error_alert_reports_suppressed_count():
    msg = sched.format_job_error_alert("j", "J", ValueError("x"), suppressed=4)
    assert "+4 more failures suppressed since last alert" in msg


def test_format_job_error_alert_singular_suppressed_count():
    msg = sched.format_job_error_alert("j", "J", ValueError("x"), suppressed=1)
    assert "+1 more failure suppressed since last alert" in msg


class _FakeClock:
    """Deterministic, manually-advanced clock — no real sleep, no flakiness."""
    def __init__(self, start=0.0):
        self.now = start

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class TestJobErrorRateLimiter:
    """RC1 fix R-2: prevent repeated identical Telegram alerts for a job stuck
    failing on every tick, while preserving first-failure visibility."""

    def test_first_failure_always_alerts(self):
        rl = sched.JobErrorRateLimiter(cooldown_s=3600, clock=_FakeClock())
        should, suppressed = rl.should_alert("job_a")
        assert should is True and suppressed == 0

    def test_repeat_failure_within_cooldown_is_suppressed(self):
        clock = _FakeClock()
        rl = sched.JobErrorRateLimiter(cooldown_s=3600, clock=clock)
        rl.should_alert("job_a")             # first: alerts
        clock.advance(10)
        should, _ = rl.should_alert("job_a")  # 10s later: still in cooldown
        assert should is False

    def test_alert_resumes_after_cooldown_expires_with_suppressed_count(self):
        clock = _FakeClock()
        rl = sched.JobErrorRateLimiter(cooldown_s=100, clock=clock)
        rl.should_alert("job_a")                      # 1st: alerts
        clock.advance(10); rl.should_alert("job_a")    # suppressed #1
        clock.advance(10); rl.should_alert("job_a")    # suppressed #2
        clock.advance(200)                             # past cooldown
        should, suppressed = rl.should_alert("job_a")
        assert should is True
        assert suppressed == 2

    def test_suppressed_counter_resets_after_it_fires(self):
        clock = _FakeClock()
        rl = sched.JobErrorRateLimiter(cooldown_s=100, clock=clock)
        rl.should_alert("job_a")
        clock.advance(10); rl.should_alert("job_a")
        clock.advance(200); should, suppressed = rl.should_alert("job_a")
        assert should is True and suppressed == 1
        # immediately after — no time has passed, still within the new cooldown
        should2, _ = rl.should_alert("job_a")
        assert should2 is False

    def test_different_job_ids_are_rate_limited_independently(self):
        clock = _FakeClock()
        rl = sched.JobErrorRateLimiter(cooldown_s=3600, clock=clock)
        should_a, _ = rl.should_alert("job_a")
        should_b, _ = rl.should_alert("job_b")
        assert should_a is True and should_b is True   # neither suppresses the other

    def test_bounded_memory_one_entry_per_distinct_job_id(self):
        clock = _FakeClock()
        rl = sched.JobErrorRateLimiter(cooldown_s=3600, clock=clock)
        for _ in range(1000):
            rl.should_alert("job_a")   # same job, hammered repeatedly
            clock.advance(1)
        assert len(rl._last_alert) == 1
        assert len(rl._suppressed) <= 1

    def test_default_cooldown_is_one_hour(self):
        assert sched.JobErrorRateLimiter().cooldown_s == 3600.0


class TestJobErrorListenerRateLimiting:
    """Integration: the listener actually gates send_telegram through the limiter."""

    def _listener(self, monkeypatch, clock, cooldown_s=3600):
        sent = []
        monkeypatch.setattr(sched, "send_telegram", lambda text: sent.append(text))
        fake_scheduler = MagicMock()
        fake_scheduler.get_job.return_value = None
        limiter = sched.JobErrorRateLimiter(cooldown_s=cooldown_s, clock=clock)
        listener = sched._make_job_error_listener(fake_scheduler, rate_limiter=limiter)
        return listener, sent

    def test_repeated_identical_failures_send_only_one_telegram_alert(self, monkeypatch):
        clock = _FakeClock()
        listener, sent = self._listener(monkeypatch, clock)
        event = MagicMock(job_id="scheduled_multi_strategy_scan", exception=RuntimeError("boom"))
        for _ in range(5):                 # 5x/day job failing on every tick
            listener(event)
            clock.advance(1)
        assert len(sent) == 1              # no duplicate Telegram spam

    def test_alert_resurfaces_after_cooldown_with_suppressed_count(self, monkeypatch):
        clock = _FakeClock()
        listener, sent = self._listener(monkeypatch, clock, cooldown_s=100)
        event = MagicMock(job_id="job_a", exception=RuntimeError("boom"))
        listener(event)                    # sends
        clock.advance(10); listener(event)  # suppressed
        clock.advance(10); listener(event)  # suppressed
        clock.advance(200); listener(event)  # cooldown expired -> sends again
        assert len(sent) == 2
        assert "+2 more failures suppressed since last alert" in sent[1]

    def test_first_failure_still_alerts_immediately(self, monkeypatch):
        clock = _FakeClock()
        listener, sent = self._listener(monkeypatch, clock)
        listener(MagicMock(job_id="job_a", exception=RuntimeError("first ever failure")))
        assert len(sent) == 1
        assert "first ever failure" in sent[0]
