"""Process-global adaptive provider governor (R-7 Tier 1).

Why this exists
---------------
z.ai's binding production limit is HTTP 429 code 1302 ("Rate limit reached for
requests") — a limit on request COUNT inside a short sliding window, empirically
low and *drifting* (it is shared with other consumers of the account). The
R-6 execution review found two structural defects in the previous mitigation:

  1. The token bucket that paces issuance lived on the ZAIProvider instance,
     and factory.build_router() rebuilds that provider every evaluate_staged()
     tick — so the burst allowance reset to full every scan, and two
     back-to-back scan jobs could double-burst z.ai in the same second. This is
     the SAME cross-tick state-loss bug class that the quota-hold hydration
     work already fixed for session limits (router.py).
  2. The pacing rate was a hand-tuned constant re-guessed after each incident.
     A fixed constant against an unknown, moving ceiling is provably either too
     conservative (wastes throughput) or too aggressive (trips 1302). Only a
     closed feedback loop tracks a moving target.

The governor fixes both: it is a **process singleton** (state survives router
rebuilds and scheduler ticks) and it is **AIMD-adaptive** (additive-increase
while requests succeed, multiplicative-decrease the instant a 1302 lands —
the standard control law for exactly this situation: TCP congestion control,
AWS SDK adaptive retry mode).

Cross-event-loop safety (load-bearing)
--------------------------------------
evaluate_staged() calls asyncio.run() — a FRESH event loop — every tick. A
process-lifetime object that held an ``asyncio.Lock`` would raise "got Future
attached to a different loop" the second tick reused it. So the pacing critical
section deliberately uses **no lock**: the token math contains no ``await``, and
Python's cooperative scheduling therefore makes read-modify-write of the token
count atomic with respect to other coroutines — the same guarantee the
CircuitBreaker documents and relies on. The only ``await`` is the sleep, which
happens after the coroutine has released its claim. ``test_governor.py``'s
cross-loop test fails if a loop-bound lock is ever reintroduced.

Scope (Tier 1 only)
-------------------
This governs issue RATE. Per-provider CONCURRENCY stays where it is (the
provider's semaphore) — concurrency has no cross-tick burst-reset failure mode
under the single-worker scheduler, so moving it would only widen the change.
Batching, priority queues, and weighted multi-provider scheduling (Tier 2/3)
are explicitly out of scope.
"""

import logging
import time
from typing import Callable

from .. import config
from .events import ProviderEvent, log_provider_event

logger = logging.getLogger("agent_firm.providers.governor")


class TokenBucketRateLimiter:
    """Async token bucket — paces request ISSUE RATE independently of
    concurrency. ``rate`` is a plain attribute so the AIMD controller can
    adjust it in place (a lowered rate slows refill on the next acquire).

    No lock: the token math has no ``await`` inside it, so cooperative
    scheduling makes the read-modify-write atomic w.r.t. other coroutines
    (see module docstring on cross-loop safety). ``time_fn`` is injectable so
    AIMD/timing is deterministic under test.
    """

    def __init__(self, rate: float, capacity: float,
                 time_fn: Callable[[], float] = time.monotonic) -> None:
        if rate <= 0 or capacity <= 0:
            raise ValueError(
                f"rate and capacity must be > 0; got rate={rate} capacity={capacity}")
        self.rate = rate            # tokens per second (mutable; AIMD writes it)
        self.capacity = capacity    # max tokens (burst allowance)
        self._tokens = capacity
        self._last: float | None = None
        self._time = time_fn

    # Floating-point tolerance for the "have we accrued a full token" check.
    # Under a real wall clock, timer jitter always overshoots the requested
    # sleep, so this never matters. Under an EXACT clock (a deterministic
    # test/replay harness whose sleep advances time by precisely the
    # requested deficit) the accrual math can converge to a fixed point a
    # few ULPs below 1.0 -- e.g. 0.9999999999999998 -- and an exact >= 1.0
    # comparison spins forever recomputing an ever-shrinking deficit that
    # never quite closes the gap (found via scripts/replay_governor_ab.py's
    # deterministic A/B replay hanging, 2026-08-05).
    _READY_EPSILON = 1e-9

    async def acquire(self) -> float:
        """Block until one token is available, then consume it. Returns the
        total seconds spent waiting (0.0 when a burst token was free)."""
        import asyncio
        waited = 0.0
        while True:
            now = self._time()
            if self._last is not None:
                self._tokens = min(
                    self.capacity, self._tokens + (now - self._last) * self.rate)
            self._last = now
            if self._tokens >= 1.0 - self._READY_EPSILON:
                self._tokens = max(0.0, self._tokens - 1.0)
                return waited
            deficit = (1.0 - self._tokens) / self.rate
            waited += deficit
            await asyncio.sleep(deficit)


