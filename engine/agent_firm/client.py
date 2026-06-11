"""DeepSeek client wrapper. OpenAI SDK pointed at api.deepseek.com.

Adds:
- per-call timeout
- retry-once on 5xx / rate limit
- token + cost accounting on every call
"""

import asyncio
import json
import re
import time

from openai import AsyncOpenAI, APIError, RateLimitError, APIStatusError

from . import config


def _strip_fences(text: str) -> str:
    """Strip markdown code fences DeepSeek sometimes wraps around JSON."""
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    return m.group(1).strip() if m else text.strip()


class DeepSeekClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self.client = AsyncOpenAI(
            api_key=api_key or config.DEEPSEEK_API_KEY or "missing",
            base_url=base_url or config.DEEPSEEK_BASE_URL,
            max_retries=0,
        )
        self.model = model or config.MODEL_ID

    async def chat(
        self,
        messages: list[dict],
        timeout: float | None = None,
        max_retries: int = 1,
    ) -> dict:
        timeout = timeout if timeout is not None else config.PER_AGENT_TIMEOUT_S
        start = time.monotonic()
        last_err: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                resp = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    timeout=timeout,
                    response_format={"type": "json_object"},
                )
                content = _strip_fences(resp.choices[0].message.content or "")
                usage = resp.usage
                tokens_in = getattr(usage, "prompt_tokens", 0) if usage else 0
                tokens_out = getattr(usage, "completion_tokens", 0) if usage else 0
                cost = self._calc_cost(tokens_in, tokens_out)
                return {
                    "content": content,
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                    "cost_usd": cost,
                    "duration_s": time.monotonic() - start,
                }
            except (APIStatusError, APIError, RateLimitError) as err:
                last_err = err
                if attempt < max_retries:
                    await asyncio.sleep(4 * (2 ** attempt))
                    continue
                raise
        assert last_err is not None
        raise last_err

    @staticmethod
    def _calc_cost(tokens_in: int, tokens_out: int) -> float:
        return (
            tokens_in / 1_000_000 * config.PRICE_INPUT_PER_M
            + tokens_out / 1_000_000 * config.PRICE_OUTPUT_PER_M
        )
