"""Log rotation for logs/cron_*.log and friends (2026-10-13). Runs as a user
timer: the system logrotate cannot see this repo's logs/ without root config."""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONF = ROOT / "deploy" / "logrotate" / "idx-logs.conf"


def test_config_rotates_only_big_files_and_never_recreates_them():
    text = CONF.read_text()
    # copytruncate: cron_wrap.sh appends with >> to a path it re-opens each run
    assert "copytruncate" in text
    # size trigger, not time: rotation resets mtime, and
    # check_backup_heartbeat.py reads cron_db_backup*.log mtimes as its signal
    assert "size 5M" in text and "daily" not in text and "weekly" not in text
    assert "./logs/cron_*.log" in text


def test_unit_pair():
    svc = (ROOT / "deploy/systemd/idx-logrotate.service").read_text()
    tmr = (ROOT / "deploy/systemd/idx-logrotate.timer").read_text()
    assert "logrotate" in svc and "idx-logs.conf" in svc and "-s " in svc
    assert "Persistent=true" in tmr


@pytest.mark.skipif(not shutil.which("logrotate"), reason="logrotate not installed")
def test_rotates_a_big_log_and_leaves_a_small_one(tmp_path):
    (tmp_path / "logs").mkdir()
    big, small = tmp_path / "logs/cron_big.log", tmp_path / "logs/cron_small.log"
    big.write_bytes(b"x" * (6 * 1024 * 1024))
    small.write_text("EXIT job rc=0\n")
    mtime = small.stat().st_mtime_ns
    r = subprocess.run(["logrotate", "-s", str(tmp_path / "state"), str(CONF)],
                       cwd=tmp_path, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert big.stat().st_size == 0
    assert list((tmp_path / "logs").glob("cron_big.log.1*"))
    assert small.stat().st_mtime_ns == mtime and small.read_text() == "EXIT job rc=0\n"
