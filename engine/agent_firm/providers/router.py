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
from .errors import (
    ProviderException, ProviderRateLimited, ProviderSessionLimit,
    ProviderUnavailable,
)
from .events import ProviderEvent, log_provider_event
from .governor import get_governor

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


def _parse_utc(s: str | None) -> datetime.datetime | None:
    """Parse a persisted '%Y-%m-%d %H:%M:%S' UTC string (the format
    events.py's `_utc_str` writes) back into an aware UTC datetime. Returns
    None for anything unparseable (missing column, corrupt row) rather than
    raising -- hydration must degrade, never crash."""
    if not s:
        return None
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=datetime.timezone.utc)
    except (ValueError, TypeError):
        return None


def _hydrate_quota_holds(db_path: str) -> dict[str, dict]:
    """Rebuild in-memory quota holds from the persisted provider_events table
    so a freshly-constructed router (evaluate_staged() rebuilds one every
    scheduler tick) honors a hold a PREVIOUS tick already discovered, instead
    of re-probing an exhausted provider until its own failure re-teaches it
    (audit 2026-07-21: the exact gap that caused the incident).

    Pure function of the DB: reads the latest ('provider_session_limit' |
    'provider_restored') event per provider, in insertion order, so N
    duplicate session_limit rows from a fan-out collapse to one hold and a
    'provider_restored' as the latest event clears any hold. Reconstructs
    the same {"until", "reset_time"} shape `_on_session_limit` writes live,
    anchoring the fallback window and the QUOTA_MAX_HOLD_S safety cap to the
    persisted event's own timestamp (not "now") so a hold's expiry is a fixed
    fact of when it happened, not when it happens to be checked. Already-
    expired holds are dropped, not hydrated -- no stale-hold-forever.

    Fails soft to {} on any error (missing file, missing/pre-Phase-1-schema
    table, corrupt row) -- hydration must never crash router construction.
    """
    from data.db import connect as _db_connect

    try:
        conn = _db_connect(db_path)
    except Exception:
        return {}
    try:
        try:
            rows = conn.execute(
                "SELECT provider, event_type, reset_time, created_at "
                "FROM provider_events "
                "WHERE event_type IN ('provider_session_limit', 'provider_restored') "
                "ORDER BY id ASC"
            ).fetchall()
        except Exception:
            return {}  # missing table/db (pre-Phase-1 schema) -- degrade silently
    finally:
        conn.close()

    latest: dict[str, tuple] = {}
    for provider, event_type, reset_time_s, created_at_s in rows:
        latest[provider] = (event_type, reset_time_s, created_at_s)

    now = _now()
    holds: dict[str, dict] = {}
    for provider, (event_type, reset_time_s, created_at_s) in latest.items():
        if event_type != "provider_session_limit":
            continue
        reset_time = _parse_utc(reset_time_s)
        anchor = _parse_utc(created_at_s) or now
        if reset_time is not None:
            until = reset_time + datetime.timedelta(seconds=config.QUOTA_RESET_BUFFER_S)
        else:
            until = anchor + datetime.timedelta(seconds=config.QUOTA_FALLBACK_HOLD_S)
        cap = anchor + datetime.timedelta(seconds=config.QUOTA_MAX_HOLD_S)
        until = min(until, cap)
        if until <= now:
            continue  # expired -- do not hydrate a stale hold
        holds[provider] = {"until": until, "reset_time": reset_time}
    return holds


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


def _hold_until_from_event(
    reset_time: datetime.datetime | None, failure_time: datetime.datetime,
) -> datetime.datetime:
    """Hold horizon reconstructed from a PERSISTED session-limit event
    (audit 2026-07-21). ``failure_time`` is the event's created_at — used as
    the reference for BOTH the no-reset fallback window AND the
    ``QUOTA_MAX_HOLD_S`` safety cap, matching the live ``_hold_until`` which
    anchors both to ``_now()`` (≈ the moment the live decision was made).
    Re-anchoring the fallback to ``_now()`` on every rebuild would silently
    extend z.ai's 5-hour window by 15 minutes per tick.

    Regression found 2026-07-21 (post-deploy): the cap was previously
    anchored to ``reset_time``, so a far-future reset (e.g. a mis-parsed
    30-day horizon) defeated the cap entirely — the hold horizon became
    ``reset_time + 6h`` ≈ 30 days. Anchoring the cap to ``failure_time``
    (the moment the live router actually decided to hold) preserves the
    cap's safety purpose across the rebuild boundary.
    """
    if reset_time is not None and reset_time.tzinfo is not None:
        until = reset_time + datetime.timedelta(seconds=config.QUOTA_RESET_BUFFER_S)
    else:
        until = failure_time + datetime.timedelta(seconds=config.QUOTA_FALLBACK_HOLD_S)
    cap = failure_time + datetime.timedelta(seconds=config.QUOTA_MAX_HOLD_S)
    return min(until, cap)


