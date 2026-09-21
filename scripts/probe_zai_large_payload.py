"""Payload-size probe: does concurrency=4 with LARGE prompts trip 1302
where concurrency=4 with tiny prompts did not? Tests the TPM hypothesis.
"""
import asyncio
import os
import sys
import time

sys.path.insert(0, "/home/tjiesar/10 Projects/idx-walkforward-5001")
os.environ["AGENT_FIRM_ENV_PATH"] = "/home/tjiesar/10 Projects/idx-walkforward-5001/.env"

from openai import AsyncOpenAI
from engine.agent_firm import config as cfg

# ~3KB user prompt — comparable to a firm analyst payload (system prompt is
# loaded separately by the firm; here we just inflate the user message).
BIG = ("Analyze this ticker. " + ("context: numbers, indicators, flow data. " * 200))[:3500]


async def one(client, idx, sem):
    async with sem:
        t0 = time.monotonic()
        try:
            r = await client.chat.completions.create(
                model=cfg.MODEL_ID,
                messages=[
                    {"role": "system", "content": "You are a financial analyst. Reply with JSON."},
                    {"role": "user", "content": BIG + f" (req {idx})"},
                ],
                timeout=45,
                response_format={"type": "json_object"},
            )
            tin = getattr(r.usage, "prompt_tokens", 0) if r.usage else 0
            return "ok", time.monotonic() - t0, tin
        except Exception as e:
            return "fail:" + str(e)[:60], time.monotonic() - t0, 0


async def main():
    client = AsyncOpenAI(api_key=cfg.ZAI_API_KEY, base_url=cfg.ZAI_BASE_URL, max_retries=0)
    print(f"Payload probe: 8 requests at concurrency=4, LARGE (~3.5KB) prompts.")
    print(f"If 1302s occur here but not with tiny prompts → TPM/payload-size is the limit.")
    sem = asyncio.Semaphore(4)
    t0 = time.monotonic()
    results = await asyncio.gather(*[one(client, i, sem) for i in range(8)])
    elapsed = time.monotonic() - t0
    ok = [r for r in results if r[0] == "ok"]
    fail = [r for r in results if r[0] != "ok"]
    total_in = sum(r[2] for r in ok)
    print(f"  8 large reqs @ conc=4: {len(ok)} ok, {len(fail)} fail in {elapsed:.1f}s")
    print(f"  prompt tokens consumed (ok calls): {total_in}")
    for r in fail:
        print(f"    {r[0]}")


asyncio.run(main())
