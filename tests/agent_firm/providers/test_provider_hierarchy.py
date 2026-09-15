"""Provider hierarchy (2026-09-15): Claude Sonnet is PRIMARY, GLM-5.3 Flash
(zai) is the sole FALLBACK for every Agent Firm LLM invocation (post-close,
premarket, and the intraday exit-veto call all share one config-driven
router — see engine.agent_firm.config.PROVIDER_ORDER).

router.py/circuit_breaker.py/factory.py are NOT modified by this change —
only the configured order/model defaults are. These tests prove the
resulting behavior with the real (as-configured) provider names, on top of
the existing generic router coverage in test_router.py:
  - Claude is tried first whenever it's available (priority)
  - a Claude failure/circuit-open/session-limit falls over to GLM (fallback)
  - a fresh invocation (router rebuilt, as every real evaluate_staged() call
    does) always retries Claude first again -- a GLM success never "sticks"
  - both providers receive byte-identical input for the same call
  - the circuit breaker still opens after CIRCUIT_FAILURES consecutive
    Claude failures within one router's lifetime (existing safeguard,
    unmodified, exercised here with the real configured threshold)
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest

from engine.agent_firm import config
from engine.agent_firm.providers.base import ProviderCapabilities, ProviderResponse
from engine.agent_firm.providers.circuit_breaker import CircuitBreaker
from engine.agent_firm.providers.errors import ProviderUnavailable
from engine.agent_firm.providers.router import ProviderRouter


def _resp(provider, model="m") -> ProviderResponse:
    return ProviderResponse(
        content="ok", provider=provider, model=model, runtime_version="v",
        tokens_in=1, tokens_out=1, cost_usd=0.0, duration_s=0.1,
        timestamp=datetime.now(timezone.utc),
    )


def _fake_provider(name, generate_result=None, generate_error=None):
    p = AsyncMock()
    p.name = name
    p.model = Mock(return_value="m")
    p.capabilities = ProviderCapabilities(
        supports_json_mode=True, supports_json_schema=True, supports_tools=True)
    if generate_error is not None:
        p.generate.side_effect = generate_error
    else:
        p.generate.return_value = generate_result or _resp(name)
    return p


def _claude_glm_router(claude_error=None, claude_result=None):
    claude = _fake_provider("claude", generate_result=claude_result, generate_error=claude_error)
    glm = _fake_provider("zai", generate_result=_resp("zai", model="glm-5.3-flash"))
    return ProviderRouter([(claude, CircuitBreaker()), (glm, CircuitBreaker())]), claude, glm


# ── Configured default hierarchy ──────────────────────────────────────────────
# config.PROVIDER_ORDER/PROVIDER_MODE default values themselves are covered by
# tests/agent_firm/test_config.py::test_provider_order_defaults_to_claude_primary
# and ::test_provider_mode_defaults_to_auto. This proves the full factory ->
# router pipeline honors that default end-to-end.

def test_build_router_with_no_overrides_uses_claude_first(monkeypatch):
    monkeypatch.delenv("AGENT_FIRM_PROVIDER", raising=False)
    monkeypatch.delenv("AGENT_FIRM_PROVIDER_ORDER", raising=False)
    import importlib
    from engine.agent_firm import config as cfg
    from engine.agent_firm.providers import factory
    importlib.reload(cfg)
    importlib.reload(factory)
    router = factory.build_router()
    assert [p.name for p, _ in router._routed] == ["claude", "zai"]


# ── Priority ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_claude_is_used_when_available():
    router, claude, glm = _claude_glm_router()
    resp = await router.generate([{"role": "user", "content": "x"}])
    assert resp.provider == "claude"
    assert resp.failover is False
    claude.generate.assert_awaited_once()
    glm.generate.assert_not_awaited()


# ── Fallback ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_falls_over_to_glm_when_claude_unavailable():
    router, claude, glm = _claude_glm_router(claude_error=ProviderUnavailable("down"))
    resp = await router.generate([{"role": "user", "content": "x"}])
    assert resp.provider == "zai"
    assert resp.model == "glm-5.3-flash"
    assert resp.failover is True
    glm.generate.assert_awaited_once()


@pytest.mark.asyncio
async def test_falls_over_to_glm_when_claude_circuit_open():
    claude = _fake_provider("claude")
    glm = _fake_provider("zai", generate_result=_resp("zai", model="glm-5.3-flash"))
    open_breaker = CircuitBreaker(failure_threshold=1, cooldown_s=999)
    open_breaker.record_failure()  # opens immediately (threshold=1)
    router = ProviderRouter([(claude, open_breaker), (glm, CircuitBreaker())])
    resp = await router.generate([{"role": "user", "content": "x"}])
    assert resp.provider == "zai"
    claude.generate.assert_not_awaited()  # circuit skipped it without calling


# ── No un-reversal: a GLM success never demotes Claude for the next call ─────

@pytest.mark.asyncio
async def test_a_fresh_invocation_retries_claude_first_after_a_prior_glm_fallback():
    """Mirrors production: evaluate_staged()/evaluate() build a brand-new
    ProviderRouter (and fresh CircuitBreakers) on every external invocation
    (engine/agent_firm/firm.py, both evaluate_async and evaluate_staged_async
    call build_router() with no caching) -- so a GLM fallback in one run has
    no way to persist into the next run's provider choice."""
    router1, claude1, glm1 = _claude_glm_router(claude_error=ProviderUnavailable("down"))
    resp1 = await router1.generate([{"role": "user", "content": "x"}])
    assert resp1.provider == "zai"

    # A brand-new router for "the next eligible invocation" -- independent
    # CircuitBreaker instances, exactly what a fresh evaluate_staged() call
    # constructs. Claude is healthy again.
    router2, claude2, glm2 = _claude_glm_router()
    resp2 = await router2.generate([{"role": "user", "content": "x"}])
    assert resp2.provider == "claude"
    assert resp2.failover is False
    glm2.generate.assert_not_awaited()