class _AIMDController:
    """Per-provider adaptive pacing: a token bucket whose rate is moved by an
    additive-increase / multiplicative-decrease loop.

    * on_rate_limit() — a 1302 landed: rate = max(min, rate * md_factor),
      immediately, and stamp last_decrease.
    * on_success() — a request succeeded: increase by ai_step, but only once
      per ai_interval_s AND only after post_decrease_cooldown_s has elapsed
      since the last decrease (this is what prevents oscillation), never above
      rate_max.

    Starting rate defaults to rate_max so steady-state pacing is identical to
    the pre-governor constant (no throughput regression); the loop only ever
    pulls the rate *down* on a 1302 and lets it recover.
    """

    def __init__(self, rate_initial: float, rate_min: float, rate_max: float,
                 burst: float, ai_step: float, ai_interval_s: float,
                 md_factor: float, post_decrease_cooldown_s: float,
                 time_fn: Callable[[], float] = time.monotonic) -> None:
        if not (0 < rate_min <= rate_max):
            raise ValueError(
                f"require 0 < rate_min <= rate_max; got min={rate_min} max={rate_max}")
        if not (0 < md_factor < 1):
            raise ValueError(f"md_factor must be in (0,1); got {md_factor}")
        self.rate_min = rate_min
        self.rate_max = rate_max
        self.ai_step = ai_step
        self.ai_interval_s = ai_interval_s
        self.md_factor = md_factor
        self.post_decrease_cooldown_s = post_decrease_cooldown_s
        self._time = time_fn
        self._bucket = TokenBucketRateLimiter(
            rate=min(max(rate_initial, rate_min), rate_max),
            capacity=burst, time_fn=time_fn,
        )
        self._last_increase: float | None = None
        self._last_decrease: float | None = None
        # telemetry counters
        self._ai_events = 0
        self._md_events = 0
        self._requests = 0
        self._total_wait_s = 0.0

    @property
    def rate(self) -> float:
        return self._bucket.rate

    async def acquire(self) -> float:
        waited = await self._bucket.acquire()
        self._requests += 1
        self._total_wait_s += waited
        return waited

    def on_rate_limit(self) -> tuple[float, float]:
        """Multiplicative decrease. Returns (old_rate, new_rate)."""
        old = self._bucket.rate
        new = max(self.rate_min, old * self.md_factor)
        self._bucket.rate = new
        self._last_decrease = self._time()
        self._md_events += 1
        return old, new

    def on_success(self) -> tuple[float, float] | None:
        """Additive increase, gated by interval + post-decrease cooldown.
        Returns (old_rate, new_rate) if the rate moved, else None."""
        now = self._time()
        if self._bucket.rate >= self.rate_max:
            return None
        if self._last_decrease is not None and \
                now - self._last_decrease < self.post_decrease_cooldown_s:
            return None
        if self._last_increase is not None and \
                now - self._last_increase < self.ai_interval_s:
            return None
        old = self._bucket.rate
        new = min(self.rate_max, old + self.ai_step)
        self._bucket.rate = new
        self._last_increase = now
        self._ai_events += 1
        return old, new

    def snapshot(self) -> dict:
        return {
            "rate": round(self._bucket.rate, 4),
            "rate_min": self.rate_min,
            "rate_max": self.rate_max,
            "ai_events": self._ai_events,
            "md_events": self._md_events,
            "requests": self._requests,
            "total_wait_s": round(self._total_wait_s, 4),
        }


