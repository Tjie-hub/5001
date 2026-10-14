"""The per-test live-DB guard must flag test writes but not a live service or WAL readers (2026-10-14)."""
import subprocess
import sys
import time

import importlib.util
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
