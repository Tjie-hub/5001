"""The provider abstraction Firm depends on. Kept deliberately small — see
design doc §1: generate(), health(), model(), name, capabilities. No
availability() (§2) and no retry() (failover is the Router's job, §4)."""

from datetime import datetime
from typing import Optional, Protocol, runtime_checkable

from pydantic import BaseModel


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
