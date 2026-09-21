"""Sustained-rate probe: fire requests at a controlled RATE (low concurrency)
and see if z.ai still returns 1302. This isolates "is it concurrency or RPM?"
"""
import asyncio
import time
import os
import sys

sys.path.insert(0, "/home/tjiesar/10 Projects/idx-walkforward-5001")
os.environ["AGENT_FIRM_ENV_PATH"] = "/home/tjiesar/10 Projects/idx-walkforward-5001/.env"

from openai import AsyncOpenAI
from engine.agent_firm import config as cfg


async def one_request(client, idx, sem):
    async with sem:
        t0 = time.monotonic()
        try:
            await client.chat.completions.create(
                model=cfg.MODEL_ID,
                messages=[{"role": "user", "content": f"reply {idx}"}],
                timeout=30,
                response_format={"type": "json_object"},
            )
            return "ok", time.monotonic() - t0
        except Exception as e:
            return "fail:" + str(e)[:50], time.monotonic() - t0


async def main():
    client = AsyncOpenAI(api_key=cfg.ZAI_API_KEY, base_url=cfg.ZAI_BASE_URL, max_retries=0)
    print(f"Sustained probe: fire 20 requests, concurrency capped at 3 (well under the 5-limit), no other throttle.")
    print("If 1302s still occur → it's RPM/sustained, not concurrency.")
    sem = asyncio.Semaphore(3)
    t0 = time.monotonic()
    results = await asyncio.gather(*[one_request(client, i, sem) for i in range(20)])
    elapsed = time.monotonic() - t0
    ok = sum(1 for r in results if r[0] == "ok")
    fail = sum(1 for r in results if r[0] != "ok")
    print(f"  20 requests at concurrency<=3: {ok} ok, {fail} fail in {elapsed:.1f}s")
    for r in results:
        if r[0] != "ok":
            print(f"    {r[0]}")
    print(f"  Effective rate: {20/(elapsed/60):.1f} RPM")


asyncio.run(main())
