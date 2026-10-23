"""fin_full_pull_20261025.sh guard tests (U3, brief 2026-10-22).

Every pre-flight must refuse, loudly, in the log — and none of these tests may touch the
network, the real token, or the real fetch (env hooks stub each guard; only the refusals are
exercised — the happy path is Sunday's actual run).
"""
import os
import subprocess
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "fin_full_pull_20261025.sh"


def _run(tmp_path, **env_overrides):
    log = tmp_path / "pull_test.log"
    env = dict(os.environ)
    env.update({k.upper(): str(v) for k, v in env_overrides.items()})
    env["FQ_PULL_LOG"] = str(log)
    r = subprocess.run(["bash", str(SCRIPT), "test"], capture_output=True, text=True,
                       env=env, timeout=60, cwd=str(REPO))
    return r, log.read_text() if log.exists() else ""


def test_script_parses():
    assert subprocess.run(["bash", "-n", str(SCRIPT)]).returncode == 0


def test_refuses_a_day_other_than_sunday(tmp_path):
    r, log = _run(tmp_path, FQ_PULL_EXPECT_DATE="1999-01-01")
    assert r.returncode != 0
    assert "REFUSED: today is" in log and "1999-01-01" in log
    assert "fetch" not in log  # refused before anything data-touching


def test_refuses_while_the_jurnal26_backfill_service_is_active(tmp_path):
    r, log = _run(tmp_path, FQ_PULL_EXPECT_DATE=date.today().isoformat(),
                  FQ_PULL_BACKFILL_CHECK="true")   # the service-state check returning rc 0 = running
    assert r.returncode != 0
    assert "tape backfill service is running" in log


def test_refuses_when_the_token_check_fails(tmp_path):
    r, log = _run(tmp_path, FQ_PULL_EXPECT_DATE=date.today().isoformat(),
                  FQ_PULL_BACKFILL_CHECK="false", FQ_PULL_PRECHECK_CMD="false")
    assert r.returncode != 0
    assert "pre-open check failed" in log


def test_s2_refuses_while_s1_holds_the_lock(tmp_path):
    """A2 review fix (2026-10-22): the 13:00 resume must not run beside a still-running 09:05
    session. flock held from the test side = a live s1; the script must refuse, not queue."""
    import fcntl

    lock = tmp_path / "pull.lock"
    fh = lock.open("w")
    fcntl.flock(fh, fcntl.LOCK_EX)
    try:
        stub = tmp_path / "fetch_ran"
        r, log = _run(tmp_path, FQ_PULL_EXPECT_DATE=date.today().isoformat(),
                      FQ_PULL_BACKFILL_CHECK="false", FQ_PULL_PRECHECK_CMD="true",
                      FQ_PULL_LOCK=str(lock), FQ_PULL_FETCH_CMD=f"touch {stub}")
        assert r.returncode != 0
        assert "holds the lock" in log
        assert not stub.exists()             # no fetch beside a live session
    finally:
        fcntl.flock(fh, fcntl.LOCK_UN)
        fh.close()


def test_green_guards_reach_a_stubbed_fetch_and_log_end_markers(tmp_path):
    """The refusal ladder's order (date -> lock -> backfill -> token -> disk) is pinned by the
    tests above; this one stubs every guard green AND stubs the fetch itself
    (FQ_PULL_FETCH_CMD) — the real fetch is never exercised from the test suite. Stubs are
    single commands with plain arguments: the script runs $FETCH_CMD unquoted, so no shell
    quoting is re-parsed."""
    today = date.today().isoformat()
    stub = tmp_path / "fetch_ran"
    r, log = _run(tmp_path, FQ_PULL_EXPECT_DATE=today, FQ_PULL_BACKFILL_CHECK="false",
                  FQ_PULL_PRECHECK_CMD="true", FQ_PULL_LOCK=str(tmp_path / "free.lock"),
                  FQ_PULL_FETCH_CMD=f"touch {stub}")
    assert r.returncode == 0
    assert stub.exists()                       # the (stubbed) fetch really ran
    assert "fetch rc=0" in log and "END full-pull session test" in log
    assert "REFUSED" not in log
