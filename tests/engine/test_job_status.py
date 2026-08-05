"""Tests for engine.job_status — the Production Status Registry (Phase 1)."""
import sqlite3


def test_ensure_job_status_table_creates_schema(tmp_path):
    from engine.job_status import ensure_job_status_table

    conn = sqlite3.connect(str(tmp_path / "test.db"))
    ensure_job_status_table(conn)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(job_execution_log)")}
    expected = {
        "id", "run_id", "job_name", "run_type", "started_at", "completed_at",
        "duration_ms", "status", "records_processed", "telegram_sent",
        "error_message", "retry_count", "engine_version",
    }
    assert expected <= cols
    conn.close()


def test_ensure_job_status_table_is_idempotent(tmp_path):
    from engine.job_status import ensure_job_status_table

    conn = sqlite3.connect(str(tmp_path / "test.db"))
    ensure_job_status_table(conn)
    ensure_job_status_table(conn)  # must not raise
    conn.close()


def test_engine_version_returns_string_or_none():
    from engine.job_status import _engine_version

    v = _engine_version()
    assert v is None or isinstance(v, str)


def test_engine_version_fail_soft_on_subprocess_error(monkeypatch):
    import engine.job_status as js

    def _boom(*a, **k):
        raise OSError("git not found")

    monkeypatch.setattr(js.subprocess, "run", _boom)
    assert js._engine_version() is None


def test_track_job_records_success(tmp_path):
    from engine.job_status import track_job

    db_path = str(tmp_path / "test.db")
    with track_job("unit_test_job", db_path=db_path) as handle:
        handle.records_processed = 7
        handle.telegram_sent = True

    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT job_name, run_type, status, records_processed, telegram_sent, "
        "error_message, completed_at, duration_ms FROM job_execution_log"
    ).fetchone()
    conn.close()
    (job_name, run_type, status, records_processed, telegram_sent,
     error_message, completed_at, duration_ms) = row
    assert job_name == "unit_test_job"
    assert run_type == "scheduled"
    assert status == "success"
    assert records_processed == 7
    assert telegram_sent == 1
    assert error_message is None
    assert completed_at is not None
    assert duration_ms is not None and duration_ms >= 0


def test_track_job_records_failure_and_reraises(tmp_path):
    import pytest
    from engine.job_status import track_job

    db_path = str(tmp_path / "test.db")
    with pytest.raises(ValueError, match="boom"):
        with track_job("unit_test_job", db_path=db_path):
            raise ValueError("boom")

    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT status, error_message FROM job_execution_log").fetchone()
    conn.close()
    assert row == ("failed", "boom")


def test_current_job_returns_none_outside_track_job():
    from engine.job_status import current_job

    assert current_job() is None


def test_current_job_returns_handle_inside_track_job(tmp_path):
    from engine.job_status import current_job, track_job

    db_path = str(tmp_path / "test.db")
    with track_job("unit_test_job", db_path=db_path) as handle:
        assert current_job() is handle
    assert current_job() is None


def test_track_job_records_skipped_status(tmp_path):
    from engine.job_status import track_job

    db_path = str(tmp_path / "test.db")
    with track_job("unit_test_job", db_path=db_path) as handle:
        handle.mark_skipped("holiday")

    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT status, error_message FROM job_execution_log").fetchone()
    conn.close()
    assert row == ("skipped", "holiday")


def test_mark_skipped_defaults_reason_when_none_given(tmp_path):
    from engine.job_status import track_job

    db_path = str(tmp_path / "test.db")
    with track_job("unit_test_job", db_path=db_path) as handle:
        handle.mark_skipped()

    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT status, error_message FROM job_execution_log").fetchone()
    conn.close()
    assert row == ("skipped", "skipped")


