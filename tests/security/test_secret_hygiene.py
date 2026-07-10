"""Secret hygiene fences (security hardening Phase 3):
no tracked secret files, no hardcoded secret literals, log redaction,
no stack traces in HTTP 500 responses."""
import importlib
import logging
import re
import sqlite3
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_env_files_not_tracked_by_git():
    out = subprocess.run(["git", "ls-files", ".env", ".stockbit_token"],
                         cwd=REPO, capture_output=True, text=True).stdout.strip()
    assert out == ""


def test_no_hardcoded_secret_literals():
    # assignments like TELEGRAM_TOKEN = "1234:AA..." with a real-looking literal
    pat = re.compile(
        r'(TOKEN|API_KEY|SECRET|PASSWORD)\s*[=:]\s*["\'][A-Za-z0-9_\-:./+]{16,}["\']')
    offenders = []
    for py in REPO.rglob("*.py"):
        rel = py.relative_to(REPO).as_posix()
        if rel.startswith(("venv/", "tests/", "_archive/", "scratchpad/",
                           "research_reports/", "chart-viewer/", ".deepseek/")):
            continue
        for i, line in enumerate(py.read_text(errors="ignore").splitlines(), 1):
            m = pat.search(line)
            if m and "getenv" not in line and "example" not in line.lower() \
                    and "your_" not in line and "os.environ" not in line:
                offenders.append(f"{rel}:{i}: {line.strip()[:80]}")
    assert not offenders, "possible hardcoded secrets:\n" + "\n".join(offenders)


def test_logging_redacts_secret_values(monkeypatch):
    monkeypatch.setenv("TELEGRAM_TOKEN", "1234567890:SECRETSECRETSECRET")
    from utils.logging_config import SecretRedactionFilter
    f = SecretRedactionFilter()
    rec = logging.LogRecord("x", logging.INFO, "f", 1,
                            "posting to bot 1234567890:SECRETSECRETSECRET now", (), None)
    assert f.filter(rec)
    assert "SECRETSECRET" not in rec.getMessage()
    assert "[REDACTED]" in rec.getMessage()


def test_redaction_filter_installed_by_setup(monkeypatch, tmp_path):
    from utils import logging_config
    logging_config.setup_logging(log_dir=str(tmp_path))
    root = logging.getLogger()
    assert any(isinstance(flt, logging_config.SecretRedactionFilter)
               for h in root.handlers for flt in h.filters)


def test_500_response_has_no_traceback(tmp_path, monkeypatch):
    db = tmp_path / "t.db"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE scheduled_signals (scan_time TEXT)")
    conn.execute("CREATE TABLE paper_trades (ticker TEXT, status TEXT)")
    conn.commit()
    conn.close()
    monkeypatch.setenv("DB_PATH", str(db))
    import app as app_module
    importlib.reload(app_module)
    app_module.app.config["TESTING"] = False   # exercise the real error handler

    @app_module.app.route("/_boom_test")
    def _boom():
        raise RuntimeError("kaboom SECRETVALUE")

    c = app_module.app.test_client()
    r = c.get("/_boom_test")
    assert r.status_code == 500
    body = r.get_data(as_text=True)
    assert "Traceback" not in body and "kaboom" not in body
    assert r.headers.get("X-Request-ID")  # correlation id survives error path
