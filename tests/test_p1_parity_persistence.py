"""P-1 regression: the rule-parity study must persist in bounded, atomic,
resumable steps and survive SQLite/WAL lock contention.

Observed 2026-09-02: run 62d3d8b71a00 computed 950/959 tickers correctly over
229 minutes, then lost every result when its single end-of-run transaction hit
`database is locked` (busy_timeout 30 s, contended 8.5 GB WAL DB).

These tests exercise the persistence layer directly rather than driving a 4-hour
walk-forward: the defect was never in the scoring, only in how results were
written.
"""
import sqlite3
import threading
import time

import pytest

from engine.wf_edge import (ensure_wf_edge_rule_table,
                            ensure_wf_parity_checkpoint_table,
                            completed_parity_tickers, save_parity_checkpoint,
                            save_wf_edge_rule, WF_PARITY_CHECKPOINT_DDL)
from research.jobs import _commit_with_retry, _is_lock_error

CFG = "cfg0123456789ab"
RULE = {"momentum": "momentum@weekly_mtf_trend#abc"}
NOW = "2026-09-03 10:00"


def _row(exp=1.0, n=60):
    return [{"strategy": "momentum", "expectancy_pct": exp, "expectancy_rp": 0.0,
             "win_rate": 55.0, "consistency_pct": 40.0, "sharpe": 0.4,
             "n_trades": n, "windows_tested": 15}]


@pytest.fixture()
def db(tmp_path):
    path = str(tmp_path / "p1.db")
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    ensure_wf_edge_rule_table(conn)
    ensure_wf_parity_checkpoint_table(conn)
    conn.commit()
    conn.close()
    return path


def _open(path, busy_ms=30000):
    c = sqlite3.connect(path, timeout=30)
    c.execute(f"PRAGMA busy_timeout={busy_ms}")
    return c


class TestCheckpointing:

    def test_checkpoint_records_completion_per_config(self, db):
        c = _open(db)
        save_parity_checkpoint(c, CFG, "AAA", 3, NOW, run_id="r1")
        c.commit()
        assert completed_parity_tickers(c, CFG) == {"AAA"}
        assert completed_parity_tickers(c, "otherconfig") == set()
        c.close()

    def test_a_different_configuration_never_reuses_completions(self, db):
        """Resuming across configurations would silently mix two studies."""
        c = _open(db)
        for t in ("AAA", "BBB"):
            save_parity_checkpoint(c, CFG, t, 1, NOW)
        c.commit()
        assert completed_parity_tickers(c, "deadbeefdeadbeef") == set()
        c.close()

    def test_checkpoint_is_idempotent(self, db):
        c = _open(db)
        save_parity_checkpoint(c, CFG, "AAA", 3, NOW)
        save_parity_checkpoint(c, CFG, "AAA", 3, NOW)
        c.commit()
        assert c.execute("SELECT COUNT(*) FROM wf_parity_checkpoint").fetchone()[0] == 1
        c.close()

    def test_zero_row_tickers_are_checkpointed_too(self, db):
        """A ticker that legitimately produced no qualifying row must not be
        recomputed on every resume."""
        c = _open(db)
        save_parity_checkpoint(c, CFG, "THIN", 0, NOW)
        c.commit()
        assert "THIN" in completed_parity_tickers(c, CFG)
        c.close()

    def test_ddl_is_keyed_on_config_and_ticker(self):
        assert "PRIMARY KEY (config_hash, ticker)" in WF_PARITY_CHECKPOINT_DDL


