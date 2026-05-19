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
    cfg = reload_config()
    assert cfg.PRICE_INPUT_PER_M == pytest.approx(0.435)
    assert cfg.PRICE_OUTPUT_PER_M == pytest.approx(0.870)
    assert cfg.MODEL_ID == "deepseek-v4-pro"
