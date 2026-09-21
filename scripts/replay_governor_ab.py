"""Deterministic A/B replay for the R-7 adaptive governor.

Why a simulation, not the live-API replay
------------------------------------------
scripts/replay_firm_offline_run.py hits the REAL z.ai endpoint. That is
non-deterministic, consumes real subscription quota, and is itself gated by the
very 5-hour / weekly usage windows under investigation — so it cannot produce a
clean, repeatable BEFORE/AFTER. (Run it by hand for a live smoke check.)

This harness instead isolates the ONE layer R-7 changes — issuance pacing — and
drives it deterministically. It uses:

  * the REAL new code: ProviderGovernor + _AIMDController + TokenBucketRateLimiter
    (engine/agent_firm/providers/governor.py), and
  * a faithful reconstruction of the OLD behavior: a fresh TokenBucketRateLimiter
    per "tick" (rate=3, burst=3) — exactly the per-ZAIProvider bucket that
    factory.build_router() rebuilt every evaluate_staged() tick before R-7.

Both are driven against a modeled z.ai burst limiter ("<=K requests per rolling
W-second window, else HTTP 429 code 1302") on a VIRTUAL clock (asyncio.sleep is
monkeypatched to advance simulated time), so the run is fast and identical every
time. The LLM pipeline itself is unchanged by R-7 and would only add noise, so
it is deliberately excluded.

Two scenarios, matching the two structural defects R-6 identified:

  A. Cross-tick burst reset — back-to-back scan jobs (run_agent_firm_gate then
     rank_bear_watchlist_and_notify run sequentially in one scan). A single tick
     stays under the limit for BOTH designs; the difference is only at tick
     boundaries, where the old per-tick bucket refills its burst allowance and
     re-bursts on top of the previous tick's tail.

  B. True limit below the configured rate — the provider's real short-window
     ceiling is stricter than the hand-set constant. The static bucket keeps
     bursting into it every window; the governor's AIMD loop converges below it.
"""
import asyncio
import sys
import time

sys.path.insert(0, "/home/tjiesar/10 Projects/idx-walkforward-5001")

from engine.agent_firm.providers.governor import (  # noqa: E402
    ProviderGovernor,
    TokenBucketRateLimiter,
    _AIMDController,
)

RATE_MAX = 3.0
RATE_MIN = 0.5
BURST = 3.0


class _VirtualClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


class _ZaiBurstLimiter:
    """Models z.ai's 1302: an attempt at time t is a 1302 if K or more attempts
    already fall inside the rolling window (t-W, t]. ALL attempts (success and
    1302 alike) count toward the window, as real per-window limiters do."""

    def __init__(self, window_s: float, max_in_window: int):
        self.W = window_s
        self.K = max_in_window
        self.attempts: list[float] = []

    def issue(self, t: float) -> bool:
        prior = sum(1 for ti in self.attempts if t - self.W < ti <= t)
        self.attempts.append(t)
        return prior < self.K  # True == accepted, False == 1302


async def _run(config_name, scenario, clock, limiter, *, adaptive):
    """Drive `scenario` through either the adaptive governor (adaptive=True) or
    the old per-tick static bucket (adaptive=False). Returns a metrics dict.

    asyncio.sleep is patched HERE (inside the running coroutine) to advance the
    virtual clock instead of really sleeping — patching it before the loop is
    created interferes with loop setup, so the swap must happen after."""
    real_sleep = asyncio.sleep

    async def _vsleep(dt, *a, **k):
        if dt:
            clock.t += dt

    asyncio.sleep = _vsleep  # type: ignore[assignment]
    try:
        return await _drive(config_name, scenario, clock, limiter, adaptive)
    finally:
        asyncio.sleep = real_sleep  # type: ignore[assignment]