class TestAtomicity:

    def test_rows_and_checkpoint_commit_together(self, db):
        c = _open(db)

        def _write(conn):
            save_wf_edge_rule(conn, "AAA", RULE, _row(), NOW, "r1")
            save_parity_checkpoint(conn, CFG, "AAA", 1, NOW, "r1")

        _commit_with_retry(c, _write, what="one")
        c.close()
        v = _open(db)
        assert v.execute("SELECT COUNT(*) FROM wf_edge_rule").fetchone()[0] == 1
        assert completed_parity_tickers(v, CFG) == {"AAA"}
        v.close()

    def test_a_failing_write_leaves_neither_rows_nor_checkpoint(self, db):
        """Never mark a ticker done whose rows were not written."""
        c = _open(db)

        def _bad(conn):
            save_wf_edge_rule(conn, "AAA", RULE, _row(), NOW, "r1")
            save_parity_checkpoint(conn, CFG, "AAA", 1, NOW, "r1")
            raise RuntimeError("boom after both writes")

        with pytest.raises(RuntimeError):
            _commit_with_retry(c, _bad, what="bad")
        c.close()
        v = _open(db)
        assert v.execute("SELECT COUNT(*) FROM wf_edge_rule").fetchone()[0] == 0
        assert completed_parity_tickers(v, CFG) == set()
        v.close()

    def test_a_non_lock_error_is_not_retried(self, db):
        c = _open(db)
        calls = []

        def _bad(conn):
            calls.append(1)
            raise ValueError("not a lock")

        with pytest.raises(ValueError):
            _commit_with_retry(c, _bad, what="bad", attempts=4)
        assert len(calls) == 1
        c.close()


class TestInterruptedAndResumed:

    def test_completed_work_survives_an_interruption(self, db):
        """Simulates the P-1 failure: some tickers persist, then the process
        dies. A resume must keep them and only do the rest."""
        c = _open(db)
        for t in ("AAA", "BBB", "CCC"):
            _commit_with_retry(
                c, lambda conn, t=t: (
                    save_wf_edge_rule(conn, t, RULE, _row(), NOW, "r1"),
                    save_parity_checkpoint(conn, CFG, t, 1, NOW, "r1")),
                what=t)
        c.close()                                    # <- process dies here

        universe = ["AAA", "BBB", "CCC", "DDD", "EEE"]
        v = _open(db)
        done = completed_parity_tickers(v, CFG)
        pending = [t for t in universe if t not in done]
        assert done == {"AAA", "BBB", "CCC"}
        assert pending == ["DDD", "EEE"]

        for t in pending:
            _commit_with_retry(
                v, lambda conn, t=t: (
                    save_wf_edge_rule(conn, t, RULE, _row(), NOW, "r2"),
                    save_parity_checkpoint(conn, CFG, t, 1, NOW, "r2")),
                what=t)
        assert completed_parity_tickers(v, CFG) == set(universe)
        assert v.execute("SELECT COUNT(*) FROM wf_edge_rule").fetchone()[0] == 5
        v.close()

    def test_earlier_batches_survive_a_later_batch_failure(self, db):
        """The whole point: one bad write costs one batch, not the run."""
        c = _open(db)
        _commit_with_retry(
            c, lambda conn: (
                save_wf_edge_rule(conn, "AAA", RULE, _row(), NOW, "r1"),
                save_parity_checkpoint(conn, CFG, "AAA", 1, NOW, "r1")),
            what="good")

        def _bad(conn):
            save_wf_edge_rule(conn, "BBB", RULE, _row(), NOW, "r1")
            raise sqlite3.OperationalError("database is locked")

        with pytest.raises(sqlite3.OperationalError):
            _commit_with_retry(c, _bad, what="bad", attempts=1)
        c.close()
        v = _open(db)
        assert completed_parity_tickers(v, CFG) == {"AAA"}
        assert v.execute("SELECT COUNT(*) FROM wf_edge_rule").fetchone()[0] == 1
        v.close()


