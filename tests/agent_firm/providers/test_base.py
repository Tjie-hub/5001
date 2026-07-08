from datetime import datetime, timezone

from engine.agent_firm.providers.base import ProviderCapabilities, ProviderResponse


def test_provider_capabilities_defaults():
    caps = ProviderCapabilities(
        supports_json_mode=True, supports_json_schema=False, supports_tools=True,
    )
    assert caps.max_context_tokens is None


def test_provider_response_round_trip():
    now = datetime.now(timezone.utc)
    resp = ProviderResponse(
        content="hi", provider="zai", model="glm-5.2", runtime_version="1.2.3",
        tokens_in=10, tokens_out=5, cost_usd=0.001, duration_s=1.5,
        request_id="req-1", timestamp=now,
    )
    assert resp.failover is False
    assert resp.timestamp == now


def test_provider_response_failover_defaults_false():
    resp = ProviderResponse(
        content="hi", provider="claude", model="sonnet", runtime_version="2.1.204",
        tokens_in=0, tokens_out=0, cost_usd=0.0, duration_s=0.5,
        timestamp=datetime.now(timezone.utc),
    )
    assert resp.failover is False
    assert resp.request_id is None