def test_skipped_job_still_persists_records_processed(tmp_path):
    """mark_skipped() and records_processed are independent -- a job can report
    e.g. 0 records and a skip reason in the same run."""
    from engine.job_status import track_job

    db_path = str(tmp_path / "test.db")
    with track_job("unit_test_job", db_path=db_path) as handle:
        handle.records_processed = 0
        handle.mark_skipped("no candidates")

    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT status, error_message, records_processed FROM job_execution_log"
    ).fetchone()
    conn.close()
    assert row == ("skipped", "no candidates", 0)


def test_track_job_records_manual_run_type(tmp_path):
    from engine.job_status import track_job

    db_path = str(tmp_path / "test.db")
    with track_job("unit_test_job", run_type="manual", db_path=db_path):
        pass

    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT run_type FROM job_execution_log").fetchone()
    conn.close()
    assert row == ("manual",)


def test_track_job_records_backfill_run_type_and_retry_count(tmp_path):
    from engine.job_status import track_job

    db_path = str(tmp_path / "test.db")
    with track_job("unit_test_job", run_type="backfill", retry_count=2, db_path=db_path):
        pass

    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT run_type, retry_count FROM job_execution_log").fetchone()
    conn.close()
    assert row == ("backfill", 2)


def test_restart_safety_orphaned_running_row_does_not_block_next_run(tmp_path):
    """Simulates a process crash mid-job: a 'running' row is left behind with
    no completed_at. A subsequent execution of the SAME job_name must still
    insert its own row and finalize normally -- run_id (not job_name) is the
    uniqueness anchor, so the orphan never collides."""
    from engine.job_status import ensure_job_status_table, track_job

    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    ensure_job_status_table(conn)
    conn.execute(
        "INSERT INTO job_execution_log (run_id, job_name, run_type, started_at, status) "
        "VALUES ('orphan-run-id', 'unit_test_job', 'scheduled', '2026-08-01 09:00:00', 'running')"
    )
    conn.commit()
    conn.close()

    with track_job("unit_test_job", db_path=db_path):
        pass

    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT run_id, status FROM job_execution_log WHERE job_name='unit_test_job' "
        "ORDER BY id"
    ).fetchall()
    conn.close()
    assert rows[0] == ("orphan-run-id", "running")   # untouched by the new run
    assert rows[1][0] != "orphan-run-id"
    assert rows[1][1] == "success"


def test_wrap_scheduled_tracks_a_call_and_returns_value(tmp_path):
    from engine.job_status import wrap_scheduled

    db_path = str(tmp_path / "test.db")
    calls = []

    def _job(x, y=2):
        calls.append((x, y))
        return x + y

    wrapped = wrap_scheduled(_job, "unit_test_job", db_path=db_path)
    result = wrapped(5, y=3)

    assert result == 8
    assert calls == [(5, 3)]
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT job_name, run_type, status FROM job_execution_log").fetchone()
    conn.close()
    assert row == ("unit_test_job", "scheduled", "success")


def test_wrap_scheduled_propagates_exceptions(tmp_path):
    import pytest
    from engine.job_status import wrap_scheduled

    db_path = str(tmp_path / "test.db")

    def _job():
        raise RuntimeError("job blew up")

    wrapped = wrap_scheduled(_job, "unit_test_job", db_path=db_path)

    with pytest.raises(RuntimeError, match="job blew up"):
        wrapped()

    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT status, error_message FROM job_execution_log").fetchone()
    conn.close()
    assert row == ("failed", "job blew up")


def test_wrap_scheduled_accepts_run_type_override(tmp_path):
    from engine.job_status import wrap_scheduled

    db_path = str(tmp_path / "test.db")
    wrapped = wrap_scheduled(lambda: None, "unit_test_job", run_type="manual", db_path=db_path)
    wrapped()

    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT run_type FROM job_execution_log").fetchone()
    conn.close()
    assert row == ("manual",)


