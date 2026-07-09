"""The provider abstraction Firm depends on. Kept deliberately small — see
design doc §1: generate(), health(), model(), name, capabilities. No
availability() (§2) and no retry() (failover is the Router's job, §4)."""

import re
from datetime import datetime
from typing import Optional, Protocol, runtime_checkable

from pydantic import BaseModel


def strip_fences(text: str) -> str:
    """Strip markdown code fences the model sometimes wraps around JSON.

    Shared by ZAIProvider and ClaudeProvider — both models have been
    observed, in production, wrapping JSON output in ```json fences despite
    prompt instructions not to.
    """
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    return m.group(1).strip() if m else text.strip()


class ProviderCapabilities(BaseModel):
    supports_json_mode: bool
    supports_json_schema: bool
    supports_tools: bool
    max_context_tokens: Optional[int] = None


class ProviderResponse(BaseModel):
    content: str
    provider: str
    model: str
    runtime_version: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    duration_s: float
    request_id: Optional[str] = None
    timestamp: datetime
    failover: bool = False


@runtime_checkable
class FirmLLMProvider(Protocol):
    name: str
    capabilities: ProviderCapabilities

    async def generate(
        self, messages: list[dict], *, timeout: Optional[float] = None,
    ) -> ProviderResponse: ...

    async def health(self) -> bool: ...

    def model(self) -> str: ...
