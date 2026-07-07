"""The external watchdog alarms on STALE/MISSING, stays silent on FRESH."""
from datetime import datetime, timedelta, timezone

import scripts.check_scheduler_heartbeat as chk


def _write(path, dt):
    from engine.heartbeat import write_heartbeat
    write_heartbeat(path, dt)


def test_fresh_does_not_alarm(tmp_path, monkeypatch):
    alarms = []
    monkeypatch.setattr(chk, "send_telegram", lambda m: alarms.append(m))
    p = str(tmp_path / "hb.txt")
    _write(p, datetime.now(timezone.utc) - timedelta(minutes=3))
    rc = chk.check(path=p, stale_after_min=15)
    assert rc == 0
    assert alarms == []


def test_stale_alarms(tmp_path, monkeypatch):
    alarms = []
    monkeypatch.setattr(chk, "send_telegram", lambda m: alarms.append(m))
    p = str(tmp_path / "hb.txt")
    _write(p, datetime.now(timezone.utc) - timedelta(minutes=40))
    rc = chk.check(path=p, stale_after_min=15)
    assert rc == 1
    assert len(alarms) == 1
    assert "STALE" in alarms[0] or "heartbeat" in alarms[0].lower()


def test_missing_alarms(tmp_path, monkeypatch):
    alarms = []
    monkeypatch.setattr(chk, "send_telegram", lambda m: alarms.append(m))
    rc = chk.check(path=str(tmp_path / "nope.txt"), stale_after_min=15)
    assert rc == 1
    assert len(alarms) == 1