# ── Identical input to both providers ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_glm_receives_the_identical_messages_claude_would_have():
    messages = [
        {"role": "system", "content": "prompt"},
        {"role": "user", "content": '{"ticker": "BBCA", "candidates": ["BBCA", "BBRI", "TLKM"]}'},
    ]
    router_claude_ok, claude_ok, glm_unused = _claude_glm_router()
    await router_claude_ok.generate(messages)
    claude_ok.generate.assert_awaited_once_with(messages, timeout=None)

    router_fallback, claude_down, glm_serves = _claude_glm_router(
        claude_error=ProviderUnavailable("down"))
    await router_fallback.generate(messages)
    glm_serves.generate.assert_awaited_once_with(messages, timeout=None)

    # Same call, same content, regardless of which provider ends up serving it —
    # GLM never sees a different ticker set or prompt than Claude would have.
    assert claude_ok.generate.await_args.args[0] == glm_serves.generate.await_args.args[0]


# ── Circuit breaker preserved, at the real configured threshold ─────────────

@pytest.mark.asyncio
async def test_circuit_opens_after_configured_failure_threshold_then_routes_to_glm():
    assert config.CIRCUIT_FAILURES == 3
    claude = _fake_provider("claude", generate_error=ProviderUnavailable("down"))
    glm = _fake_provider("zai", generate_result=_resp("zai", model="glm-5.3-flash"))
    breaker = CircuitBreaker(failure_threshold=config.CIRCUIT_FAILURES,
                             cooldown_s=config.CIRCUIT_COOLDOWN_S)
    router = ProviderRouter([(claude, breaker), (glm, CircuitBreaker())])

    for _ in range(config.CIRCUIT_FAILURES):
        resp = await router.generate([{"role": "user", "content": "x"}])
        assert resp.provider == "zai"  # every call still falls over correctly

    assert breaker.state == "OPEN"
    claude.generate.reset_mock()

    # One more call: circuit is open, Claude must not even be attempted.
    resp = await router.generate([{"role": "user", "content": "x"}])
    assert resp.provider == "zai"
    claude.generate.assert_not_awaited()
