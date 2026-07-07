"""The in-app heartbeat job must stamp a fresh, parseable timestamp."""
from datetime import datetime, timezone

import engine.heartbeat as hb
from scheduler.jobs import run_scheduler_heartbeat, HEARTBEAT_PATH


def test_run_scheduler_heartbeat_writes_fresh(tmp_path, monkeypatch):
    p = str(tmp_path / "hb.txt")
    monkeypatch.setattr("scheduler.jobs.HEARTBEAT_PATH", p)
    run_scheduler_heartbeat()
    last = hb.read_heartbeat(p)
    assert last is not None
    assert hb.heartbeat_status(last, datetime.now(timezone.utc)) == "FRESH"
