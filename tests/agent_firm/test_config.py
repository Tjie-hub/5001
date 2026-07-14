import importlib
import os
from pathlib import Path

import pytest


def reload_config():
    from engine.agent_firm import config
    return importlib.reload(config)


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch, tmp_path):
    """Point the firm config at an empty temp .env for every test in this
    file, so "default" assertions aren't polluted by the real repo .env
    (the module loads .env on import since RCA 2026-07-13). Individual
    tests that WANT a .env value set it explicitly via monkeypatch.setenv
    or by writing to tmp_path and reloading."""
    monkeypatch.setenv("AGENT_FIRM_ENV_PATH", str(tmp_path / "absent.env"))
    yield


def test_default_disabled(monkeypatch):
    monkeypatch.delenv("AGENT_FIRM_ENABLED", raising=False)
    cfg = reload_config()
    assert cfg.FIRM_ENABLED is False
    assert cfg.is_active() is False


def test_enabled_via_env(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_FIRM_ENABLED", "true")
    monkeypatch.setattr("engine.agent_firm.config.KILL_SWITCH_FILE", tmp_path / "missing")
    cfg = reload_config()
    monkeypatch.setattr(cfg, "KILL_SWITCH_FILE", tmp_path / "missing")
    assert cfg.FIRM_ENABLED is True
    assert cfg.is_active() is True


def test_kill_switch_overrides(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_FIRM_ENABLED", "true")
    kill = tmp_path / "agent_firm.disable"
    kill.write_text("")
    cfg = reload_config()
    monkeypatch.setattr(cfg, "KILL_SWITCH_FILE", kill)
    assert cfg.is_active() is False


def test_pricing_defaults(monkeypatch):
    monkeypatch.delenv("AGENT_FIRM_PRICE_IN", raising=False)
    monkeypatch.delenv("AGENT_FIRM_PRICE_OUT", raising=False)
    monkeypatch.delenv("AGENT_FIRM_MODEL", raising=False)
    cfg = reload_config()
    assert cfg.PRICE_INPUT_PER_M == pytest.approx(0.435)
    assert cfg.PRICE_OUTPUT_PER_M == pytest.approx(0.870)
    assert cfg.MODEL_ID == "glm-5.2"


def test_tavily_config_defaults(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("AGENT_FIRM_TAVILY_MAX", raising=False)
    cfg = reload_config()
    assert cfg.TAVILY_API_KEY == ""
    assert cfg.TAVILY_MAX_RESULTS == 5


def test_tavily_config_from_env(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test-key")
    monkeypatch.setenv("AGENT_FIRM_TAVILY_MAX", "3")
    cfg = reload_config()
    assert cfg.TAVILY_API_KEY == "tvly-test-key"
    assert cfg.TAVILY_MAX_RESULTS == 3


def test_zai_key_from_new_var(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("ZAI_API_KEY", "zai-key-123")
    cfg = reload_config()
    assert cfg.ZAI_API_KEY == "zai-key-123"


def test_zai_key_falls_back_to_deprecated_deepseek_var(monkeypatch, caplog):
    monkeypatch.delenv("ZAI_API_KEY", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "old-deepseek-key")
    cfg = reload_config()
    assert cfg.ZAI_API_KEY == "old-deepseek-key"


def test_provider_mode_defaults_to_zai(monkeypatch):
    monkeypatch.delenv("AGENT_FIRM_PROVIDER", raising=False)
    cfg = reload_config()
    assert cfg.PROVIDER_MODE == "zai"


def test_provider_order_parses_csv(monkeypatch):
    monkeypatch.setenv("AGENT_FIRM_PROVIDER_ORDER", "claude,zai,openai")
    cfg = reload_config()
    assert cfg.PROVIDER_ORDER == ["claude", "zai", "openai"]


def test_circuit_breaker_defaults(monkeypatch):
    monkeypatch.delenv("AGENT_FIRM_CIRCUIT_FAILURES", raising=False)
    monkeypatch.delenv("AGENT_FIRM_CIRCUIT_COOLDOWN", raising=False)
    cfg = reload_config()
    assert cfg.CIRCUIT_FAILURES == 3
    assert cfg.CIRCUIT_COOLDOWN_S == pytest.approx(30.0)


def test_claude_config_defaults(monkeypatch):
    monkeypatch.delenv("AGENT_FIRM_CLAUDE_MODEL", raising=False)
    monkeypatch.delenv("AGENT_FIRM_CLAUDE_MAX_CONCURRENT", raising=False)
    monkeypatch.delenv("AGENT_FIRM_CLAUDE_MAX_CALLS_PER_DAY", raising=False)
    cfg = reload_config()
    assert cfg.CLAUDE_MODEL == "sonnet"
    assert cfg.CLAUDE_MAX_CONCURRENT == 4
    assert cfg.CLAUDE_MAX_CALLS_PER_DAY == 200


def test_quota_hold_defaults(monkeypatch):
    """RCA 2026-07-10: quota-aware routing knobs, sensible defaults."""
    for var in ("AGENT_FIRM_QUOTA_HOLD", "AGENT_FIRM_QUOTA_RESET_BUFFER",
                "AGENT_FIRM_QUOTA_FALLBACK_HOLD", "AGENT_FIRM_QUOTA_MAX_HOLD"):
        monkeypatch.delenv(var, raising=False)
    cfg = reload_config()
    assert cfg.QUOTA_HOLD_ENABLED is True
    assert cfg.QUOTA_RESET_BUFFER_S == pytest.approx(60.0)
    assert cfg.QUOTA_FALLBACK_HOLD_S == pytest.approx(900.0)
    assert cfg.QUOTA_MAX_HOLD_S == pytest.approx(6 * 3600.0)


def test_quota_hold_env_overrides(monkeypatch):
    monkeypatch.setenv("AGENT_FIRM_QUOTA_HOLD", "false")
    monkeypatch.setenv("AGENT_FIRM_QUOTA_FALLBACK_HOLD", "120")
    cfg = reload_config()
    assert cfg.QUOTA_HOLD_ENABLED is False
    assert cfg.QUOTA_FALLBACK_HOLD_S == pytest.approx(120.0)


def test_quota_alert_defaults(monkeypatch):
    for var in ("AGENT_FIRM_QUOTA_ALERTS", "AGENT_FIRM_ALERT_MIN_INTERVAL",
                "AGENT_FIRM_QUOTA_REPEAT_THRESHOLD"):
        monkeypatch.delenv(var, raising=False)
    cfg = reload_config()
    assert cfg.QUOTA_ALERTS_ENABLED is True
    assert cfg.ALERT_MIN_INTERVAL_S == pytest.approx(1800.0)
    assert cfg.QUOTA_REPEAT_THRESHOLD == 3


# --- RCA 2026-07-13: standalone import must load .env ------------------------

def test_dotenv_values_loaded_on_import(monkeypatch, tmp_path):
    """Importing this module without the app's root config.py having run
    first must still load .env, so a standalone smoke/CLI run sees
    ZAI_API_KEY etc. Previously the key read as empty and every provider
    call failed with a spurious 401."""
    env_file = tmp_path / "firm.env"
    env_file.write_text("AGENT_FIRM_MODEL=from-dotenv-file\n")
    monkeypatch.setenv("AGENT_FIRM_ENV_PATH", str(env_file))
    monkeypatch.delenv("AGENT_FIRM_MODEL", raising=False)
    cfg = reload_config()
    assert cfg.MODEL_ID == "from-dotenv-file"


def test_explicit_env_var_wins_over_dotenv(monkeypatch, tmp_path):
    """Explicitly-set env vars (CI, systemd Environment=, monkeypatched tests)
    must override .env — load_dotenv is called with override=False, so a value
    already in os.environ is preserved."""
    env_file = tmp_path / "firm.env"
    env_file.write_text("AGENT_FIRM_MODEL=from-dotenv-file\n")
    monkeypatch.setenv("AGENT_FIRM_ENV_PATH", str(env_file))
    monkeypatch.setenv("AGENT_FIRM_MODEL", "from-real-env")
    cfg = reload_config()
    assert cfg.MODEL_ID == "from-real-env"
