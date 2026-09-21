"""Direct concurrency probe — fires N simultaneous requests at z.ai and
reports how many succeed vs fail with 1302. Tells us the actual concurrency
cap independent of any code hypothesis.
"""
import asyncio
import time
import os
import sys

sys.path.insert(0, "/home/tjiesar/10 Projects/idx-walkforward-5001")
os.environ["AGENT_FIRM_ENV_PATH"] = "/home/tjiesar/10 Projects/idx-walkforward-5001/.env"

from openai import AsyncOpenAI
from engine.agent_firm import config as cfg


async def one_request(client, idx):
    t0 = time.monotonic()
    try:
        resp = await client.chat.completions.create(
            model=cfg.MODEL_ID,
            messages=[{"role": "user", "content": f"reply with the number {idx}"}],
            timeout=30,
            response_format={"type": "json_object"},
        )
        return idx, "ok", time.monotonic() - t0, None
    except Exception as e:
        return idx, "fail", time.monotonic() - t0, str(e)[:90]


async def fire(n):
    client = AsyncOpenAI(api_key=cfg.ZAI_API_KEY, base_url=cfg.ZAI_BASE_URL, max_retries=0)
    t0 = time.monotonic()
    results = await asyncio.gather(*[one_request(client, i) for i in range(n)])
    elapsed = time.monotonic() - t0
    ok = sum(1 for r in results if r[1] == "ok")
    fail = sum(1 for r in results if r[1] == "fail")
    print(f"  fired {n} concurrent → {ok} ok, {fail} fail in {elapsed:.1f}s")
    for idx, status, dur, err in results:
        if status == "fail":
            print(f"    req {idx}: {err}")
    return ok


async def main():
    print(f"Probing z.ai concurrency limit. model={cfg.MODEL_ID} base={cfg.ZAI_BASE_URL}")
    # Wait between probes so the previous probe's in-flight calls drain.
    for n in [1, 2, 3, 4, 6]:
        ok = await fire(n)
        if ok < n and n > 1:
            print(f"  *** first failure observed at concurrency={n} ***")
        await asyncio.sleep(35)  # let z.ai's window recover


asyncio.run(main())
