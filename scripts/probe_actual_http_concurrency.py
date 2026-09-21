"""Instrumented short replay — 3 candidates only — that measures ACTUAL peak
concurrent in-flight HTTP requests to z.ai (inside the semaphore).

Adds a wrapper around the ZAIProvider's _client.chat.completions.create to
count concurrent HTTP calls. If the peak exceeds ZAI_MAX_CONCURRENT, the
semaphore is broken. If the peak stays <=4 yet 1302s still occur, z.ai's
cap is lower than 4 under real workload (token size, model load, etc.).
"""
import asyncio
import os
import sys
import time

sys.path.insert(0, "/home/tjiesar/10 Projects/idx-walkforward-5001")
os.environ["AGENT_FIRM_ENV_PATH"] = "/home/tjiesar/10 Projects/idx-walkforward-5001/.env"

from engine.agent_firm import firm as firm_mod
from engine.agent_firm import config as cfg
from engine.agent_firm.providers.factory import build_router
from engine.agent_firm.schemas import SignalCandidate

TICKERS = ["CDIA", "ADRO", "JGLE"]  # small sample

# Build the router and instrument the zai provider's HTTP layer.
router = build_router()
for prov, _ in router._routed:
    if prov.name == "zai":
        zai = prov
        break

# Wrap the SDK create() to count concurrent in-flight HTTP calls.
state = {"inflight": 0, "peak": 0, "history": []}
orig_create = zai._client.chat.completions.create

async def counting_create(*args, **kwargs):
    state["inflight"] += 1
    state["history"].append(("start", time.monotonic(), state["inflight"]))
    if state["inflight"] > state["peak"]:
        state["peak"] = state["inflight"]
    try:
        return await orig_create(*args, **kwargs)
    finally:
        state["inflight"] -= 1
        state["history"].append(("end", time.monotonic(), state["inflight"]))

zai._client.chat.completions.create = counting_create
print(f"Instrumented zai. semaphore={zai._semaphore._value} rate_limit={zai._rate_limiter.rate}/s cap={zai._rate_limiter.capacity}")

# Patch the router into the firm
candidates = [
    SignalCandidate(
        ticker=t, strategy="eod", score=1.0,
        scan_time=f"INSTRUMENTED-{t}", flow_verdict=None,
        indicators={"sources": ["R"], "confluence": 1, "vol_ratio": 1.0, "net_value": 0.0},
    ) for t in TICKERS
]

firm_mod.reset_market_ctx()
t0 = time.monotonic()
# Pass OUR instrumented router so the counting_create wrapper is on the path.
decisions = firm_mod.evaluate_staged(candidates, client=router)
elapsed = time.monotonic() - t0

print(f"\nDecisions: {[(d.ticker, d.decision) for d in decisions]}")
print(f"Elapsed: {elapsed:.1f}s")
print(f"\n=== MEASURED peak concurrent HTTP-in-flight to z.ai: {state['peak']} ===")
print(f"(semaphore allows {cfg.ZAI_MAX_CONCURRENT}; z.ai's cap per probe = 5)")
print(f"Total HTTP events recorded: {len(state['history'])}")
