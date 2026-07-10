"""Structured, JSON-loggable provider decision events (design doc §7).
Machine-parseable for a future log shipper (ELK/Grafana/etc.) without
adding any new logging infra now.

Persistence (audit 2026-07-10 P-2): when the caller supplies a db_path the
event is ALSO written to the provider_events table — the table existed since
Phase 1 of the provider work but had no writer, so providers/metrics.py
failover/circuit stats always read zero. The Router passes its db_path;
callers without one (unit tests, ad-hoc) stay log-only, keeping the suite
hermetic."""

import logging
from datetime import datetime, timezone
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


def log_provider_event(event: ProviderEvent, db_path: Optional[str] = None) -> None:
    logger.info(event.model_dump_json())
    if db_path:
        _persist(event, db_path)


def _persist(event: ProviderEvent, db_path: str) -> None:
    """Best-effort INSERT into provider_events. Never raises — telemetry loss
    must not break a provider call."""
    try:
        from data.db import connect
        conn = connect(db_path)
        try:
            with conn:
                conn.execute(
                    "INSERT INTO provider_events "
                    "(event_type, provider, model, reason, duration_s, "
                    "request_id, failover, created_at) VALUES (?,?,?,?,?,?,?,?)",
                    (
                        event.event_type, event.provider, event.model,
                        event.reason, event.duration_s, event.request_id,
                        int(event.failover),
                        event.timestamp.astimezone(timezone.utc)
                        .strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
        finally:
            conn.close()
    except Exception as err:
        logger.warning("provider_event persist failed (event logged above): %s", err)
