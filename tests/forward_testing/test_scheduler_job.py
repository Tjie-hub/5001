"""Job-level e2e: run_forward_test_cycle ingests + opens, and is idempotent."""
import sqlite3

from tests.forward_testing.conftest import seed_ohlcv, seed_signal

FLAT = [("2026-06-%02d" % d, 100, 100.5, 99.5, 100, 1000) for d in range(1, 27)]


def _seed(ft_db):
    conn = sqlite3.connect(ft_db)
    seed_signal(conn, "2026-06-26 16:15", "BBCA", "vol_weighted", direction="BUY")
    seed_ohlcv(conn, "BBCA", FLAT + [("2026-06-27", 100, 100.5, 99.5, 100, 1000)])
    conn.commit(); conn.close()


def test_cycle_ingests_and_opens(ft_db, repo):
    from scheduler.jobs import run_forward_test_cycle
    _seed(ft_db)

    # Real two-day flow: a 06-26 signal is ingested on the 06-26 cycle (open deferred
    # -- its fill bar 06-27 is in the future), then fills at 06-27's open on the
    # 06-27 cycle (next_open == run_date). Opening at 06-27 during the 06-26 run
    # would be look-ahead, which the entry-timeliness guard now blocks.
    run_forward_test_cycle(db_path=ft_db, run_date="2026-06-26")   # ingest; defer
    run_forward_test_cycle(db_path=ft_db, run_date="2026-06-27")   # timely open

    positions = repo.get_open_shadow_positions()
    assert len(positions) == 1
    assert positions[0]["ticker"] == "BBCA"


def test_cycle_is_idempotent(ft_db, repo):
    from scheduler.jobs import run_forward_test_cycle
    _seed(ft_db)

    run_forward_test_cycle(db_path=ft_db, run_date="2026-06-26")   # ingest
    run_forward_test_cycle(db_path=ft_db, run_date="2026-06-27")   # opens
    run_forward_test_cycle(db_path=ft_db, run_date="2026-06-27")   # second 06-27 run = no-op

    assert len(repo.get_open_shadow_positions()) == 1


def test_cycle_failsoft_on_bad_db(caplog):
    """A broken db_path must not raise -- the scheduler must survive."""
    from scheduler.jobs import run_forward_test_cycle
    run_forward_test_cycle(db_path="/nonexistent/dir/x.db", run_date="2026-06-26")
    assert "Forward-test cycle error" in caplog.text
