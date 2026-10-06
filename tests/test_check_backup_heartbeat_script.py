"""P1-2: the backup/restore-drill dead-man's-switch alarms when either cron's
log file hasn't been touched within its cadence, stays silent when both are
fresh. Mirrors tests/test_check_heartbeat_script.py's structure for the
scheduler heartbeat watchdog."""
import os
import time
from datetime import datetime, timedelta, timezone

import scripts.check_backup_heartbeat as chk


def _touch(path, dt):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write("EXIT job rc=0\n")
    ts = dt.timestamp()
    os.utime(path, (ts, ts))


def test_all_fresh_does_not_alarm(tmp_path, monkeypatch):
    alarms = []
    monkeypatch.setattr(chk, "send_telegram", lambda m, **kw: alarms.append(m))
    backup_log = str(tmp_path / "cron_db_backup.log")
    research_log = str(tmp_path / "cron_db_backup_research.log")
    drill_log = str(tmp_path / "cron_db_restore_drill.log")
    now = datetime.now(timezone.utc)
    _touch(backup_log, now - timedelta(hours=2))
    _touch(research_log, now - timedelta(hours=2))
    _touch(drill_log, now - timedelta(days=1))
    rc = chk.check(checks=[("nightly DB backup", backup_log, 26 * 60),
                            ("nightly research.db backup (R-5)", research_log, 26 * 60),
                            ("weekly restore drill", drill_log, 8 * 24 * 60)],
                    now=now)
    assert rc == 0
    assert alarms == []


def test_default_checks_cover_all_three_backup_jobs():
    names = [name for name, _, _ in chk.DEFAULT_CHECKS]
    assert names == ["nightly DB backup", "nightly research.db backup (R-5)",
                      "weekly restore drill"]


def test_stale_backup_alarms(tmp_path, monkeypatch):
    alarms = []
    monkeypatch.setattr(chk, "send_telegram", lambda m, **kw: alarms.append(m))
    backup_log = str(tmp_path / "cron_db_backup.log")
    now = datetime.now(timezone.utc)
    _touch(backup_log, now - timedelta(hours=40))  # > 26h threshold
    rc = chk.check(checks=[("nightly DB backup", backup_log, 26 * 60)], now=now)
    assert rc == 1
    assert len(alarms) == 1
    assert "nightly DB backup" in alarms[0] and "STALE" in alarms[0]


def test_missing_restore_drill_log_alarms(tmp_path, monkeypatch):
    alarms = []
    monkeypatch.setattr(chk, "send_telegram", lambda m, **kw: alarms.append(m))
    drill_log = str(tmp_path / "never_ran.log")  # never created
    rc = chk.check(checks=[("weekly restore drill", drill_log, 8 * 24 * 60)],
                    now=datetime.now(timezone.utc))
    assert rc == 1
    assert len(alarms) == 1
    assert "weekly restore drill" in alarms[0] and "MISSING" in alarms[0]


def test_each_stale_job_alarms_separately(tmp_path, monkeypatch):
    """Both jobs stale -> two distinct alarms, not one combined/silent one."""
    alarms = []
    monkeypatch.setattr(chk, "send_telegram", lambda m, **kw: alarms.append(m))
    backup_log = str(tmp_path / "cron_db_backup.log")
    drill_log = str(tmp_path / "cron_db_restore_drill.log")
    now = datetime.now(timezone.utc)
    _touch(backup_log, now - timedelta(hours=40))
    _touch(drill_log, now - timedelta(days=10))
    rc = chk.check(checks=[("nightly DB backup", backup_log, 26 * 60),
                            ("weekly restore drill", drill_log, 8 * 24 * 60)],
                    now=now)
    assert rc == 1
    assert len(alarms) == 2


def test_alert_failure_does_not_crash_the_check(tmp_path, monkeypatch):
    monkeypatch.setattr(chk, "send_telegram",
                        lambda m, **kw: (_ for _ in ()).throw(RuntimeError("down")))
    backup_log = str(tmp_path / "cron_db_backup.log")
    now = datetime.now(timezone.utc)
    _touch(backup_log, now - timedelta(hours=40))
    rc = chk.check(checks=[("nightly DB backup", backup_log, 26 * 60)], now=now)
    assert rc == 1  # still reports failure via exit code even if alert itself failed