class TestLockContention:

    def test_write_succeeds_after_a_concurrent_writer_releases(self, db):
        """A real held write lock, released mid-flight. The retry/backoff must
        ride it out instead of discarding the result."""
        holding = threading.Event()
        released = threading.Event()

        def _hold():
            # the connection is created AND released inside this thread --
            # sqlite3 objects cannot cross threads
            h = _open(db)
            h.execute("BEGIN IMMEDIATE")
            h.execute("INSERT INTO wf_parity_checkpoint "
                      "VALUES ('other','ZZZ',0,'r',?)", (NOW,))
            holding.set()
            time.sleep(1.5)
            h.commit()
            h.close()
            released.set()

        t = threading.Thread(target=_hold, daemon=True)
        t.start()
        assert holding.wait(timeout=5)

        writer = _open(db, busy_ms=200)      # short timeout -> forces a retry
        t0 = time.time()
        _commit_with_retry(
            writer, lambda conn: (
                save_wf_edge_rule(conn, "AAA", RULE, _row(), NOW, "r1"),
                save_parity_checkpoint(conn, CFG, "AAA", 1, NOW, "r1")),
            what="contended", attempts=6)
        elapsed = time.time() - t0
        writer.close()

        assert released.wait(timeout=5)
        t.join(timeout=5)
        assert elapsed >= 1.0, "should have waited for the lock, not raced it"
        v = _open(db)
        assert completed_parity_tickers(v, CFG) == {"AAA"}
        v.close()

    def test_exhausted_retries_raise_rather_than_silently_lose_data(self, db):
        """A permanently-held lock must surface, not vanish."""
        holding = threading.Event()
        finish = threading.Event()

        def _hold():
            h = _open(db)
            h.execute("BEGIN IMMEDIATE")
            h.execute("INSERT INTO wf_parity_checkpoint "
                      "VALUES ('other','ZZZ',0,'r',?)", (NOW,))
            holding.set()
            finish.wait(timeout=20)
            h.rollback()
            h.close()

        t = threading.Thread(target=_hold, daemon=True)
        t.start()
        assert holding.wait(timeout=5)

        writer = _open(db, busy_ms=100)
        with pytest.raises(sqlite3.OperationalError):
            _commit_with_retry(
                writer, lambda conn: save_parity_checkpoint(
                    conn, CFG, "AAA", 1, NOW, "r1"),
                what="doomed", attempts=2)
        writer.close()
        finish.set()
        t.join(timeout=5)

    def test_lock_error_detection(self):
        assert _is_lock_error(sqlite3.OperationalError("database is locked"))
        assert _is_lock_error(sqlite3.OperationalError("database table is busy"))
        assert not _is_lock_error(sqlite3.OperationalError("no such table: x"))
        assert not _is_lock_error(ValueError("locked"))


class TestJobContract:

    def test_job_writes_in_bounded_transactions(self):
        import inspect
        from research import jobs
        src = inspect.getsource(jobs.refresh_wf_edge_rule)
        assert "_commit_with_retry" in src
        assert "checkpoint_every" in src
        assert "save_parity_checkpoint" in src

    def test_job_resumes_by_default_and_can_be_forced_to_restart(self):
        import inspect
        from research import jobs
        sig = inspect.signature(jobs.refresh_wf_edge_rule)
        assert sig.parameters["restart"].default is False
        assert sig.parameters["checkpoint_every"].default == 1
        src = inspect.getsource(jobs.refresh_wf_edge_rule)
        assert "completed_parity_tickers" in src

    def test_job_uses_the_long_write_busy_timeout(self):
        import inspect
        from research import jobs
        from data.db import LONG_WRITE_BUSY_TIMEOUT_MS, DEFAULT_BUSY_TIMEOUT_MS
        assert LONG_WRITE_BUSY_TIMEOUT_MS > DEFAULT_BUSY_TIMEOUT_MS
        assert "busy_timeout_ms=LONG_WRITE_BUSY_TIMEOUT_MS" in \
            inspect.getsource(jobs.refresh_wf_edge_rule)

    def test_scoring_and_eligibility_logic_untouched(self):
        """P-1 is a persistence fix only."""
        import inspect
        from research import jobs
        src = inspect.getsource(jobs.refresh_wf_edge_rule)
        assert "_WEEKLY_GATE_BYPASS" in src          # roster rule unchanged
        assert "filters=[WEEKLY_MTF_FILTER]" in src  # gate unchanged
        assert "warmup_bars=WARMUP_BARS" in src      # warm-up unchanged
        assert "aggregate_wf_windows" in src         # aggregation unchanged

    def test_default_connect_timeout_is_unchanged(self):
        from data.db import DEFAULT_BUSY_TIMEOUT_MS
        assert DEFAULT_BUSY_TIMEOUT_MS == 30_000
