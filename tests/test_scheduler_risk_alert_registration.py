"""Regression tests for the risk-alert scheduler registration (audit H-1).

H-1: `run_hourly_risk_bundle` and `run_eod_risk_summary` were fully
implemented and imported into scheduler/__init__.py, but never handed to
`scheduler.add_job(...)`. RED/ORANGE/YELLOW alerts were written to
`market_risk_log` with sent=0 and never delivered — the operator's mental
model ("I'll be told when market risk is RED") was false.

Two layers are tested:
  1. Registration (this module's own edit): start_scheduler() must add both
     jobs, at times that don't race the job that writes market_risk_log.
  2. Idempotence (pre-existing, unmodified engine.risk_alert behavior):
     re-running either delivery job must not re-send already-sent alerts —
     this is what makes "hourly during session" safe to schedule at all
     (a missed or repeated tick can't double-alert or lose an alert).
"""
import sqlite3

import pytest
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

import scheduler as scheduler_pkg
from engine.risk_alert import route_risk_alert, send_hourly_risk_bundle, send_eod_risk_summary


@pytest.fixture
def registered_scheduler(monkeypatch):
    """start_scheduler() with every non-job-registration side effect
    (schema init, watchlist init, registry announce, actually starting
    background threads) neutralized, so only add_job calls run."""
    monkeypatch.setattr(BackgroundScheduler, "start", lambda self: None)
    monkeypatch.setattr("engine.watchlist.ensure_table", lambda *a, **k: None)
    monkeypatch.setattr("data.market_schema.ensure_market_data_schema", lambda *a, **k: None)
    monkeypatch.setattr("engine.registry_loader.announce_registry", lambda *a, **k: None)
    return scheduler_pkg.start_scheduler()


def _job_by_id(sched, job_id):
    return sched.get_job(job_id)


def _cron_minute(job):
    """Extract the integer minute from a CronTrigger job (looked up by
    field name, not position — robust to APScheduler field-order changes)."""
    field = next(f for f in job.trigger.fields if f.name == "minute")
    return field.expressions[0].first


def test_hourly_risk_bundle_registered_every_session_hour(registered_scheduler):
    """RED bundle: 7 jobs, 09:10..15:10, targeting run_hourly_risk_bundle."""
    for hour in range(9, 16):
        job = _job_by_id(registered_scheduler, f"hourly_risk_bundle_{hour:02d}10")
        assert job is not None, f"missing hourly_risk_bundle job for hour {hour}"
        assert job.func is scheduler_pkg.run_hourly_risk_bundle
        trigger_str = str(job.trigger)
        assert f"hour='{hour}'" in trigger_str
        assert "minute='10'" in trigger_str
        assert "day_of_week='mon-fri'" in trigger_str


def test_eod_risk_summary_registered_exactly_once(registered_scheduler):
    """ORANGE/YELLOW EOD summary: exactly one job, targeting run_eod_risk_summary."""
    job = _job_by_id(registered_scheduler, "eod_risk_summary")
    assert job is not None
    assert job.func is scheduler_pkg.run_eod_risk_summary
    trigger_str = str(job.trigger)
    assert "hour='16'" in trigger_str
    assert "minute='10'" in trigger_str

    matches = [j for j in registered_scheduler.get_jobs() if j.func is scheduler_pkg.run_eod_risk_summary]
    assert len(matches) == 1  # not double-registered


def test_no_duplicate_job_ids(registered_scheduler):
    """Every add_job id across the whole scheduler is unique — a duplicate id
    would silently replace the earlier registration (APScheduler default
    add_job behavior), which is exactly the kind of silent scheduler
    omission this task must not introduce."""
    ids = [j.id for j in registered_scheduler.get_jobs()]
    assert len(ids) == len(set(ids))


