"""Z.ai provider. OpenAI SDK pointed at Z.ai's OpenAI-compatible endpoint —
this was previously (and confusingly) named DeepSeekClient; nothing about
the underlying integration changes, only the name, now that it correctly
reflects what it actually calls.

Retries once on 5xx/rate-limit at the HTTP layer — provider-local
resilience, independent of and prior to the Router's cross-provider
failover.
"""

import asyncio
import time
from datetime import datetime, timezone

import openai
from openai import AsyncOpenAI, APIError, APIStatusError, APITimeoutError, RateLimitError

from .. import config
from .base import ProviderCapabilities, ProviderResponse, strip_fences
from .errors import (
    ProviderException, ProviderQuotaExceeded, ProviderRateLimited,
    ProviderSessionLimit, ProviderTimeout, ProviderUnavailable,
)
from .registry import register

# Z.ai error 1308: "Usage limit reached for 5 hour" — a subscription usage
# window, not a transient burst limit (RCA 2026-07-10). No reset timestamp
# is provided, so the Router falls back to its configured hold duration.
_SESSION_LIMIT_MSG = "usage limit reached"


def _classify(err: Exception) -> ProviderException:
    if isinstance(err, APITimeoutError):
        return ProviderTimeout(str(err))
    if isinstance(err, RateLimitError):
        if _SESSION_LIMIT_MSG in str(err).lower():
            return ProviderSessionLimit(str(err), reset_time=None)
        return ProviderRateLimited(str(err))
    if isinstance(err, APIStatusError) and err.status_code in (402, 403):
        return ProviderQuotaExceeded(str(err))
    return ProviderUnavailable(str(err))


@register("zai")
class ZAIProvider:
    name = "zai"
    capabilities = ProviderCapabilities(
        supports_json_mode=True, supports_json_schema=False,
        supports_tools=True, max_context_tokens=None,
    )

    def __init__(self, api_key: str | None = None, base_url: str | None = None,
                 model: str | None = None, max_concurrent: int | None = None) -> None:
        self._client = AsyncOpenAI(
            api_key=api_key or config.ZAI_API_KEY or "missing",
            base_url=base_url or config.ZAI_BASE_URL,
            max_retries=0,
        )
        self._model = model or config.MODEL_ID
        # Concurrency cap (RCA 2026-07-13): the firm fans out candidates with
        # unbounded asyncio.gather(); without a throttle the ZAI endpoint sees
        # 50+ req/s bursts and returns 429 code 1302 (per-minute rate limit),
        # which opens the circuit and feeds the "all providers down" alert.
        # Mirrors ClaudeProvider's semaphore.
        self._semaphore = asyncio.Semaphore(
            max_concurrent if max_concurrent is not None else config.ZAI_MAX_CONCURRENT
        )

    def model(self) -> str:
        return self._model

    async def generate(
        self, messages: list[dict], *, timeout: float | None = None, max_retries: int = 1,
    ) -> ProviderResponse:
        timeout = timeout if timeout is not None else config.PER_AGENT_TIMEOUT_S
        start = time.monotonic()
        last_err: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                # Acquire the semaphore only around the HTTP call so pending
                # tasks don't hold a slot while waiting on their retry backoff.
                async with self._semaphore:
                    resp = await self._client.chat.completions.create(
                        model=self._model, messages=messages, timeout=timeout,
                        response_format={"type": "json_object"},
                    )
                content = strip_fences(resp.choices[0].message.content or "")
                usage = resp.usage
                tokens_in = getattr(usage, "prompt_tokens", 0) if usage else 0
                tokens_out = getattr(usage, "completion_tokens", 0) if usage else 0
                return ProviderResponse(
                    content=content, provider="zai", model=self._model,
                    runtime_version=openai.__version__,
                    tokens_in=tokens_in, tokens_out=tokens_out,
                    cost_usd=self._calc_cost(tokens_in, tokens_out),
                    duration_s=time.monotonic() - start,
                    request_id=resp.id, timestamp=datetime.now(timezone.utc),
                )
            except (APIStatusError, APIError, RateLimitError) as err:
                last_err = err
                if attempt < max_retries:
                    await asyncio.sleep(4 * (2 ** attempt))
                    continue
                raise _classify(err) from err
        assert last_err is not None
        raise _classify(last_err) from last_err

    async def health(self) -> bool:
        try:
            await self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1, timeout=10,
            )
            return True
        except Exception:
            return False

    @staticmethod
    def _calc_cost(tokens_in: int, tokens_out: int) -> float:
        return (
            tokens_in / 1_000_000 * config.PRICE_INPUT_PER_M
            + tokens_out / 1_000_000 * config.PRICE_OUTPUT_PER_M
        )
