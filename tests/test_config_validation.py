"""Startup config validation (hardening Phase 5) + production runtime config
guards (Phase 3)."""
import importlib.util
from pathlib import Path

import pytest

import config as cfg

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def good_env(tmp_path, monkeypatch):
    db = tmp_path / "wf.db"
    db.write_bytes(b"")
    monkeypatch.setenv("DB_PATH", str(db))
    monkeypatch.setenv("TELEGRAM_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "c")
    monkeypatch.delenv("AGENT_FIRM_ENABLED", raising=False)
    return db


def test_validate_config_passes_with_mandatory_vars(good_env):
    cfg.validate_config()  # must not raise


def test_validate_config_reports_all_problems_at_once(monkeypatch, tmp_path):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "missing.db"))
    monkeypatch.setenv("TELEGRAM_TOKEN", "")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "")
    monkeypatch.setattr(cfg, "TELEGRAM_TOKEN", "")
    monkeypatch.setattr(cfg, "TELEGRAM_CHAT_ID", "")
    with pytest.raises(cfg.ConfigError) as e:
        cfg.validate_config()
    msg = str(e.value)
    assert "DB_PATH" in msg and "TELEGRAM_TOKEN" in msg and "TELEGRAM_CHAT_ID" in msg


def test_validate_config_requires_zai_key_when_firm_enabled(good_env, monkeypatch):
    monkeypatch.setenv("AGENT_FIRM_ENABLED", "true")
    monkeypatch.setenv("AGENT_FIRM_PROVIDER", "auto")
    monkeypatch.setenv("AGENT_FIRM_PROVIDER_ORDER", "zai,claude")
    monkeypatch.delenv("ZAI_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(cfg.ConfigError, match="ZAI_API_KEY"):
        cfg.validate_config()
    monkeypatch.setenv("ZAI_API_KEY", "k")
    cfg.validate_config()  # satisfied now


def test_validate_config_claude_only_needs_no_zai_key(good_env, monkeypatch):
    monkeypatch.setenv("AGENT_FIRM_ENABLED", "true")
    monkeypatch.setenv("AGENT_FIRM_PROVIDER", "claude")
    monkeypatch.delenv("ZAI_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    cfg.validate_config()  # must not raise


def _load_gunicorn_conf():
    spec = importlib.util.spec_from_file_location("gconf", ROOT / "gunicorn.conf.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_gunicorn_config_stays_single_worker():
    """workers>1 would double-run every APScheduler job and fight over the
    SQLite write lock — guard the invariant, not just the comment."""
    g = _load_gunicorn_conf()
    assert g.workers == 1
    assert callable(g.post_worker_init) and callable(g.worker_exit)
    assert g.bind.endswith(":5001")


def test_systemd_unit_matches_runtime_contract():
    unit = (ROOT / "deploy" / "idx-walkforward.service").read_text()
    assert "Restart=always" in unit
    assert "wait_for_health.sh" in unit
    assert "-m gunicorn" in unit
