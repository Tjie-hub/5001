"""2026-10-13 fd-exhaustion incident: `with sqlite3.connect(...) as c:` commits but
never closes. On Python 3.14 those connections linger until the cyclic GC runs, so
the Forward-Test Cycle (hundreds of repo calls in seconds) pinned 1,012 handles on
walkforward.db, hit the 1024 soft limit and killed every DB open in the worker.
data.db.transaction() / forward_testing ft_txn() commit, roll back AND close."""
import ast
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
_PAT = re.compile(r"\bwith\s+(?:db\.)?(?:db_connect|connect|get_db|ft_get_db|_connect|get_conn|_get_conn|sqlite3\.connect)\s*\(")


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


# The `with`-form scan above misses the other leak shape: `conn = connect(...)` in a function that
# never closes it. On Python 3.14 such connections linger until cyclic GC, which is what exhausted
# the 1024-fd limit on 2026-10-13. AST scan, because a regex cannot tell "closed later" from "never".
_CONN_FACTORIES = {"db_connect", "connect", "get_db", "ft_get_db", "_connect", "get_conn", "_get_conn",
                   "db.get_conn", "sqlite3.connect"}


def _factory_name(node):
    if isinstance(node, ast.Call):
        f = node.func
        if isinstance(f, ast.Name):
            return f.id
        if isinstance(f, ast.Attribute):
            return f"{f.value.id}.{f.attr}" if isinstance(f.value, ast.Name) else f.attr
    return None


def _names_in(node):
    return {x.id for x in ast.walk(node) if isinstance(x, ast.Name)}


def unclosed_connections(source: str):
    """(line, variable, function) for `x = <connection factory>(...)` never closed in that function.

    A connection is accepted when the function calls x.close(), wraps it in closing(x), uses it as
    a context manager, or hands it on (return/yield/stored on an attribute -- a factory)."""
    out = []
    for fn in ast.walk(ast.parse(source)):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        assigned = {n.targets[0].id: n.lineno for n in ast.walk(fn)
                    if isinstance(n, ast.Assign) and _factory_name(n.value) in _CONN_FACTORIES
                    and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)}
        for name, line in assigned.items():
            ok = False
            for n in ast.walk(fn):
                if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "close"
                        and isinstance(n.func.value, ast.Name) and n.func.value.id == name):
                    ok = True
                elif isinstance(n, ast.Call) and _factory_name(n) in ("closing", "contextlib.closing") \
                        and any(isinstance(a, ast.Name) and a.id == name for a in n.args):
                    ok = True
                elif isinstance(n, (ast.Return, ast.Yield)) and n.value is not None and name in _names_in(n.value):
                    ok = True
                elif isinstance(n, ast.Assign) and any(isinstance(t, ast.Attribute) for t in n.targets) \
                        and name in _names_in(n.value):
                    ok = True
                elif isinstance(n, ast.With) and any(isinstance(i.context_expr, ast.Name)
                                                     and i.context_expr.id == name for i in n.items):
                    ok = True
            if not ok:
                out.append((line, name, fn.name))
    return out


def test_scanner_flags_unclosed_and_accepts_closed():
    leak = "import sqlite3\ndef f():\n    c = sqlite3.connect('x')\n    c.execute('select 1')\n"
    assert unclosed_connections(leak) == [(3, "c", "f")]
    closed = "def f():\n    c = db_connect()\n    try:\n        c.execute('x')\n    finally:\n        c.close()\n"
    assert unclosed_connections(closed) == []
    factory = "def get():\n    c = connect()\n    return c\n"
    assert unclosed_connections(factory) == []
    wrapped = "from contextlib import closing\ndef f():\n    c = connect()\n    with closing(c):\n        pass\n"
    assert unclosed_connections(wrapped) == []


def test_no_unclosed_connection_variable_in_worker_code():
    # One-shot scripts (tools/, scripts/, research/) are deliberately out of scope: they exit and
    # free their descriptors. Only long-lived worker code can exhaust the fd limit.
    offenders = []
    paths = [p for d in _WORKER_DIRS for p in (ROOT / d).rglob("*.py")]
    paths += [ROOT / f for f in _WORKER_FILES]
    for p in paths:
        if "__pycache__" in p.parts:
            continue
        for line, name, fn in unclosed_connections(p.read_text(errors="ignore")):
            offenders.append(f"{p.relative_to(ROOT).as_posix()}:{line}: {name} in {fn}()")
    assert not offenders, ("connection opened but never closed in worker code (fd leak) -- close it "
                           "in a finally, or use data.db.transaction()/ft_txn():\n" + "\n".join(offenders))


def test_screener_txn_commits_rolls_back_and_closes(tmp_path, monkeypatch):
    """screener.db.txn(): the 2026-10-14 OOM fix. The per-ticker loop opened ~3 connections per ticker."""
    from screener import db as sdb
    path = str(tmp_path / "s.db")
    monkeypatch.setattr(sdb, "DB_PATH", path)
    with sdb.txn() as c:
        c.execute("CREATE TABLE t (x)")
        c.execute("INSERT INTO t VALUES (1)")
    with pytest.raises(sqlite3.ProgrammingError):
        c.execute("SELECT 1")  # closed
    with pytest.raises(RuntimeError):
        with sdb.txn() as c2:
            c2.execute("INSERT INTO t VALUES (2)")
            raise RuntimeError("boom")
    with sdb.txn() as c3:
        assert [r[0] for r in c3.execute("SELECT x FROM t")] == [1]


def test_screener_loop_does_not_leak_descriptors(tmp_path, monkeypatch):
    from screener import db as sdb
    path = str(tmp_path / "s.db")
    monkeypatch.setattr(sdb, "DB_PATH", path)
    sdb.init_screener_tables()
    before = _fds()
    for i in range(400):
        sdb.get_avg_vol_from_db(f"T{i}", "2026-10-14")
        sdb.log_run("x", 1, 0, 0.1)
    assert _fds() - before <= 2
