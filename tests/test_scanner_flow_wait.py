"""2026-10-15: the 16:00 daily scan filters BUY signals on stockbit_flow, but the 16:05 flow fetch only saves all
names at its end (~16:27), so at 16:00 the table held the 15:37 intraday snapshot. The scan now waits for rows
written at or after 15:50 (the post-close fetch), fail-open after a timeout."""
from datetime import datetime

from data.db import connect
from scheduler import scanner


def _db(tmp_path, stamp):
    p = tmp_path / "wf.db"
    c = connect(str(p))
    c.execute("CREATE TABLE stockbit_flow (ticker TEXT, trade_date TEXT, buy_lot INT, sell_lot INT, updated_at TEXT)")
    if stamp:
        c.execute("INSERT INTO stockbit_flow VALUES ('TOWR', '2026-10-15', 1, 1, ?)", (stamp,))
    c.commit()
    c.close()
    return str(p)


def test_returns_at_once_when_post_close_rows_exist(tmp_path):
    slept = []
    ok = scanner._wait_for_post_close_flow(_db(tmp_path, "2026-10-15 16:27"), today="2026-10-15",
                                           timeout_s=60, poll_s=10, sleep=slept.append)
    assert ok and slept == []


def test_waits_on_intraday_snapshot_then_gives_up_fail_open(tmp_path):
    slept = []
    ok = scanner._wait_for_post_close_flow(_db(tmp_path, "2026-10-15 15:37"), today="2026-10-15",
                                           timeout_s=60, poll_s=10, sleep=slept.append)
    assert ok is False and sum(slept) >= 60                       # waited the full timeout, then proceeded


def test_no_rows_today_does_not_wait(tmp_path):
    slept = []
    ok = scanner._wait_for_post_close_flow(_db(tmp_path, None), today="2026-10-15",
                                           timeout_s=60, poll_s=10, sleep=slept.append)
    assert ok is False and slept == []                            # holiday / flow outage: nothing to wait for


def test_missing_flow_table_is_fail_open(tmp_path):
    p = tmp_path / "empty.db"
    connect(str(p)).close()
    assert scanner._wait_for_post_close_flow(str(p), today="2026-10-15", timeout_s=60, sleep=lambda s: None) is False


def test_only_the_scheduled_job_waits():
    import inspect

    import scheduler as sched
    assert "_wait_for_post_close_flow" in inspect.getsource(scanner.daily_signal_scan_scheduled)
    assert "_wait_for_post_close_flow" not in inspect.getsource(scanner.daily_signal_scan)   # routes stay instant
    assert "daily_signal_scan_scheduled, CronTrigger" in inspect.getsource(sched)