def _seed_row(db_path, **overrides):
    from engine.job_status import ensure_job_status_table

    defaults = dict(
        run_id=None, job_name="job_a", run_type="scheduled",
        started_at="2026-08-01 09:00:00", completed_at="2026-08-01 09:00:01",
        duration_ms=1000, status="success", records_processed=None,
        telegram_sent=0, error_message=None, retry_count=0, engine_version="abc123",
    )
    defaults.update(overrides)
    if defaults["run_id"] is None:
        import uuid
        defaults["run_id"] = uuid.uuid4().hex

    conn = sqlite3.connect(db_path)
    ensure_job_status_table(conn)
    conn.execute(
        "INSERT INTO job_execution_log (run_id, job_name, run_type, started_at, "
        "completed_at, duration_ms, status, records_processed, telegram_sent, "
        "error_message, retry_count, engine_version) VALUES "
        "(:run_id,:job_name,:run_type,:started_at,:completed_at,:duration_ms,"
        ":status,:records_processed,:telegram_sent,:error_message,:retry_count,"
        ":engine_version)",
        defaults,
    )
    conn.commit()
    conn.close()


def test_get_latest_job_status_for_single_job(tmp_path):
    from engine.job_status import get_latest_job_status

    db_path = str(tmp_path / "test.db")
    _seed_row(db_path, job_name="job_a", started_at="2026-08-01 09:00:00")
    _seed_row(db_path, job_name="job_a", started_at="2026-08-02 09:00:00")

    latest = get_latest_job_status("job_a", db_path=db_path)
    assert latest["started_at"] == "2026-08-02 09:00:00"


def test_get_latest_job_status_returns_none_for_unknown_job(tmp_path):
    from engine.job_status import get_latest_job_status

    db_path = str(tmp_path / "test.db")
    _seed_row(db_path, job_name="job_a")

    assert get_latest_job_status("no_such_job", db_path=db_path) is None


def test_get_latest_job_status_across_all_jobs(tmp_path):
    from engine.job_status import get_latest_job_status

    db_path = str(tmp_path / "test.db")
    _seed_row(db_path, job_name="job_a", started_at="2026-08-01 09:00:00")
    _seed_row(db_path, job_name="job_a", started_at="2026-08-02 09:00:00")
    _seed_row(db_path, job_name="job_b", started_at="2026-08-01 10:00:00")

    latest = get_latest_job_status(db_path=db_path)
    by_job = {row["job_name"]: row["started_at"] for row in latest}
    assert by_job == {"job_a": "2026-08-02 09:00:00", "job_b": "2026-08-01 10:00:00"}


def test_get_last_success_ignores_failed_rows(tmp_path):
    from engine.job_status import get_last_success

    db_path = str(tmp_path / "test.db")
    _seed_row(db_path, job_name="job_a", status="success", started_at="2026-08-01 09:00:00")
    _seed_row(db_path, job_name="job_a", status="failed", started_at="2026-08-02 09:00:00")

    last_success = get_last_success("job_a", db_path=db_path)
    assert last_success["started_at"] == "2026-08-01 09:00:00"


def test_get_last_success_returns_none_when_never_succeeded(tmp_path):
    from engine.job_status import get_last_success

    db_path = str(tmp_path / "test.db")
    _seed_row(db_path, job_name="job_a", status="failed")

    assert get_last_success("job_a", db_path=db_path) is None


def test_get_failed_jobs_filters_by_status_and_since(tmp_path):
    from engine.job_status import get_failed_jobs

    db_path = str(tmp_path / "test.db")
    _seed_row(db_path, job_name="job_a", status="failed", started_at="2026-08-01 09:00:00")
    _seed_row(db_path, job_name="job_b", status="failed", started_at="2026-08-03 09:00:00")
    _seed_row(db_path, job_name="job_c", status="success", started_at="2026-08-03 09:00:00")

    all_failed = get_failed_jobs(db_path=db_path)
    assert {r["job_name"] for r in all_failed} == {"job_a", "job_b"}

    recent_failed = get_failed_jobs(since="2026-08-02 00:00:00", db_path=db_path)
    assert {r["job_name"] for r in recent_failed} == {"job_b"}


