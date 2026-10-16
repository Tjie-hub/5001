"""The per-test live-DB guard must flag test writes but not a live service or WAL readers (2026-10-14)."""
import importlib.util
import os
import subprocess
import sys
import time

from pathlib import Path

# Two conftest.py files exist (root and tests/); `import conftest` would pick the root one.
_spec = importlib.util.spec_from_file_location("tests_conftest_guard", Path(__file__).with_name("conftest.py"))
cf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cf)


def test_file_held_open_by_another_process_is_exempt(tmp_path):
    f = tmp_path / "walkforward.db"
    f.write_text("x")
    p = subprocess.Popen([sys.executable, "-c",
                          f"import time; h=open({str(f)!r},'rb'); print('ready',flush=True); time.sleep(30)"],
                         stdout=subprocess.PIPE, text=True)
    try:
        assert p.stdout.readline().strip() == "ready"
        assert cf._held_open_by_other_process(f) is True
    finally:
        p.kill()
        p.wait()
    time.sleep(0.05)
    assert cf._held_open_by_other_process(f) is False


def test_file_open_only_in_this_process_is_not_exempt(tmp_path):
    f = tmp_path / "walkforward.db"
    f.write_text("x")
    with open(f, "rb"):
        assert cf._held_open_by_other_process(f) is False


def test_new_or_changed_file_is_flagged_unless_held(tmp_path, monkeypatch):
    monkeypatch.setattr(cf, "_REPO_DATA_DIR", tmp_path)
    f = tmp_path / "x.db"
    f.write_text("a")
    after = {("x.db", 1, 1)}
    assert cf._changed_by_tests(after, set()) == after
    assert cf._changed_by_tests(after, after) == set()


def test_shm_is_not_tracked(tmp_path, monkeypatch):
    monkeypatch.setattr(cf, "_REPO_DATA_DIR", tmp_path)
    (tmp_path / "w.db").write_text("a")
    (tmp_path / "w.db-shm").write_text("a")
    (tmp_path / "w.db-wal").write_text("a")
    assert {n for n, _, _ in cf._real_db_files()} == {"w.db", "w.db-wal"}


# --- 2026-10-16: the live-WAL false positive and the sqlite3.connect attribution layer ---

def test_wal_change_on_preexisting_db_is_not_flagged(tmp_path, monkeypatch):
    """The 2026-10-16 suite false positive: the live service rewrote walkforward.db-wal while
    the test ran (nobody else holding the fd), and the mtime sweep blamed the test."""
    monkeypatch.setattr(cf, "_REPO_DATA_DIR", tmp_path)
    (tmp_path / "w.db").write_text("main")
    (tmp_path / "w.db-wal").write_text("wal-1")
    before = cf._real_db_files()
    (tmp_path / "w.db-wal").write_text("wal-2-written-by-the-service")   # size + mtime change
    assert cf._changed_by_tests(cf._real_db_files(), before) == set()


def test_sidecar_without_preexisting_main_db_is_still_flagged(tmp_path, monkeypatch):
    monkeypatch.setattr(cf, "_REPO_DATA_DIR", tmp_path)
    (tmp_path / "orphan.db-wal").write_text("x")
    after = cf._real_db_files()
    assert cf._changed_by_tests(after, set()) == after


def test_recorder_flags_connects_under_real_data(tmp_path, monkeypatch):
    import sqlite3
    monkeypatch.setattr(cf, "_REPO_DATA_DIR", tmp_path)
    with cf._record_real_db_opens() as opens:
        sqlite3.connect(tmp_path / "w.db").close()
        sqlite3.connect(f"file:{tmp_path / 'w.db'}?mode=ro", uri=True).close()
        work = tmp_path / "sub"
        work.mkdir()
        sqlite3.connect(work / "scratch.db").close()
    assert len(opens) == 3 and all(str(tmp_path) in o for o in opens)
    with cf._record_real_db_opens() as opens:
        elsewhere = tmp_path.parent / "outside.db"
        sqlite3.connect(elsewhere).close()
    assert opens == []


def test_a_real_write_still_fails_the_guard(tmp_path):
    """End-to-end negative (brief Z1 done-when (a)): a subprocess pytest run whose test opens the
    REAL data/walkforward.db must fail with the attribution message, not pass silently."""
    import subprocess
    repo = Path(__file__).resolve().parents[1]
    bad = repo / "tests" / f"_test_guard_negative_{os.getpid()}.py"
    bad.write_text(
        "import sqlite3\n"
        "def test_opens_real_db():\n"
        "    conn = sqlite3.connect('data/walkforward.db')\n"
        "    conn.close()\n")
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q",
             bad.relative_to(repo).as_posix()], cwd=repo, capture_output=True, text=True, timeout=120)
        assert r.returncode != 0
        assert "opened the real database" in r.stdout
    finally:
        bad.unlink(missing_ok=True)
