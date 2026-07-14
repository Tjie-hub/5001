"""Owns provider selection, ordering, and cross-provider failover (design
doc §4). Providers stay dumb; the Router never constructs them (see
factory.py).

Quota-aware routing (RCA 2026-07-10): when a provider reports a session/
usage-window limit, it is held out of rotation until the advertised reset
time (+ buffer) instead of being rediscovered-exhausted on every circuit
cooldown — during the incident the Router burned 2–4s per attempt re-probing
a provider whose own error message named the reset time. The hold is a
lightweight per-provider timestamp that coexists with (does not replace)
the Circuit Breaker.
"""

import datetime
import logging

from .. import config
from . import alerts
from .base import ProviderResponse
from .errors import ProviderException, ProviderSessionLimit, ProviderUnavailable
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


def _hold_until(reset_time: datetime.datetime | None) -> datetime.datetime:
    """Hold horizon for a session-limited provider: advertised reset + buffer,
    fallback duration when no reset was parseable, always capped by
    QUOTA_MAX_HOLD_S so a mis-parsed far-future reset can't bench a provider
    for days."""
    now = _now()
    if reset_time is None or reset_time.tzinfo is None:
        until = now + datetime.timedelta(seconds=config.QUOTA_FALLBACK_HOLD_S)
    else:
        until = reset_time + datetime.timedelta(seconds=config.QUOTA_RESET_BUFFER_S)
    cap = now + datetime.timedelta(seconds=config.QUOTA_MAX_HOLD_S)
    return min(max(until, now), cap)


class ProviderRouter:
    name = "router"

    def __init__(self, routed, db_path: str | None = None):
        self._routed = routed  # list[tuple[FirmLLMProvider, CircuitBreaker]]
        self._db_path = db_path
        # provider name -> {"until": aware dt, "reset_time": aware dt | None}
        self._quota_holds: dict[str, dict] = {}

    def model(self) -> str:
        return self._routed[0][0].model() if self._routed else ""

    async def health(self) -> bool:
        results = [await p.health() for p, _ in self._routed]
        return any(results)

    def provider_status(self) -> list[dict]:
        """Per-provider availability snapshot: WHY a provider is (un)available
        — session-limit hold (with resume time) or open circuit."""
        now = _now()
        out = []
        for provider, breaker in self._routed:
            hold = self._quota_holds.get(provider.name)
            on_hold = hold is not None and now < hold["until"]
            if on_hold:
                reason = f"session limit (resumes {hold['until'].isoformat()})"
            elif breaker.state == "OPEN":
                reason = "circuit open"
            else:
                reason = None
            out.append({
                "provider": provider.name,
                "circuit_state": breaker.state,
                "available": reason is None,
                "quota_hold_until": hold["until"].isoformat() if on_hold else None,
                "estimated_reset": (
                    hold["reset_time"].isoformat()
                    if on_hold and hold.get("reset_time") else None
                ),
                "reason": reason,
            })
        return out

    def _on_session_limit(self, provider, err: ProviderSessionLimit) -> None:
        until = _hold_until(err.reset_time)
        self._quota_holds[provider.name] = {
            "until": until, "reset_time": err.reset_time,
        }
        reset_str = err.reset_time.isoformat() if err.reset_time else "unknown"
        logger.warning(
            "Provider: %s | Status: Session Limit Reached | Reset: %s | "
            "Action: held out of rotation until %s",
            provider.name, reset_str, until.isoformat(),
        )
        try:
            model = provider.model()
            model = model if isinstance(model, str) else None
        except Exception:
            model = None
        log_provider_event(ProviderEvent(
            event_type="provider_session_limit", timestamp=_now(),
            provider=provider.name, model=model,
            reason=str(err), reset_time=err.reset_time,
        ), db_path=self._db_path)
        try:
            alerts.session_limit_alert(provider.name, err.reset_time,
                                       model=provider.model())
        except Exception as alert_err:  # alerting must not break routing
            logger.debug("session-limit alert failed: %s", alert_err)

    async def generate(self, messages, *, timeout=None) -> ProviderResponse:
        last_err: ProviderException | None = None
        for i, (provider, breaker) in enumerate(self._routed):
            hold = self._quota_holds.get(provider.name)
            if hold is not None and config.QUOTA_HOLD_ENABLED and _now() < hold["until"]:
                logger.info(
                    "Provider: %s | Status: On session-limit hold | "
                    "Resumes: %s | Action: skipped",
                    provider.name, hold["until"].isoformat(),
                )
                log_provider_event(ProviderEvent(
                    event_type="provider_skipped", timestamp=_now(),
                    provider=provider.name,
                    reason=f"session limit hold — resumes {hold['until'].isoformat()}",
                    reset_time=hold.get("reset_time"),
                ), db_path=self._db_path)
                continue

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
                if isinstance(err, ProviderSessionLimit):
                    self._on_session_limit(provider, err)
                else:
                    event_type = (
                        "provider_timeout" if type(err).__name__ == "ProviderTimeout"
                        else "provider_failed"
                    )
                    log_provider_event(ProviderEvent(
                        event_type=event_type, timestamp=_now(),
                        provider=provider.name,
                        reason=f"[{getattr(err, 'category', 'unknown')}] {err}",
                    ), db_path=self._db_path)
                if just_opened:
                    log_provider_event(ProviderEvent(
                        event_type="provider_circuit_open", timestamp=_now(),
                        provider=provider.name, reason=str(err),
                    ), db_path=self._db_path)
                continue
            else:
                if provider.name in self._quota_holds:
                    # First success after a session-limit hold: window is back.
                    self._quota_holds.pop(provider.name, None)
                    logger.info(
                        "Provider: %s | Status: Restored | Action: back in rotation",
                        provider.name,
                    )
                    log_provider_event(ProviderEvent(
                        event_type="provider_restored", timestamp=_now(),
                        provider=provider.name, model=resp.model,
                    ), db_path=self._db_path)
                    try:
                        alerts.provider_restored_alert(provider.name)
                    except Exception as alert_err:
                        logger.debug("restored alert failed: %s", alert_err)
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

        if len(self._routed) > 1:
            try:
                # RCA 2026-07-13: a transient burst can open every circuit in
                # the same second, but the providers aren't actually "down" —
                # they recover within the cooldown. Only page when every
                # provider is in a lasting unavailable state (quota hold or
                # OPEN circuit); a single request that fails through both
                # providers under load logs an event but stays quiet. The
                # per-request `provider_failed` events still surface bursts.
                status = self.provider_status()
                all_unavailable = all(not s["available"] for s in status)
                if all_unavailable:
                    alerts.all_providers_unavailable_alert(
                        [p.name for p, _ in self._routed])
                else:
                    logger.info(
                        "Provider: router exhausted but not all providers "
                        "unavailable; suppressing all-down alert. status=%s",
                        status,
                    )
            except Exception as alert_err:
                logger.debug("all-unavailable alert failed: %s", alert_err)
        raise last_err or ProviderUnavailable("no providers available")
