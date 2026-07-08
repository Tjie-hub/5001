import importlib
import os
from pathlib import Path

import pytest


def reload_config():
    from engine.agent_firm import config
    return importlib.reload(config)


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