def test_get_jobs_since_returns_all_statuses_from_cutoff(tmp_path):
    from engine.job_status import get_jobs_since

    db_path = str(tmp_path / "test.db")
    _seed_row(db_path, job_name="job_a", status="success", started_at="2026-08-01 09:00:00")
    _seed_row(db_path, job_name="job_b", status="failed", started_at="2026-08-03 09:00:00")

    rows = get_jobs_since("2026-08-02 00:00:00", db_path=db_path)
    assert [r["job_name"] for r in rows] == ["job_b"]


def test_get_running_jobs_returns_only_running_status(tmp_path):
    from engine.job_status import get_running_jobs

    db_path = str(tmp_path / "test.db")
    _seed_row(db_path, job_name="job_a", status="running",
              started_at="2026-08-01 09:00:00", completed_at=None)
    _seed_row(db_path, job_name="job_b", status="success", started_at="2026-08-01 09:00:00")

    running = get_running_jobs(db_path=db_path)
    assert {r["job_name"] for r in running} == {"job_a"}


def test_get_running_jobs_empty_when_none_running(tmp_path):
    from engine.job_status import get_running_jobs

    db_path = str(tmp_path / "test.db")
    _seed_row(db_path, job_name="job_a", status="success")

    assert get_running_jobs(db_path=db_path) == []


def test_get_running_jobs_newest_first(tmp_path):
    from engine.job_status import get_running_jobs

    db_path = str(tmp_path / "test.db")
    _seed_row(db_path, job_name="job_a", status="running", started_at="2026-08-01 09:00:00")
    _seed_row(db_path, job_name="job_b", status="running", started_at="2026-08-02 09:00:00")

    running = get_running_jobs(db_path=db_path)
    assert [r["job_name"] for r in running] == ["job_b", "job_a"]


def test_get_recent_jobs_respects_limit(tmp_path):
    from engine.job_status import get_recent_jobs

    db_path = str(tmp_path / "test.db")
    for i in range(5):
        _seed_row(db_path, job_name=f"job_{i}", started_at=f"2026-08-0{i+1} 09:00:00")

    recent = get_recent_jobs(limit=3, db_path=db_path)
    assert len(recent) == 3
    # newest first
    assert [r["job_name"] for r in recent] == ["job_4", "job_3", "job_2"]


def test_get_recent_jobs_default_limit_is_reasonable(tmp_path):
    from engine.job_status import get_recent_jobs

    db_path = str(tmp_path / "test.db")
    for i in range(120):
        _seed_row(db_path, job_name=f"job_{i}", started_at=f"2026-08-01 {i%24:02d}:00:00")

    recent = get_recent_jobs(db_path=db_path)
    assert 0 < len(recent) <= 100  # some sane cap, not unbounded


def test_get_recent_jobs_empty_db_returns_empty_list(tmp_path):
    from engine.job_status import get_recent_jobs

    db_path = str(tmp_path / "test.db")
    assert get_recent_jobs(db_path=db_path) == []


def test_get_status_summary_counts_by_status(tmp_path):
    from engine.job_status import get_status_summary

    db_path = str(tmp_path / "test.db")
    _seed_row(db_path, job_name="job_a", status="success")
    _seed_row(db_path, job_name="job_b", status="success")
    _seed_row(db_path, job_name="job_c", status="failed")
    _seed_row(db_path, job_name="job_d", status="skipped")
    _seed_row(db_path, job_name="job_e", status="running")

    summary = get_status_summary(db_path=db_path)
    assert summary == {"total": 5, "success": 2, "failed": 1, "skipped": 1, "running": 1}


def test_get_status_summary_empty_db_all_zero(tmp_path):
    from engine.job_status import get_status_summary

    db_path = str(tmp_path / "test.db")
    summary = get_status_summary(db_path=db_path)
    assert summary == {"total": 0, "success": 0, "failed": 0, "skipped": 0, "running": 0}
