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
    # This test is about the ZAI_API_KEY branch, not CLI discovery -- mock
    # shutil.which so it doesn't depend on whether the claude CLI happens to
    # be on PATH in whatever environment runs this (same pattern already
    # used by test_claude_in_order_requires_cli below, just the opposite
    # return value: CI failure found this test assumed "claude" present).
    monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/claude")
    with pytest.raises(cfg.ConfigError, match="ZAI_API_KEY"):
        cfg.validate_config()
    monkeypatch.setenv("ZAI_API_KEY", "k")
    cfg.validate_config()  # satisfied now


def test_validate_config_claude_only_needs_no_zai_key(good_env, monkeypatch):
    monkeypatch.setenv("AGENT_FIRM_ENABLED", "true")
    monkeypatch.setenv("AGENT_FIRM_PROVIDER", "claude")
    monkeypatch.delenv("ZAI_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    # This test is about the ZAI-key skip, not CLI discovery -- mock
    # shutil.which so it doesn't depend on the claude CLI being on PATH in
    # whatever environment runs this (see test_claude_in_order_requires_cli
    # for the mirror case; CI has no claude CLI installed, so this was
    # failing there for a reason unrelated to what the test asserts).
    monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/claude")
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


# --- security & release hardening: auth / DB / provider / manifest checks ---

def test_enforce_without_tokens_aborts(good_env, monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "enforce")
    for v in ("AUTH_TOKEN_ADMIN", "AUTH_TOKEN_OPERATOR", "AUTH_TOKEN_VIEWER",
              "AUTH_TOKEN_SCHEDULER"):
        monkeypatch.delenv(v, raising=False)
    with pytest.raises(cfg.ConfigError, match="AUTH_MODE=enforce"):
        cfg.validate_config()


def test_short_token_rejected(good_env, monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "enforce")
    monkeypatch.setenv("AUTH_TOKEN_ADMIN", "short")
    with pytest.raises(cfg.ConfigError, match="16"):
        cfg.validate_config()


def test_unknown_auth_mode_rejected(good_env, monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "banana")
    with pytest.raises(cfg.ConfigError, match="AUTH_MODE"):
        cfg.validate_config()


def test_enforce_with_good_tokens_passes(good_env, monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "enforce")
    monkeypatch.setenv("AUTH_TOKEN_ADMIN", "an-admin-token-of-decent-length")
    cfg.validate_config()  # must not raise


def test_db_with_wrong_tables_aborts(monkeypatch, tmp_path):
    import sqlite3
    db = tmp_path / "foreign.db"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE unrelated (x INT)")
    conn.commit(); conn.close()
    monkeypatch.setenv("DB_PATH", str(db))
    monkeypatch.setenv("TELEGRAM_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "c")
    monkeypatch.delenv("AGENT_FIRM_ENABLED", raising=False)
    with pytest.raises(cfg.ConfigError, match="required table"):
        cfg.validate_config()


def test_empty_db_allowed_for_bootstrap(good_env):
    # fresh DB (no tables at all) is created/migrated by init_runtime AFTER
    # validation — must not abort first boot
    cfg.validate_config()


def test_claude_in_order_requires_cli(good_env, monkeypatch):
    monkeypatch.setenv("AGENT_FIRM_ENABLED", "true")
    monkeypatch.setenv("AGENT_FIRM_PROVIDER", "claude")
    monkeypatch.setattr("shutil.which", lambda name: None)
    with pytest.raises(cfg.ConfigError, match="claude CLI"):
        cfg.validate_config()


def test_invalid_release_manifest_aborts(good_env, monkeypatch, tmp_path):
    bad = tmp_path / "release.json"
    bad.write_text('{"git_sha": "abc"}')   # missing version/built_at
    monkeypatch.setattr(cfg, "_RELEASE_MANIFEST", bad)
    with pytest.raises(cfg.ConfigError, match="release.json"):
        cfg.validate_config()


def test_valid_release_manifest_passes(good_env, monkeypatch, tmp_path):
    ok = tmp_path / "release.json"
    ok.write_text('{"version": "v", "git_sha": "s", "built_at": "t"}')
    monkeypatch.setattr(cfg, "_RELEASE_MANIFEST", ok)
    cfg.validate_config()
