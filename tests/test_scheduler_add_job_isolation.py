"""P1-1: _add_job() is the single choke point every one of start_scheduler()'s
~20 job registrations funnels through -- isolating failures here protects all
of them without touching each call site. Never calls the real
start_scheduler() (see tests/test_scheduler_instance_getter.py's docstring
for why); exercises _add_job() directly instead.

Uses a mock scheduler whose add_job() is forced to raise, rather than trying
to provoke a real APScheduler failure (e.g. a duplicate job id) -- verified
by direct experiment that APScheduler 3.11.2's BackgroundScheduler.add_job()
does NOT raise on a duplicate id (it silently registers two jobs sharing one
id), so that would not have exercised the except path at all. A mock keeps
this test about _add_job()'s own try/except, not APScheduler's validation
rules, which could change across versions."""
from unittest.mock import MagicMock, patch

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

import scheduler as sched


def _dummy():
    pass


def _failing_scheduler():
    s = MagicMock()
    s.add_job.side_effect = RuntimeError("boom: bad trigger config")
    return s


def test_bad_registration_does_not_raise():
    sched._add_job(_failing_scheduler(), _dummy, CronTrigger(hour=1), id="bad_job")


def test_bad_registration_does_not_block_the_next_good_one():
    s = BackgroundScheduler()
    bad = _failing_scheduler()
    sched._add_job(bad, _dummy, CronTrigger(hour=1), id="bad_job")  # fails, isolated
    sched._add_job(s, _dummy, CronTrigger(hour=3), id="second_job")  # real scheduler, must register
    ids = {j.id for j in s.get_jobs()}
    assert ids == {"second_job"}


def test_bad_registration_alerts_via_telegram_with_job_id():
    with patch("scheduler.send_telegram") as mock_send:
        sched._add_job(_failing_scheduler(), _dummy, CronTrigger(hour=1), id="bad_job")
    mock_send.assert_called_once()
    assert "bad_job" in mock_send.call_args[0][0]


def test_alert_failure_itself_does_not_propagate():
    """The inner send_telegram call is itself best-effort -- if Telegram is
    down too, _add_job must still not raise."""
    with patch("scheduler.send_telegram", side_effect=RuntimeError("telegram down")):
        sched._add_job(_failing_scheduler(), _dummy, CronTrigger(hour=1), id="bad_job")


def test_good_registration_never_touches_telegram():
    s = BackgroundScheduler()
    with patch("scheduler.send_telegram") as mock_send:
        sched._add_job(s, _dummy, CronTrigger(hour=1), id="clean_job")
    mock_send.assert_not_called()
    assert {j.id for j in s.get_jobs()} == {"clean_job"}
