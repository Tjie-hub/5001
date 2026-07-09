import asyncio
import json
import subprocess
from unittest.mock import AsyncMock, Mock, patch

import pytest

from engine.agent_firm.providers.claude import ClaudeProvider
from engine.agent_firm.providers.errors import (
    ProviderQuotaExceeded, ProviderRateLimited, ProviderTimeout, ProviderUnavailable,
)


def _fake_proc(stdout: bytes, stderr: bytes, returncode: int):
    proc = AsyncMock()
    proc.communicate.return_value = (stdout, stderr)
    proc.returncode = returncode
    return proc


def _cli_json(result="ok", session_id="sess-1", input_tokens=100, output_tokens=50):
    return json.dumps({
        "result": result, "session_id": session_id,
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
    }).encode()


@pytest.fixture(autouse=True)
def _fake_version(monkeypatch):
    monkeypatch.setattr(
        subprocess, "run",
        lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout="2.1.204 (Claude Code)\n", stderr=""),
    )


@pytest.mark.asyncio
async def test_generate_returns_provider_response():
    provider = ClaudeProvider(model="sonnet", max_concurrent=4, overall_timeout=5.0)
    with patch("asyncio.create_subprocess_exec",
               AsyncMock(return_value=_fake_proc(_cli_json(result="hi there"), b"", 0))):
        resp = await provider.generate([
            {"role": "system", "content": "sys"}, {"role": "user", "content": "usr"},
        ])
    assert resp.content == "hi there"
    assert resp.provider == "claude"
    assert resp.tokens_in == 100
    assert resp.tokens_out == 50
    assert resp.cost_usd == 0.0
    assert resp.request_id == "sess-1"
    assert resp.runtime_version == "2.1.204 (Claude Code)"


@pytest.mark.asyncio
async def test_generate_strips_markdown_fences_from_result():
    provider = ClaudeProvider(model="sonnet", max_concurrent=4, overall_timeout=5.0)
    fenced_result = '```json\n{"verdict": "approve"}\n```'
    with patch("asyncio.create_subprocess_exec",
               AsyncMock(return_value=_fake_proc(_cli_json(result=fenced_result), b"", 0))):
        resp = await provider.generate([
            {"role": "system", "content": "sys"}, {"role": "user", "content": "usr"},
        ])
    assert resp.content == '{"verdict": "approve"}'


@pytest.mark.asyncio
async def test_generate_raises_provider_timeout_on_wait_for_timeout():
    provider = ClaudeProvider(overall_timeout=0.01)

    async def _hang(*a, **k):
        await asyncio.sleep(10)
        return b"", b""

    hung_proc = AsyncMock()
    hung_proc.communicate = _hang
    # Process.kill() is synchronous in asyncio's subprocess API; Process.wait()
    # is a coroutine. AsyncMock() would make both attributes async by default,
    # so kill must be overridden with a plain Mock to match the real API.
    hung_proc.kill = Mock()
    hung_proc.wait = AsyncMock()
    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=hung_proc)):
        with pytest.raises(ProviderTimeout):
            await provider.generate([{"role": "user", "content": "x"}])

    hung_proc.kill.assert_called_once()
    hung_proc.wait.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_raises_quota_exceeded_on_usage_limit_stderr():
    provider = ClaudeProvider()
    proc = _fake_proc(b"", b"Error: usage limit reached for this account", 1)
    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)):
        with pytest.raises(ProviderQuotaExceeded):
            await provider.generate([{"role": "user", "content": "x"}])


@pytest.mark.asyncio
async def test_generate_raises_rate_limited_on_rate_limit_stderr():
    provider = ClaudeProvider()
    proc = _fake_proc(b"", b"429 too many requests", 1)
    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)):
        with pytest.raises(ProviderRateLimited):
            await provider.generate([{"role": "user", "content": "x"}])


@pytest.mark.asyncio
async def test_generate_raises_unavailable_on_unclassified_nonzero_exit():
    provider = ClaudeProvider()
    proc = _fake_proc(b"", b"some other CLI error", 1)
    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)):
        with pytest.raises(ProviderUnavailable):
            await provider.generate([{"role": "user", "content": "x"}])


@pytest.mark.asyncio
async def test_generate_raises_unavailable_on_malformed_json():
    provider = ClaudeProvider()
    proc = _fake_proc(b"not json", b"", 0)
    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)):
        with pytest.raises(ProviderUnavailable):
            await provider.generate([{"role": "user", "content": "x"}])


def test_claude_capabilities_and_name():
    provider = ClaudeProvider()
    assert provider.name == "claude"
    assert provider.capabilities.supports_json_schema is True
    assert provider.model() == "sonnet"


@pytest.mark.asyncio
async def test_health_returns_true_on_zero_exit():
    provider = ClaudeProvider()
    proc = _fake_proc(b"2.1.204", b"", 0)
    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)):
        assert await provider.health() is True


@pytest.mark.asyncio
async def test_health_returns_false_on_exception():
    provider = ClaudeProvider()
    with patch("asyncio.create_subprocess_exec", AsyncMock(side_effect=OSError("no such file"))):
        assert await provider.health() is False
