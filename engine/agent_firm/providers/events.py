"""Structured, JSON-loggable provider decision events (design doc §7).
Machine-parseable for a future log shipper (ELK/Grafana/etc.) without
adding any new logging infra now."""

import logging
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel

logger = logging.getLogger("agent_firm.providers")

EventType = Literal[
    "provider_selected", "provider_failed", "provider_timeout",
    "provider_failover", "provider_circuit_open",
    "provider_circuit_closed", "provider_quota_exceeded",
]


class ProviderEvent(BaseModel):
    event_type: EventType
    timestamp: datetime
    provider: str
    model: Optional[str] = None
    reason: Optional[str] = None
    duration_s: Optional[float] = None
    request_id: Optional[str] = None
    failover: bool = False


def log_provider_event(event: ProviderEvent) -> None:
    logger.info(event.model_dump_json())
