"""Tests for engine.heartbeat — the scheduler dead-man's-switch core."""
from datetime import datetime, timedelta, timezone

import engine.heartbeat as hb


def _now():
    return datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc)


def test_status_fresh_within_window():
    last = (_now() - timedelta(minutes=5)).isoformat()
    assert hb.heartbeat_status(last, _now(), stale_after_min=15) == "FRESH"


def test_status_stale_beyond_window():
    last = (_now() - timedelta(minutes=20)).isoformat()
    assert hb.heartbeat_status(last, _now(), stale_after_min=15) == "STALE"


def test_status_missing_when_none():
    assert hb.heartbeat_status(None, _now(), stale_after_min=15) == "MISSING"


def test_status_missing_when_unparseable():
    assert hb.heartbeat_status("not-a-timestamp", _now(), stale_after_min=15) == "MISSING"


def test_status_exact_boundary_is_fresh():
    last = (_now() - timedelta(minutes=15)).isoformat()
    # exactly at threshold counts as fresh (strictly-greater is stale)
    assert hb.heartbeat_status(last, _now(), stale_after_min=15) == "FRESH"


def test_write_then_read_roundtrip(tmp_path):
    p = str(tmp_path / "hb.txt")
    hb.write_heartbeat(p, _now())
    assert hb.read_heartbeat(p) == _now().isoformat()


def test_read_missing_file_returns_none(tmp_path):
    assert hb.read_heartbeat(str(tmp_path / "nope.txt")) is None