class ProviderGovernor:
    """Routes issuance pacing to the right per-provider AIMD controller.

    A provider with no controller (e.g. Claude, whose subprocess CLI has no
    HTTP burst limit — its constraint is the subscription window handled by the
    Router's quota holds) is un-governed: acquire() is an instant no-op and
    feedback is ignored.
    """

    def __init__(self, controllers: dict[str, _AIMDController]) -> None:
        self._controllers = controllers

    async def acquire(self, provider: str, *, db_path: str | None = None) -> float:
        c = self._controllers.get(provider)
        if c is None:
            return 0.0
        return await c.acquire()

    def on_success(self, provider: str, *, db_path: str | None = None) -> None:
        c = self._controllers.get(provider)
        if c is None:
            return
        change = c.on_success()
        if change is not None:
            old, new = change
            logger.info("Governor: %s | recovery | rate %.2f -> %.2f rps",
                        provider, old, new)
            self._log(provider, "governor_rate_increase",
                      f"recovery: rate {old:.2f} -> {new:.2f} rps", db_path)

    def on_rate_limit(self, provider: str, *, db_path: str | None = None) -> None:
        c = self._controllers.get(provider)
        if c is None:
            return
        old, new = c.on_rate_limit()
        logger.warning("Governor: %s | 429/1302 | rate %.2f -> %.2f rps",
                       provider, old, new)
        self._log(provider, "governor_rate_decrease",
                  f"429/1302: rate {old:.2f} -> {new:.2f} rps", db_path)

    def snapshot(self) -> dict[str, dict]:
        return {name: c.snapshot() for name, c in self._controllers.items()}

    @staticmethod
    def _log(provider: str, event_type: str, reason: str,
             db_path: str | None) -> None:
        import datetime
        try:
            log_provider_event(ProviderEvent(
                event_type=event_type,
                timestamp=datetime.datetime.now(datetime.timezone.utc),
                provider=provider, reason=reason,
            ), db_path=db_path)
        except Exception as err:  # telemetry must never break routing
            logger.debug("governor telemetry log failed: %s", err)


# ── Process singleton ────────────────────────────────────────────────────────

_GOVERNOR: ProviderGovernor | None = None


def _build_from_config() -> ProviderGovernor:
    """Construct the governor from AGENT_FIRM_* config. Only providers named in
    GOVERNOR_PROVIDERS get an AIMD controller; everything else is un-governed."""
    controllers: dict[str, _AIMDController] = {}
    if config.GOVERNOR_ENABLED:
        for name in config.GOVERNOR_PROVIDERS:
            controllers[name] = _AIMDController(
                rate_initial=config.GOVERNOR_RATE_MAX,   # start at the ceiling
                rate_min=config.GOVERNOR_RATE_MIN,
                rate_max=config.GOVERNOR_RATE_MAX,
                burst=config.GOVERNOR_BURST,
                ai_step=config.GOVERNOR_AI_STEP,
                ai_interval_s=config.GOVERNOR_AI_INTERVAL_S,
                md_factor=config.GOVERNOR_MD_FACTOR,
                post_decrease_cooldown_s=config.GOVERNOR_POST_DECREASE_COOLDOWN_S,
            )
    return ProviderGovernor(controllers)


def get_governor() -> ProviderGovernor:
    """Return the process-global governor, building it once from config."""
    global _GOVERNOR
    if _GOVERNOR is None:
        _GOVERNOR = _build_from_config()
    return _GOVERNOR


def reset_governor() -> None:
    """Drop the singleton so the next get_governor() rebuilds from current
    config. Test hook only — production never resets mid-process."""
    global _GOVERNOR
    _GOVERNOR = None
