"""Z.ai provider. OpenAI SDK pointed at Z.ai's OpenAI-compatible endpoint —
this was previously (and confusingly) named DeepSeekClient; nothing about
the underlying integration changes, only the name, now that it correctly
reflects what it actually calls.

Retries once on 5xx/rate-limit at the HTTP layer — provider-local
resilience, independent of and prior to the Router's cross-provider
failover.
"""

import asyncio
import re
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

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
# window, not a transient burst limit (RCA 2026-07-10).
_SESSION_LIMIT_MSG = "usage limit reached"

# Audit 2026-07-22: z.ai's genuine quota-exhaustion errors (1308 5-hour, 1310
# weekly/monthly) carry "Your limit will reset at YYYY-MM-DD HH:MM:SS" — this
# was previously discarded (reset_time hardcoded to None), forcing the
# Router's 15-minute QUOTA_FALLBACK_HOLD_S fallback instead of the true
# window and causing continuous re-probing of a provider already known (from
# its own error response) to still be exhausted. Cross-checked against 3
# independent production incidents (2026-07-13, 2026-07-21): the advertised
# timestamp is unlabeled local time that only fits a "5 hour" window when
# read as Asia/Jakarta (WIB) — the same fallback zone classification.py
# already uses for Claude's differently-formatted reset phrase, and the
# codebase-wide time convention (CLAUDE.md: "All times are WIB").
_ZAI_RESET_TZ = ZoneInfo("Asia/Jakarta")
_ZAI_RESET = re.compile(
    r"reset\s+at\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})", re.IGNORECASE)


def _parse_zai_reset(text: str) -> datetime | None:
    """Extract z.ai's advertised reset timestamp, interpreted as WIB, as an
    aware UTC datetime. Returns None on no match / unparseable text so a
    wording change degrades to the pre-existing fallback-hold behavior
    instead of crashing classification."""
    m = _ZAI_RESET.search(text or "")
    if m is None:
        return None
    try:
        naive = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None
    return naive.replace(tzinfo=_ZAI_RESET_TZ).astimezone(timezone.utc)


def _classify(err: Exception) -> ProviderException:
    if isinstance(err, APITimeoutError):
        return ProviderTimeout(str(err))
    if isinstance(err, RateLimitError):
        text = str(err)
        reset_time = _parse_zai_reset(text)
        # A parseable reset timestamp is itself the signal of a sustained
        # quota exhaustion (vs. a transient burst limit like code 1302/1305,
        # which never carries one) — this also catches wording z.ai has not
        # used yet, the exact gap that hid the 2026-07-13 Claude regression.
        if reset_time is not None or _SESSION_LIMIT_MSG in text.lower():
            return ProviderSessionLimit(text, reset_time=reset_time)
        return ProviderRateLimited(text)
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
        # unbounded asyncio.gather(); this caps in-flight CONCURRENCY so a slow
        # 250s call can't starve others. Mirrors ClaudeProvider's semaphore.
        #
        # Issue RATE is NO LONGER paced here (R-7 Tier 1): the per-provider
        # token bucket used to reset its burst allowance every evaluate_staged()
        # tick because this provider is rebuilt each tick. Rate pacing now lives
        # in the PROCESS-GLOBAL adaptive governor (providers/governor.py),
        # consulted by the Router before dispatch, so its AIMD state survives
        # across ticks and event loops.
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
                # Issue-rate pacing happens in the Router via the global
                # governor (R-7 Tier 1). Here we only bound CONCURRENCY: acquire
                # the semaphore around the HTTP call so pending tasks don't hold
                # a slot while waiting on their retry backoff.
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
