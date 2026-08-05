"""Process-global adaptive provider governor (R-7 Tier 1).

The governor owns per-provider issuance pacing for the Agent Firm. Two
independent concerns:

  * a token bucket paces the ISSUE RATE (the fix that stopped z.ai HTTP 429
    code 1302 bursts), and
  * an AIMD controller adapts that rate to the provider's *actual*, drifting
    short-window limit — additive-increase while requests succeed,
    multiplicative-decrease the instant a 1302 lands.

Unlike the previous per-ZAIProvider bucket (rebuilt every evaluate_staged()
tick, so its burst allowance reset every scan), the governor is a process
singleton: its adaptive state survives router rebuilds, scheduler ticks, and
— critically — the fresh asyncio event loop that evaluate_staged() spins up
via asyncio.run() every tick.
"""
import asyncio
import time

import pytest

from engine.agent_firm.providers.governor import (
    ProviderGovernor,
    TokenBucketRateLimiter,
    _AIMDController,
    get_governor,
    reset_governor,
)


class FakeClock:
    """Deterministic monotonic clock for AIMD state transitions."""

    def __init__(self, t: float = 1000.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


def _controller(clock=None, **over):
    # AIMD *state* tests pass a frozen FakeClock; *pacing* tests that actually
    # await acquire() must use a real advancing clock or the bucket can never
    # refill (the sleep would never make progress).
    params = dict(
        rate_initial=3.0, rate_min=0.5, rate_max=3.0, burst=3.0,
        ai_step=0.5, ai_interval_s=10.0, md_factor=0.5,
        post_decrease_cooldown_s=30.0, time_fn=clock or time.monotonic,
    )
    params.update(over)
    return _AIMDController(**params)


# ── AIMD policy (deterministic clock) ────────────────────────────────────────

def test_on_rate_limit_multiplicatively_decreases_rate():
    clock = FakeClock()
    c = _controller(clock)
    assert c.rate == 3.0
    old, new = c.on_rate_limit()
    assert (old, new) == (3.0, 1.5)
    assert c.rate == 1.5
    assert c.snapshot()["md_events"] == 1


def test_repeated_rate_limits_floor_at_min():
    clock = FakeClock()
    c = _controller(clock, rate_min=0.5)
    for _ in range(10):
        c.on_rate_limit()
    assert c.rate == 0.5  # 3 -> 1.5 -> 0.75 -> 0.375(->clamped 0.5)
    assert c.rate >= 0.5


def test_on_success_does_not_increase_within_post_decrease_cooldown():
    clock = FakeClock()
    c = _controller(clock, post_decrease_cooldown_s=30.0)
    c.on_rate_limit()               # rate 1.5, last_decrease = now
    clock.advance(5.0)              # still inside the 30s cooldown
    changed = c.on_success()
    assert changed is None
    assert c.rate == 1.5


def test_on_success_increases_additively_after_cooldown_and_interval():
    clock = FakeClock()
    c = _controller(clock, ai_step=0.5, ai_interval_s=10.0,
                    post_decrease_cooldown_s=30.0)
    c.on_rate_limit()              # rate 1.5
    clock.advance(31.0)           # past the post-decrease cooldown
    old, new = c.on_success()
    assert (old, new) == (1.5, 2.0)
    assert c.snapshot()["ai_events"] == 1


def test_on_success_respects_additive_interval_between_increases():
    clock = FakeClock()
    c = _controller(clock, ai_step=0.5, ai_interval_s=10.0,
                    post_decrease_cooldown_s=0.0)
    c.on_rate_limit()             # rate 1.5
    clock.advance(1.0)
    assert c.on_success() == (1.5, 2.0)  # first increase
    clock.advance(1.0)                    # only 1s later — below ai_interval
    assert c.on_success() is None         # too soon to increase again
    clock.advance(10.0)
    assert c.on_success() == (2.0, 2.5)   # interval elapsed -> increases


def test_on_success_never_exceeds_rate_max():
    clock = FakeClock()
    c = _controller(clock, rate_max=3.0, post_decrease_cooldown_s=0.0)
    # Already at max: successes must not push above the hard ceiling.
    for _ in range(5):
        clock.advance(100.0)
        assert c.on_success() is None
    assert c.rate == 3.0


def test_recovery_climbs_gradually_back_toward_max():
    clock = FakeClock()
    c = _controller(clock, ai_step=0.5, ai_interval_s=10.0,
                    post_decrease_cooldown_s=10.0, rate_max=3.0)
    c.on_rate_limit()            # 1.5
    rates = []
    for _ in range(6):
        clock.advance(11.0)
        c.on_success()
        rates.append(c.rate)
    # Monotonic non-decreasing, additive, capped at max.
    assert rates == [2.0, 2.5, 3.0, 3.0, 3.0, 3.0]


# ── Token bucket primitive (wall clock, matches pre-existing tolerances) ──────

@pytest.mark.asyncio
async def test_token_bucket_allows_burst_up_to_capacity():
    lb = TokenBucketRateLimiter(rate=1.0, capacity=3)
    t0 = time.monotonic()
    for _ in range(3):
        await lb.acquire()
    assert time.monotonic() - t0 < 0.1


@pytest.mark.asyncio
async def test_token_bucket_paces_after_burst():
    lb = TokenBucketRateLimiter(rate=10.0, capacity=2)
    await lb.acquire()
    await lb.acquire()
    t0 = time.monotonic()
    await lb.acquire()
    elapsed = time.monotonic() - t0
    assert 0.08 <= elapsed < 0.5


@pytest.mark.asyncio
async def test_token_bucket_concurrent_acquire_is_safe():
    lb = TokenBucketRateLimiter(rate=5.0, capacity=2)
    t0 = time.monotonic()
    await asyncio.gather(*[lb.acquire() for _ in range(5)])
    elapsed = time.monotonic() - t0
    assert 0.4 <= elapsed < 1.5


@pytest.mark.asyncio
async def test_token_bucket_rate_is_mutable_after_construction():
    """AIMD adjusts the bucket's rate in place; a lowered rate must slow refill."""
    lb = TokenBucketRateLimiter(rate=1000.0, capacity=1)
    await lb.acquire()          # empty the single burst token
    lb.rate = 10.0              # AIMD drops the rate
    t0 = time.monotonic()
    await lb.acquire()          # next token now accrues at 10/s -> ~0.1s
    assert time.monotonic() - t0 >= 0.08


def test_token_bucket_terminates_under_exact_virtual_clock():
    """Regression (2026-08-05, found via scripts/replay_governor_ab.py's
    deterministic A/B replay hanging): under a virtual clock whose sleep
    advances time by EXACTLY the requested deficit -- no real-wall-clock
    jitter to mask float rounding -- repeated near-empty-bucket acquires can
    converge to a floating-point fixed point just below 1.0 token (e.g.
    0.9999999999999998) and spin forever recomputing an ever-shrinking
    deficit. The loop never truly suspends (each iteration's "sleep" is a
    synchronous clock bump), so not even asyncio.wait_for's own timeout can
    preempt it -- run the repro in a subprocess with a hard OS-level timeout
    so a regression here fails this test instead of hanging the suite."""
    import subprocess
    import sys
    import textwrap
    from pathlib import Path

    script = textwrap.dedent("""
        import asyncio
        from engine.agent_firm.providers.governor import TokenBucketRateLimiter

        class VClock:
            def __init__(self):
                self.t = 0.0
            def __call__(self):
                return self.t

        async def main():
            clock = VClock()
            async def vsleep(dt, *a, **k):
                if dt:
                    clock.t += dt
            asyncio.sleep = vsleep
            lb = TokenBucketRateLimiter(rate=3.0, capacity=3.0, time_fn=clock)
            for _ in range(20):
                await lb.acquire()

        asyncio.run(main())
    """)
    repo_root = Path(__file__).resolve().parents[3]
    try:
        result = subprocess.run(
            [sys.executable, "-c", script], timeout=10,
            capture_output=True, text=True, cwd=str(repo_root),
        )
    except subprocess.TimeoutExpired:
        pytest.fail(
            "TokenBucketRateLimiter.acquire() hung under an exact virtual "
            "clock -- floating-point convergence bug regressed"
        )
    assert result.returncode == 0, result.stderr


# ── Governor: routing between governed / ungoverned providers ────────────────

@pytest.mark.asyncio
async def test_ungoverned_provider_acquire_is_instant_noop():
    gov = ProviderGovernor({"zai": _controller(FakeClock())})
    t0 = time.monotonic()
    wait = await gov.acquire("claude")   # not in the controller map
    assert wait == 0.0
    assert time.monotonic() - t0 < 0.05
    # Feedback on an ungoverned provider is a silent no-op.
    gov.on_success("claude")
    gov.on_rate_limit("claude")


@pytest.mark.asyncio
async def test_governor_paces_governed_provider_after_burst():
    c = _controller(rate_initial=10.0, rate_max=10.0, burst=2.0)  # real clock
    gov = ProviderGovernor({"zai": c})
    await gov.acquire("zai")
    await gov.acquire("zai")     # burst exhausted
    t0 = time.monotonic()
    await gov.acquire("zai")     # must wait ~0.1s at 10/s
    assert 0.08 <= time.monotonic() - t0 < 0.5


@pytest.mark.asyncio
async def test_governor_rate_limit_feedback_decreases_pacing():
    clock = FakeClock()
    c = _controller(clock)
    gov = ProviderGovernor({"zai": c})
    gov.on_rate_limit("zai")
    assert c.rate == 1.5
    snap = gov.snapshot()["zai"]
    assert snap["rate"] == 1.5
    assert snap["md_events"] == 1
    assert snap["rate_max"] == 3.0


# ── Singleton / process-lifetime ─────────────────────────────────────────────

def test_get_governor_returns_singleton():
    reset_governor()
    g1 = get_governor()
    g2 = get_governor()
    assert g1 is g2
    reset_governor()
    assert get_governor() is not g1


def test_governor_state_survives_router_rebuild_across_event_loops():
    """THE core requirement: evaluate_staged() spins a fresh asyncio.run() loop
    every tick and rebuilds the router. The governor is a process singleton, so
    an adaptive decrease taken in one tick must still be in force in the next —
    and it must not blow up reusing state across two different event loops
    (which a loop-bound asyncio.Lock would). This test is deliberately sync so
    it can own the asyncio.run() calls, exactly as evaluate_staged() does."""
    reset_governor()

    async def tick_that_hits_rate_limit():
        gov = get_governor()          # same singleton every tick
        await gov.acquire("zai")
        gov.on_rate_limit("zai")
        return gov.snapshot()["zai"]["rate"]

    async def tick_that_reads_rate():
        gov = get_governor()
        await gov.acquire("zai")
        return gov.snapshot()["zai"]["rate"]

    rate_after_first = asyncio.run(tick_that_hits_rate_limit())   # new loop #1
    rate_in_second = asyncio.run(tick_that_reads_rate())          # new loop #2

    assert rate_after_first < 3.0          # decreased in tick 1
    assert rate_in_second == rate_after_first  # persisted into tick 2
    reset_governor()


@pytest.mark.asyncio
async def test_concurrent_acquire_does_not_double_spend():
    c = _controller(rate_initial=5.0, rate_max=5.0, burst=2.0)  # real clock
    gov = ProviderGovernor({"zai": c})
    t0 = time.monotonic()
    await asyncio.gather(*[gov.acquire("zai") for _ in range(5)])
    elapsed = time.monotonic() - t0
    # 2 burst instant + 3 paced at 5/s -> ~0.6s; never faster than the bucket.
    assert 0.4 <= elapsed < 1.5


def test_snapshot_exposes_telemetry_fields():
    gov = ProviderGovernor({"zai": _controller(FakeClock())})
    snap = gov.snapshot()["zai"]
    for key in ("rate", "rate_min", "rate_max", "ai_events", "md_events",
                "requests", "total_wait_s"):
        assert key in snap
