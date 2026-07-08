"""Claude provider — via the `claude` CLI (Claude Code Subscription), not
the Anthropic API. No SDK; shells out per call.

Each call is a pure structured-reasoning request: --disallowedTools "*"
--strict-mcp-config means no file/bash/web tool use and no inherited MCP
servers from an interactive session — matching what Firm agents actually
need (JSON in, JSON out). See design doc §9.
"""

import asyncio
import json
import re
import subprocess
import time
from datetime import datetime, timezone

from .base import ProviderCapabilities, ProviderResponse
from .errors import (
    ProviderQuotaExceeded, ProviderRateLimited, ProviderTimeout, ProviderUnavailable,
)
from .registry import register

_QUOTA_PATTERNS = re.compile(r"usage limit|quota|out of credits", re.IGNORECASE)
_RATE_LIMIT_PATTERNS = re.compile(r"rate limit|too many requests|429", re.IGNORECASE)


@register("claude")
class ClaudeProvider:
    name = "claude"
    capabilities = ProviderCapabilities(
        supports_json_mode=True, supports_json_schema=True,
        supports_tools=True, max_context_tokens=None,
    )

    def __init__(
        self,
        model: str = "sonnet",
        max_concurrent: int = 4,
        overall_timeout: float = 75.0,
    ) -> None:
        self._model = model
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._overall_timeout = overall_timeout
        self._runtime_version = self._capture_runtime_version()

    def model(self) -> str:
        return self._model

    @staticmethod
    def _capture_runtime_version() -> str:
        try:
            out = subprocess.run(
                ["claude", "--version"], capture_output=True, text=True, timeout=5,
            )
            return out.stdout.strip() or "unknown"
        except Exception:
            return "unknown"

    async def generate(
        self, messages: list[dict], *, timeout: float | None = None,
    ) -> ProviderResponse:
        system_prompt = "\n".join(m["content"] for m in messages if m["role"] == "system")
        user_prompt = "\n".join(m["content"] for m in messages if m["role"] == "user")

        args = [
            "claude", "-p", user_prompt,
            "--append-system-prompt", system_prompt,
            "--model", self._model,
            "--output-format", "json",
            "--disallowedTools", "*",
            "--strict-mcp-config",
        ]
        effective_timeout = timeout if timeout is not None else self._overall_timeout

        start = time.monotonic()
        async with self._semaphore:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=effective_timeout,
                )
            except asyncio.TimeoutError as err:
                proc.kill()
                await proc.wait()
                raise ProviderTimeout(
                    f"claude CLI timed out after {effective_timeout}s"
                ) from err
        duration = time.monotonic() - start

        if proc.returncode != 0:
            stderr_text = stderr.decode(errors="replace").strip()
            if _QUOTA_PATTERNS.search(stderr_text):
                raise ProviderQuotaExceeded(stderr_text or "claude CLI quota exceeded")
            if _RATE_LIMIT_PATTERNS.search(stderr_text):
                raise ProviderRateLimited(stderr_text or "claude CLI rate limited")
            raise ProviderUnavailable(stderr_text or f"claude CLI exited {proc.returncode}")

        try:
            result = json.loads(stdout.decode())
        except json.JSONDecodeError as err:
            raise ProviderUnavailable(f"claude CLI returned non-JSON output: {err}") from err

        usage = result.get("usage") or {}
        return ProviderResponse(
            content=result.get("result", ""),
            provider="claude",
            model=self._model,
            runtime_version=self._runtime_version,
            tokens_in=usage.get("input_tokens", 0),
            tokens_out=usage.get("output_tokens", 0),
            cost_usd=0.0,
            duration_s=duration,
            request_id=result.get("session_id"),
            timestamp=datetime.now(timezone.utc),
        )

    async def health(self) -> bool:
        try:
            proc = await asyncio.create_subprocess_exec(
                "claude", "--version",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.communicate(), timeout=5.0)
            return proc.returncode == 0
        except Exception:
            return False
