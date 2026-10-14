"""2026-10-13 fd-exhaustion incident: `with sqlite3.connect(...) as c:` commits but
never closes. On Python 3.14 those connections linger until the cyclic GC runs, so
the Forward-Test Cycle (hundreds of repo calls in seconds) pinned 1,012 handles on
walkforward.db, hit the 1024 soft limit and killed every DB open in the worker.
data.db.transaction() / forward_testing ft_txn() commit, roll back AND close."""
import os
import re
import sqlite3
from pathlib import Path

import pytest

from data.db import transaction

ROOT = Path(__file__).resolve().parents[1]


def _fds():
    return len(os.listdir("/proc/self/fd"))


@pytest.mark.skipif(not os.path.isdir("/proc/self/fd"), reason="needs /proc")
def test_transaction_does_not_leak_descriptors(tmp_path):
    db = str(tmp_path / "t.db")
    with transaction(db) as c:
        c.execute("CREATE TABLE t (a)")
    before = _fds()
    for i in range(300):
        with transaction(db) as c:
            c.execute("INSERT INTO t VALUES (?)", (i,))
    assert _fds() - before <= 2          # nothing accumulates, with no gc.collect()


def test_commits_on_success_and_rolls_back_on_error(tmp_path):
    db = str(tmp_path / "t.db")
    with transaction(db) as c:
        c.execute("CREATE TABLE t (a)")
        c.execute("INSERT INTO t VALUES (1)")
    with pytest.raises(RuntimeError):
        with transaction(db) as c:
            c.execute("INSERT INTO t VALUES (2)")
            raise RuntimeError("boom")
    raw = sqlite3.connect(db)
    assert raw.execute("SELECT a FROM t").fetchall() == [(1,)]
    raw.close()


def test_connection_is_closed_after_the_block(tmp_path):
    with transaction(str(tmp_path / "t.db")) as c:
        c.execute("CREATE TABLE t (a)")
    with pytest.raises(sqlite3.ProgrammingError):
        c.execute("SELECT 1")


def test_ft_repo_calls_do_not_leak(tmp_path):
    from forward_testing.storage.db import init_ft_tables
    from forward_testing.storage.repo import FTRepo
    db = str(tmp_path / "ft.db")
    init_ft_tables(db)
    repo = FTRepo(db)
    before = _fds()
    for i in range(300):
        repo.get_signal_state(i)
    assert _fds() - before <= 2


# Worker-reachable code must not use `with <connection factory>(...)`: it never closes.
_WORKER_DIRS = ("scheduler", "forward_testing", "engine", "routes", "data", "screener")
_WORKER_FILES = ("app.py", "monitor.py", "paper_trade.py")
_PAT = re.compile(r"\bwith\s+(?:db_connect|connect|get_db|ft_get_db|_connect|sqlite3\.connect)\s*\(")


def test_no_unclosed_with_connect_in_worker_code():
    offenders = []
    paths = [p for d in _WORKER_DIRS for p in (ROOT / d).rglob("*.py")]
    paths += [ROOT / f for f in _WORKER_FILES]
    for p in paths:
        if "__pycache__" in p.parts:
            continue
        for i, line in enumerate(p.read_text(errors="ignore").splitlines(), 1):
            if _PAT.search(line) and not line.lstrip().startswith("#"):
                offenders.append(f"{p.relative_to(ROOT).as_posix()}:{i}: {line.strip()[:70]}")
    assert not offenders, ("`with connect(...)` commits but never closes (fd leak, see module "
                           "docstring) -- use data.db.transaction()/ft_txn():\n" + "\n".join(offenders))
