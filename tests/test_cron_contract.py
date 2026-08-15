"""Cron reliability (hardening Phase 4 / audit P-4): the canonical crontab in
deploy/crontab must reference only scripts that exist, wrap every job in
cron_wrap.sh, and the wrapper must log + alert on failure."""
import http.server
import os
import re
import subprocess
import threading
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


class _CapturingHandler(http.server.BaseHTTPRequestHandler):
    """Minimal mock Telegram API: records the POST body, always 200s."""
    captured = []

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        self.__class__.captured.append(self.rfile.read(length).decode())
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":true,"result":{}}')

    def log_message(self, *args):
        pass  # keep test output quiet


def test_cron_wrap_redacts_secret_before_telegram_send(tmp_path):
    """P1-7: cron_wrap.sh's shell-based Telegram alert was the one outbound
    path never covered by utils.logging_config.redact_secrets(). A wrapped
    job's last 5 log lines can contain anything it printed -- including a
    leaked secret value -- and that used to go straight to Telegram
    unredacted. Requires the real project venv (redact_secrets imports
    flask); skips rather than false-passes when unavailable, since this
    checkout may not have one (see scripts/release.sh's own SHARED_PATHS
    test for the same Windows-checkout caveat)."""
    repo_root = Path(__file__).resolve().parents[1]
    pybin_unix = repo_root / "venv" / "bin" / "python3"
    if not pybin_unix.exists():
        import pytest
        pytest.skip("no venv/bin/python3 on this checkout (see cron_wrap.sh's "
                    "PYBIN fallback) -- validate on a real Linux checkout")

    server = http.server.HTTPServer(("127.0.0.1", 0), _CapturingHandler)
    _CapturingHandler.captured = []
    port = server.server_address[1]
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()

    secret = "supersecret-zai-key-0123456789"
    env_file = tmp_path / "test.env"
    env_file.write_text("TELEGRAM_TOKEN=faketoken123\nTELEGRAM_CHAT_ID=99999\n")
    env = dict(os.environ)
    env.update(
        PATH=os.environ.get("PATH", ""),
        CRON_WRAP_LOG_DIR=str(tmp_path),
        CRON_WRAP_ENV=str(env_file),
        CRON_WRAP_API_BASE=f"http://127.0.0.1:{port}",
        ZAI_API_KEY=secret,
    )
    r = subprocess.run(
        [WRAP, "leakjob", "sh", "-c", f"echo 'boom: {secret}'; exit 1"],
        env=env, capture_output=True, text=True,
    )
    assert r.returncode == 1
    thread.join(timeout=10)

    assert len(_CapturingHandler.captured) == 1, "alert was not sent"
    body = _CapturingHandler.captured[0]
    assert secret not in body, "raw secret leaked into the Telegram payload"
    assert "%5BREDACTED%5D" in body or "[REDACTED]" in body

    log = (tmp_path / "cron_leakjob.log").read_text()
    assert "REDACTION SKIPPED" not in log
    assert "REDACTION FAILED" not in log
