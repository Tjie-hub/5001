import importlib

import pytest


def _reload_factory():
    from engine.agent_firm import config
    from engine.agent_firm.providers import factory
    importlib.reload(config)
    importlib.reload(factory)
    return factory


def test_build_router_single_provider_mode(monkeypatch):
    monkeypatch.setenv("AGENT_FIRM_PROVIDER", "zai")
    factory = _reload_factory()
    router = factory.build_router()
    assert len(router._routed) == 1
    assert router._routed[0][0].name == "zai"


def test_build_router_auto_mode_uses_provider_order(monkeypatch):
    monkeypatch.setenv("AGENT_FIRM_PROVIDER", "auto")
    monkeypatch.setenv("AGENT_FIRM_PROVIDER_ORDER", "claude,zai")
    factory = _reload_factory()
    router = factory.build_router()
    assert [p.name for p, _ in router._routed] == ["claude", "zai"]


def test_build_router_rejects_invalid_provider_mode(monkeypatch):
    monkeypatch.setenv("AGENT_FIRM_PROVIDER", "bogus")
    factory = _reload_factory()
    with pytest.raises(ValueError, match="invalid AGENT_FIRM_PROVIDER"):
        factory.build_router()


def test_build_router_rejects_unregistered_provider_in_order(monkeypatch):
    monkeypatch.setenv("AGENT_FIRM_PROVIDER", "auto")
    monkeypatch.setenv("AGENT_FIRM_PROVIDER_ORDER", "claude,openai")
    factory = _reload_factory()
    with pytest.raises(ValueError, match="unregistered"):
        factory.build_router()


def test_build_router_rejects_duplicate_names_in_order(monkeypatch):
    monkeypatch.setenv("AGENT_FIRM_PROVIDER", "auto")
    monkeypatch.setenv("AGENT_FIRM_PROVIDER_ORDER", "claude,claude")
    factory = _reload_factory()
    with pytest.raises(ValueError, match="duplicate"):
        factory.build_router()


def test_build_router_rejects_empty_order(monkeypatch):
    monkeypatch.setenv("AGENT_FIRM_PROVIDER", "auto")
    monkeypatch.setenv("AGENT_FIRM_PROVIDER_ORDER", "")
    factory = _reload_factory()
    with pytest.raises(ValueError, match="must not be empty"):
        factory.build_router()
