"""Owns provider selection, ordering, and cross-provider failover (design
doc §4). Providers stay dumb; the Router never constructs them (see
factory.py)."""

import datetime
import logging

from .. import config
from .base import ProviderResponse
from .errors import ProviderException, ProviderUnavailable
from .events import ProviderEvent, log_provider_event

logger = logging.getLogger("agent_firm.providers.router")


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _claude_daily_call_count(db_path: str) -> int:
    from ..tools.sqlite_query import query
    try:
        rows = query(
            db_path,
            "SELECT COUNT(*) AS c FROM agent_traces WHERE provider='claude' "
            "AND DATE(created_at) = ?",
            (datetime.date.today().isoformat(),),
        )
        return int(rows[0]["c"]) if rows else 0
    except Exception:
        return 0


class ProviderRouter:
    name = "router"

    def __init__(self, routed, db_path: str | None = None):
        self._routed = routed  # list[tuple[FirmLLMProvider, CircuitBreaker]]
        self._db_path = db_path

    def model(self) -> str:
        return self._routed[0][0].model() if self._routed else ""

    async def health(self) -> bool:
        results = [await p.health() for p, _ in self._routed]
        return any(results)

    async def generate(self, messages, *, timeout=None) -> ProviderResponse:
        last_err: ProviderException | None = None
        for i, (provider, breaker) in enumerate(self._routed):
            if not breaker.allow_request():
                log_provider_event(ProviderEvent(
                    event_type="provider_failover", timestamp=_now(),
                    provider=provider.name, reason="circuit open",
                ), db_path=self._db_path)
                continue

            if provider.name == "claude" and self._db_path is not None:
                if _claude_daily_call_count(self._db_path) >= config.CLAUDE_MAX_CALLS_PER_DAY:
                    breaker.release_trial()
                    log_provider_event(ProviderEvent(
                        event_type="provider_quota_exceeded", timestamp=_now(),
                        provider=provider.name, reason="daily call cap reached",
                    ), db_path=self._db_path)
                    continue

            try:
                resp = await provider.generate(messages, timeout=timeout)
            except ProviderException as err:
                just_opened = breaker.record_failure()
                err.provider = provider.name  # trace attribution (audit P-2)
                last_err = err
                event_type = (
                    "provider_timeout" if type(err).__name__ == "ProviderTimeout"
                    else "provider_failed"
                )
                log_provider_event(ProviderEvent(
                    event_type=event_type, timestamp=_now(),
                    provider=provider.name, reason=str(err),
                ), db_path=self._db_path)
                if just_opened:
                    log_provider_event(ProviderEvent(
                        event_type="provider_circuit_open", timestamp=_now(),
                        provider=provider.name, reason=str(err),
                    ), db_path=self._db_path)
                continue
            else:
                just_closed = breaker.record_success()
                if just_closed:
                    log_provider_event(ProviderEvent(
                        event_type="provider_circuit_closed", timestamp=_now(),
                        provider=provider.name,
                    ), db_path=self._db_path)
                resp.failover = i > 0
                log_provider_event(ProviderEvent(
                    event_type="provider_failover" if resp.failover else "provider_selected",
                    timestamp=_now(), provider=provider.name, model=resp.model,
                    duration_s=resp.duration_s, request_id=resp.request_id,
                    failover=resp.failover,
                ), db_path=self._db_path)
                return resp
        raise last_err or ProviderUnavailable("no providers available")
