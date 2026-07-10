"""Cron reliability (hardening Phase 4 / audit P-4): the canonical crontab in
deploy/crontab must reference only scripts that exist, wrap every job in
cron_wrap.sh, and the wrapper must log + alert on failure."""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CRONTAB = (ROOT / "deploy" / "crontab").read_text()
WRAP = ROOT / "scripts" / "cron_wrap.sh"

JOB_LINES = [l for l in CRONTAB.splitlines()
             if l.strip() and not l.strip().startswith("#")
             and not re.match(r"^[A-Z]+=", l.strip())]


def test_every_cron_job_uses_the_wrapper():
    for line in JOB_LINES:
        assert "$W " in line, f"unwrapped cron job: {line}"


def test_dead_jobs_are_gone():
    for dead in ("sectors_fetcher.py", "audit_signals.py"):
        assert not any(dead in l for l in JOB_LINES), f"{dead} still scheduled"


def test_all_referenced_scripts_exist():
    """'Detect missing scripts' — the failure mode that ran silently for weeks."""
    missing = []
    for line in JOB_LINES:
        for script in re.findall(r"[\w./-]+\.py", line):
            if not (ROOT / script).exists():
                missing.append(f"{script} (from: {line.strip()})")
        for mod in re.findall(r"-m ([\w.]+)", line):
            p = ROOT / (mod.replace(".", "/") + ".py")
            if not p.exists() and not (ROOT / mod.replace(".", "/")).is_dir():
                missing.append(f"module {mod} (from: {line.strip()})")
    assert not missing, f"crontab references missing scripts: {missing}"


def _run_wrap(tmp_path, *cmd):
    env_file = tmp_path / "empty.env"
    env_file.write_text("")  # no telegram creds → alert-skipped path
    return subprocess.run(
        [str(WRAP), *cmd],
        env={"PATH": "/usr/bin:/bin",
             "CRON_WRAP_LOG_DIR": str(tmp_path),
             "CRON_WRAP_ENV": str(env_file)},
        capture_output=True, text=True,
    )


def test_wrapper_success_logs_and_exits_zero(tmp_path):
    r = _run_wrap(tmp_path, "okjob", "true")
    assert r.returncode == 0
    log = (tmp_path / "cron_okjob.log").read_text()
    assert "START okjob" in log and "EXIT okjob rc=0" in log
    assert "ALERT" not in log


def test_wrapper_failure_exits_nonzero_and_records_alert(tmp_path):
    r = _run_wrap(tmp_path, "failjob", "false")
    assert r.returncode == 1
    log = (tmp_path / "cron_failjob.log").read_text()
    assert "EXIT failjob rc=1" in log
    assert "ALERT SKIPPED (no telegram creds)" in log  # would have alerted


def test_wrapper_missing_script_is_a_loud_failure(tmp_path):
    r = _run_wrap(tmp_path, "gone", "/no/such/script.py")
    assert r.returncode != 0
    log = (tmp_path / "cron_gone.log").read_text()
    assert "ALERT SKIPPED (no telegram creds)" in log