def _parse_utc(text: str | None) -> datetime.datetime | None:
    """Parse the ``%Y-%m-%d %H:%M:%S`` UTC string ``events._persist`` writes.
    Returns None on anything that isn't a parseable timestamp so a corrupt
    row can't crash hydration."""
    if not text:
        return None
    try:
        return datetime.datetime.strptime(text, "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=datetime.timezone.utc)
    except (ValueError, TypeError):
        return None


def _hydrate_quota_holds(db_path: str) -> dict[str, dict]:
    """Reconstruct ``_quota_holds`` from the persisted provider_events table.

    The Router writes a ``provider_session_limit`` event (with reset_time and
    a UTC created_at) every time a provider is held out of rotation, and a
    ``provider_restored`` event the first time it succeeds again. This reads
    the LAST such event per provider and rebuilds the hold only when the most
    recent event is still a session_limit AND its hold horizon has not yet
    elapsed — so a freshly-built Router (the firm rebuilds one every
    ``evaluate_staged()`` tick) does NOT re-probe providers whose quota window
    is still exhausted.

    Resilience: any DB/schema/parse error returns an empty dict (log-only) —
    hydration is a correctness optimization, not a hard dependency. A missing
    or unreadable table simply falls back to the pre-2026-07-21 behavior.
    """
    from ..tools.sqlite_query import query
    try:
        rows = query(
            db_path,
            "SELECT provider, event_type, reset_time, created_at FROM ( "
            "  SELECT provider, event_type, reset_time, created_at, "
            "         ROW_NUMBER() OVER (PARTITION BY provider ORDER BY id DESC) AS rn "
            "  FROM provider_events "
            "  WHERE event_type IN ('provider_session_limit', 'provider_restored') "
            ") WHERE rn = 1",
            (),
        )
    except Exception as err:
        # sqlite_query re-raises; a missing table (pre-Phase-1 schema) or a
        # locked DB must not break routing — degrade to in-memory-only.
        logger.warning("quota hold hydration skipped (db unreadable): %s", err)
        return {}

    now = _now()
    holds: dict[str, dict] = {}
    for row in rows:
        if row["event_type"] != "provider_session_limit":
            continue  # most recent event was a recovery -> provider is available
        reset_time = _parse_utc(row.get("reset_time"))
        failure_time = _parse_utc(row.get("created_at")) or now
        until = _hold_until_from_event(reset_time, failure_time)
        if until <= now:
            continue  # hold already expired; nothing to reconstruct
        holds[row["provider"]] = {"until": until, "reset_time": reset_time}
        logger.info(
            "Provider: %s | Status: Hydrated session-limit hold | Resumes: %s",
            row["provider"], until.isoformat(),
        )
    return holds


class ProviderRouter:
    name = "router"

    def __init__(self, routed, db_path: str | None = None, governor=None):
        self._routed = routed  # list[tuple[FirmLLMProvider, CircuitBreaker]]
        self._db_path = db_path
        # Process-global adaptive issue-rate governor (R-7 Tier 1). The Router
        # is rebuilt every evaluate_staged() tick, but the governor is NOT — it
        # is a singleton whose AIMD state persists across ticks/loops. Injectable
        # for tests; defaults to the process singleton.
        self._governor = governor if governor is not None else get_governor()
        # provider name -> {"until": aware dt, "reset_time": aware dt | None}
        # Hydrated eagerly (not lazily on first generate()) from provider_events
        # so a fresh router built against an existing db_path honors a hold a
        # PREVIOUS tick already discovered (audit 2026-07-21) -- every caller
        # already passes db_path (factory.build_router() included), so a
        # freshly-built router observing an in-flight hold is the norm, not an
        # edge case. db_path=None (unit tests without a db) hydrates to {}.
        self._quota_holds: dict[str, dict] = (
            _hydrate_quota_holds(db_path) if db_path else {}
        )

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

            # Ask the global governor for issuance permission BEFORE dispatch
            # (paces this provider's request rate; no-op for un-governed
            # providers). Placed after the hold/circuit/cap checks so a skipped
            # provider never consumes a pacing token.
            await self._governor.acquire(provider.name, db_path=self._db_path)

            try:
                resp = await provider.generate(messages, timeout=timeout)
            except ProviderException as err:
                just_opened = breaker.record_failure()
                err.provider = provider.name  # trace attribution (audit P-2)
                last_err = err
                if isinstance(err, ProviderRateLimited):
                    # HTTP 429 / code 1302 burst limit -> AIMD multiplicative
                    # decrease. NB: ProviderSessionLimit is NOT a subclass of
                    # ProviderRateLimited, so a usage-window limit (1308/1310)
                    # takes the quota-hold path below, not a rate decrease.
                    self._governor.on_rate_limit(provider.name, db_path=self._db_path)
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
                # Successful request -> AIMD additive increase (rate-limited by
                # the governor's own interval/cooldown so it recovers gradually).
                self._governor.on_success(provider.name, db_path=self._db_path)
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