def test_risk_bundle_does_not_share_a_minute_with_its_data_source(registered_scheduler):
    """The job that writes market_risk_log (scheduled_multi_strategy_scan /
    _run_open_trade_monitor, both at :05) must not share a tick with the job
    that reads it — same-minute-write-then-read is the exact race class
    flagged elsewhere in this codebase (audit M-7)."""
    writer_minutes = {
        _cron_minute(j) for j in registered_scheduler.get_jobs()
        if j.func in (scheduler_pkg.scheduled_multi_strategy_scan, scheduler_pkg._run_open_trade_monitor)
    }
    bundle_minutes = {
        _cron_minute(j) for j in registered_scheduler.get_jobs()
        if j.func is scheduler_pkg.run_hourly_risk_bundle
    }
    assert writer_minutes.isdisjoint(bundle_minutes)


def test_run_hourly_risk_bundle_and_run_eod_risk_summary_are_imported_and_registered_targets():
    """Sanity: the exact two functions the audit named are the ones wired in
    (not stand-ins). `run_foreign_snapshot`, H-1's third named job, was
    removed as dead/superseded code in P0.E1.S2.T2 — see
    test_scheduler_foreign_snapshot_removal.py."""
    assert scheduler_pkg.run_hourly_risk_bundle.__name__ == "run_hourly_risk_bundle"
    assert scheduler_pkg.run_eod_risk_summary.__name__ == "run_eod_risk_summary"


# ── Idempotence (engine.risk_alert itself — unmodified, but this is what
# makes "hourly during session" a safe registration in the first place) ──

@pytest.fixture
def risk_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "risk_alert_test.db")
    monkeypatch.setattr("engine.risk_alert.DB_PATH", db_path)
    return db_path


def test_send_hourly_risk_bundle_is_idempotent(risk_db, monkeypatch, caplog):
    conn = sqlite3.connect(risk_db)
    route_risk_alert(conn, {"tier": "RED", "score": 72.0, "components": {}}, "2026-07-23", "10:00")
    conn.close()

    sent = []
    monkeypatch.setattr("engine.risk_alert.send_telegram", lambda m: sent.append(m))

    import logging
    with caplog.at_level(logging.INFO):
        send_hourly_risk_bundle("2026-07-23", "10:10")  # 1st run: delivers
        send_hourly_risk_bundle("2026-07-23", "11:10")  # 2nd run: nothing left to send

    assert len(sent) == 1
    assert "RED" in sent[0]
    assert any("Sent 1 RED alerts" in r.message for r in caplog.records)


def test_send_eod_risk_summary_is_idempotent(risk_db, monkeypatch, caplog):
    conn = sqlite3.connect(risk_db)
    route_risk_alert(conn, {"tier": "ORANGE", "score": 55.0, "components": {}}, "2026-07-23", "13:00")
    route_risk_alert(conn, {"tier": "YELLOW", "score": 40.0, "components": {}}, "2026-07-23", "14:00")
    conn.close()

    sent = []
    monkeypatch.setattr("engine.risk_alert.send_telegram", lambda m: sent.append(m))

    import logging
    with caplog.at_level(logging.INFO):
        send_eod_risk_summary("2026-07-23")  # 1st run: delivers both
        send_eod_risk_summary("2026-07-23")  # 2nd run: nothing left to send

    assert len(sent) == 1
    assert "ORANGE" in sent[0] and "YELLOW" in sent[0]
    assert any("Sent 2 ORANGE/YELLOW alerts" in r.message for r in caplog.records)


def test_send_hourly_risk_bundle_ignores_orange_yellow_tiers(risk_db, monkeypatch):
    """RED bundle must not steal ORANGE/YELLOW rows from the EOD summary —
    a pre-existing engine.risk_alert contract this registration now
    actually exercises in production for the first time."""
    conn = sqlite3.connect(risk_db)
    route_risk_alert(conn, {"tier": "ORANGE", "score": 55.0, "components": {}}, "2026-07-23", "10:00")
    conn.close()

    sent = []
    monkeypatch.setattr("engine.risk_alert.send_telegram", lambda m: sent.append(m))

    send_hourly_risk_bundle("2026-07-23", "10:10")

    assert sent == []