async def _drive(config_name, scenario, clock, limiter, adaptive):
    ticks = scenario["ticks"]
    per_tick = scenario["reqs_per_tick"]
    gap = scenario["inter_tick_gap_s"]

    if adaptive:
        controller = _AIMDController(
            rate_initial=RATE_MAX, rate_min=RATE_MIN, rate_max=RATE_MAX, burst=BURST,
            ai_step=0.5, ai_interval_s=2.0, md_factor=0.5,
            post_decrease_cooldown_s=3.0, time_fn=clock,
        )
        governor = ProviderGovernor({"zai": controller})

    attempts = successes = rate_limits = 0
    for _tick in range(ticks):
        if not adaptive:
            # OLD behavior: a brand-new bucket every tick -> burst allowance
            # resets to full every scan job.
            static_bucket = TokenBucketRateLimiter(
                rate=RATE_MAX, capacity=BURST, time_fn=clock)
        for _req in range(per_tick):
            if adaptive:
                await governor.acquire("zai")
            else:
                await static_bucket.acquire()
            t = clock()
            attempts += 1
            if limiter.issue(t):
                successes += 1
                if adaptive:
                    governor.on_success("zai")
            else:
                rate_limits += 1
                if adaptive:
                    governor.on_rate_limit("zai")
        clock.t += gap  # next scan job starts ~immediately after this one

    metrics = {
        "config": config_name,
        "attempts": attempts,
        "successes": successes,
        "rate_limits_1302": rate_limits,
        "makespan_s": round(clock.t, 2),
    }
    if adaptive:
        snap = governor.snapshot()["zai"]
        metrics["final_rate_rps"] = snap["rate"]
        metrics["md_events"] = snap["md_events"]
        metrics["ai_events"] = snap["ai_events"]
    return metrics


def run_scenario(title, scenario):
    # BASELINE (pre-R-7: static per-tick bucket)
    clock_b = _VirtualClock()
    lim_b = _ZaiBurstLimiter(scenario["window_s"], scenario["max_in_window"])
    base = asyncio.run(
        _run("BASELINE (static per-tick bucket)", scenario, clock_b, lim_b,
             adaptive=False))
    # NEW (R-7: global adaptive governor)
    clock_g = _VirtualClock()
    lim_g = _ZaiBurstLimiter(scenario["window_s"], scenario["max_in_window"])
    gov = asyncio.run(
        _run("GOVERNOR (global adaptive)", scenario, clock_g, lim_g,
             adaptive=True))

    print("\n" + "=" * 78)
    print(title)
    print(f"  provider limit: <= {scenario['max_in_window']} attempts / "
          f"{scenario['window_s']}s window   |   workload: {scenario['ticks']} "
          f"ticks x {scenario['reqs_per_tick']} reqs, "
          f"{scenario['inter_tick_gap_s']}s apart")
    print("=" * 78)
    hdr = f"{'config':<34}{'attempts':>9}{'ok':>6}{'1302':>6}{'extra':>18}"
    print(hdr); print("-" * len(hdr))
    for m in (base, gov):
        extra = ""
        if "final_rate_rps" in m:
            extra = f"rate {m['final_rate_rps']}rps md={m['md_events']} ai={m['ai_events']}"
        print(f"{m['config']:<34}{m['attempts']:>9}{m['successes']:>6}"
              f"{m['rate_limits_1302']:>6}{extra:>18}")
    reduction = base["rate_limits_1302"] - gov["rate_limits_1302"]
    print(f"\n  1302 reduction: {base['rate_limits_1302']} -> "
          f"{gov['rate_limits_1302']}  ({reduction:+d})")
    return base, gov


SCENARIOS = {
    "A. Cross-tick burst reset (back-to-back scan jobs)": dict(
        window_s=1.0, max_in_window=6, ticks=6, reqs_per_tick=8,
        inter_tick_gap_s=0.05),
    "B. True provider limit below configured rate": dict(
        window_s=1.0, max_in_window=3, ticks=6, reqs_per_tick=8,
        inter_tick_gap_s=0.05),
}


def main():
    print("R-7 ADAPTIVE GOVERNOR — DETERMINISTIC A/B REPLAY")
    print(f"(virtual clock; real governor code; run at {time.strftime('%Y-%m-%d %H:%M')})")
    results = {}
    for title, scn in SCENARIOS.items():
        results[title] = run_scenario(title, scn)
    print("\n" + "=" * 78)
    print("SUMMARY")
    print("=" * 78)
    for title, (base, gov) in results.items():
        print(f"  {title}")
        print(f"    successful evals : {base['successes']} -> {gov['successes']}")
        print(f"    self-inflicted 1302: {base['rate_limits_1302']} -> "
              f"{gov['rate_limits_1302']}")


if __name__ == "__main__":
    main()
