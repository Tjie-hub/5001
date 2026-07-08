import json
import logging
from datetime import datetime, timezone

from engine.agent_firm.providers.events import ProviderEvent, log_provider_event


def test_log_provider_event_writes_json_line(caplog):
    event = ProviderEvent(
        event_type="provider_failover", timestamp=datetime.now(timezone.utc),
        provider="claude", model="sonnet", reason="circuit open",
        duration_s=1.2, request_id="req-1", failover=True,
    )
    with caplog.at_level(logging.INFO, logger="agent_firm.providers"):
        log_provider_event(event)
    assert len(caplog.records) == 1
    parsed = json.loads(caplog.records[0].message)
    assert parsed["event_type"] == "provider_failover"
    assert parsed["provider"] == "claude"
    assert parsed["reason"] == "circuit open"
