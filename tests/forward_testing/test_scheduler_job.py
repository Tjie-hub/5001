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


def test_cycle_sends_forward_test_telegram_report(ft_db, repo, monkeypatch):
    """Phase 3 wiring: a successful cycle sends the Telegram reporting layer's
    message (audit 2026-07-28) — reporting only, no change to ingest/open/exit."""
    import scheduler.jobs as jobs_mod
    sent = []
    monkeypatch.setattr(jobs_mod, "send_telegram", lambda text: sent.append(text))

    _seed(ft_db)
    jobs_mod.run_forward_test_cycle(db_path=ft_db, run_date="2026-06-26")   # ingest only
    jobs_mod.run_forward_test_cycle(db_path=ft_db, run_date="2026-06-27")   # opens BBCA

    assert len(sent) == 2
    assert "FORWARD TEST SUMMARY" in sent[-1]
    assert "New: 1" in sent[-1] and "BBCA" in sent[-1]


def test_cycle_dedup_guard_sends_telegram_only_once_per_run_date(ft_db, repo, monkeypatch):
    import scheduler.jobs as jobs_mod
    sent = []
    monkeypatch.setattr(jobs_mod, "send_telegram", lambda text: sent.append(text))

    _seed(ft_db)
    jobs_mod.run_forward_test_cycle(db_path=ft_db, run_date="2026-06-26")
    jobs_mod.run_forward_test_cycle(db_path=ft_db, run_date="2026-06-27")
    jobs_mod.run_forward_test_cycle(db_path=ft_db, run_date="2026-06-27")   # dup -> no 2nd send

    assert len(sent) == 2   # one for 06-26, one for 06-27; the repeat 06-27 sent nothing new
