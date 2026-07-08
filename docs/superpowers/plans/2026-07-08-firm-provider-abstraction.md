# Firm LLM Provider Abstraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decouple `engine/agent_firm/` from any single LLM provider so Claude (via Claude Code Subscription CLI) and Z.ai (currently mislabeled "DeepSeek") are interchangeable, config-selected, auto-failover-capable backends behind one `FirmLLMProvider` interface — with zero change to Firm prompts, scoring, guardrails, or the LangGraph flow.

**Architecture:** `firm.py` → `ProviderFactory.build_router()` → `ProviderRouter` (ordered provider list, one `CircuitBreaker` per provider, daily-cap check) → `FirmLLMProvider` implementations (`ClaudeProvider` subprocess-based via the `claude` CLI, `ZAIProvider` — the renamed `DeepSeekClient`) → structured `ProviderResponse`. Providers self-register into a `Registry` by name; the Router only ever sees names from config, never imports a concrete provider class.

**Tech Stack:** Python 3.10+, pydantic v2, `openai` SDK (unchanged, now used only by `ZAIProvider`), `asyncio` subprocess for `ClaudeProvider`, pytest + `pytest-asyncio` + `respx`/`httpx` for tests, SQLite (`data/db.py`) for persistence.

**Design doc:** `docs/superpowers/specs/2026-07-08-firm-provider-abstraction-design.md` (locked, 3 review rounds — read it if a task here is ambiguous; section numbers below (`§N`) refer to it).

**Scope note:** two small additions beyond the locked spec, found during planning and needed to make it actually work — both flagged inline where they occur:
1. `agent_traces` needs an `error TEXT` column (the spec's Metrics §12 needs to query per-call failure/timeout, but the current schema never persisted `AgentResult.error` at all).
2. `AgentResult` needs a `cost_usd` field (currently only `AgentDecision.cost_usd` exists, computed by applying Z.ai's flat per-token price to the *summed* tokens across all 7 traces — which would incorrectly price Claude's free tokens once mixed-provider traces exist).

---

### Task 1: Provider package skeleton + exception hierarchy

**Files:**
- Create: `engine/agent_firm/providers/__init__.py`
- Create: `engine/agent_firm/providers/errors.py`
- Test: `tests/agent_firm/providers/__init__.py`
- Test: `tests/agent_firm/providers/test_errors.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/agent_firm/providers/test_errors.py
from engine.agent_firm.providers.errors import (
    ProviderException, ProviderQuotaExceeded, ProviderRateLimited,
    ProviderTimeout, ProviderUnavailable,
)


def test_all_provider_exceptions_are_provider_exception():
    for cls in (ProviderQuotaExceeded, ProviderRateLimited, ProviderTimeout, ProviderUnavailable):
        assert issubclass(cls, ProviderException)
        assert issubclass(cls, Exception)


def test_provider_exception_carries_message():
    err = ProviderTimeout("claude CLI timed out after 75s")
    assert str(err) == "claude CLI timed out after 75s"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/agent_firm/providers/test_errors.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'engine.agent_firm.providers'`

- [ ] **Step 3: Create the package and exceptions**

```python
# engine/agent_firm/providers/__init__.py
```
(empty — package marker)

```python
# tests/agent_firm/providers/__init__.py
```
(empty — package marker)

```python
# engine/agent_firm/providers/errors.py
"""Provider-layer exception hierarchy. Every FirmLLMProvider.generate()
failure is re-raised as one of these four subclasses so the Router can act
on it uniformly regardless of which SDK/subprocess raised the original
error."""


class ProviderException(Exception):
    """Base class for all provider-layer failures the Router can act on."""


class ProviderQuotaExceeded(ProviderException):
    pass


class ProviderRateLimited(ProviderException):
    pass


class ProviderTimeout(ProviderException):
    pass


class ProviderUnavailable(ProviderException):
    pass
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/agent_firm/providers/test_errors.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add engine/agent_firm/providers/__init__.py engine/agent_firm/providers/errors.py \
        tests/agent_firm/providers/__init__.py tests/agent_firm/providers/test_errors.py
git commit -m "feat(firm): add provider exception hierarchy"
```

---

### Task 2: `FirmLLMProvider` interface, `ProviderCapabilities`, `ProviderResponse`

**Files:**
- Create: `engine/agent_firm/providers/base.py`
- Test: `tests/agent_firm/providers/test_base.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/agent_firm/providers/test_base.py
from datetime import datetime, timezone

from engine.agent_firm.providers.base import ProviderCapabilities, ProviderResponse


def test_provider_capabilities_defaults():
    caps = ProviderCapabilities(
        supports_json_mode=True, supports_json_schema=False, supports_tools=True,
    )
    assert caps.max_context_tokens is None


def test_provider_response_round_trip():
    now = datetime.now(timezone.utc)
    resp = ProviderResponse(
        content="hi", provider="zai", model="glm-5.2", runtime_version="1.2.3",
        tokens_in=10, tokens_out=5, cost_usd=0.001, duration_s=1.5,
        request_id="req-1", timestamp=now,
    )
    assert resp.failover is False
    assert resp.timestamp == now


def test_provider_response_failover_defaults_false():
    resp = ProviderResponse(
        content="hi", provider="claude", model="sonnet", runtime_version="2.1.204",
        tokens_in=0, tokens_out=0, cost_usd=0.0, duration_s=0.5,
        timestamp=datetime.now(timezone.utc),
    )
    assert resp.failover is False
    assert resp.request_id is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/agent_firm/providers/test_base.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'engine.agent_firm.providers.base'`

- [ ] **Step 3: Write `base.py`**

```python
# engine/agent_firm/providers/base.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/agent_firm/providers/test_base.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add engine/agent_firm/providers/base.py tests/agent_firm/providers/test_base.py
git commit -m "feat(firm): add FirmLLMProvider interface, ProviderCapabilities, ProviderResponse"
```

---

### Task 3: Circuit Breaker

**Files:**
- Create: `engine/agent_firm/providers/circuit_breaker.py`
- Test: `tests/agent_firm/providers/test_circuit_breaker.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent_firm/providers/test_circuit_breaker.py
from engine.agent_firm.providers.circuit_breaker import CircuitBreaker


def test_closed_allows_requests():
    cb = CircuitBreaker(failure_threshold=3, cooldown_s=30)
    assert cb.state == "CLOSED"
    assert cb.allow_request() is True


def test_opens_after_threshold_failures():
    cb = CircuitBreaker(failure_threshold=3, cooldown_s=30)
    assert cb.record_failure() is False  # 1st failure, still CLOSED
    assert cb.record_failure() is False  # 2nd failure, still CLOSED
    assert cb.record_failure() is True   # 3rd failure -> fresh OPEN transition
    assert cb.state == "OPEN"


def test_open_blocks_requests_before_cooldown():
    cb = CircuitBreaker(failure_threshold=1, cooldown_s=30)
    cb.record_failure()
    assert cb.state == "OPEN"
    assert cb.allow_request() is False  # cooldown hasn't elapsed


def test_half_open_after_cooldown_allows_one_trial(monkeypatch):
    cb = CircuitBreaker(failure_threshold=1, cooldown_s=10)
    cb.record_failure()
    fake_now = [1000.0]
    monkeypatch.setattr(
        "engine.agent_firm.providers.circuit_breaker.time.monotonic",
        lambda: fake_now[0],
    )
    cb.last_failure = 990.0  # 10s ago, at/past cooldown
    assert cb.allow_request() is True
    assert cb.state == "HALF_OPEN"


def test_half_open_second_concurrent_caller_blocked_until_trial_resolves(monkeypatch):
    cb = CircuitBreaker(failure_threshold=1, cooldown_s=10)
    cb.record_failure()
    cb.last_failure = 0.0
    monkeypatch.setattr(
        "engine.agent_firm.providers.circuit_breaker.time.monotonic",
        lambda: 100.0,
    )
    assert cb.allow_request() is True   # first caller acquires the trial slot
    assert cb.allow_request() is False  # second concurrent caller is blocked


def test_trial_success_closes_circuit():
    cb = CircuitBreaker(failure_threshold=1, cooldown_s=0)
    cb.record_failure()
    cb.state = "HALF_OPEN"
    assert cb.record_success() is True  # was OPEN/HALF_OPEN -> now closed
    assert cb.state == "CLOSED"
    assert cb.consecutive_failures == 0


def test_trial_failure_reopens_circuit():
    cb = CircuitBreaker(failure_threshold=1, cooldown_s=0)
    cb.record_failure()
    cb.state = "HALF_OPEN"
    assert cb.record_failure() is True  # trial failed -> re-opens
    assert cb.state == "OPEN"


def test_release_trial_frees_slot_without_changing_state():
    cb = CircuitBreaker(failure_threshold=1, cooldown_s=10)
    cb.record_failure()
    cb.last_failure = 0.0
    import engine.agent_firm.providers.circuit_breaker as cb_mod
    orig = cb_mod.time.monotonic
    cb_mod.time.monotonic = lambda: 100.0
    try:
        assert cb.allow_request() is True  # acquires trial slot
        cb.release_trial()
        assert cb.allow_request() is True  # slot is free again
    finally:
        cb_mod.time.monotonic = orig
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/agent_firm/providers/test_circuit_breaker.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `circuit_breaker.py`**

```python
# engine/agent_firm/providers/circuit_breaker.py
"""Per-provider circuit breaker (design doc §3). One instance per provider,
owned by the Router, in-memory only (single-process app).

allow_request() has no `await` inside it, so Python's cooperative
scheduling makes the whole check-and-flip-state sequence atomic with
respect to other coroutines — that's what actually guarantees only one
HALF_OPEN trial is in flight at a time, without needing a real lock object.
"""

import time
from typing import Literal


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, cooldown_s: float = 30.0):
        self.consecutive_failures = 0
        self.last_failure: float | None = None  # time.monotonic() timestamp
        self.state: Literal["CLOSED", "OPEN", "HALF_OPEN"] = "CLOSED"
        self.failure_threshold = failure_threshold
        self.cooldown_s = cooldown_s
        self._trial_in_flight = False

    def allow_request(self) -> bool:
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            if self.last_failure is not None and \
               time.monotonic() - self.last_failure >= self.cooldown_s:
                self.state = "HALF_OPEN"
            else:
                return False
        # HALF_OPEN: allow exactly one trial through
        if self._trial_in_flight:
            return False
        self._trial_in_flight = True
        return True

    def record_success(self) -> bool:
        """Returns True if this success just closed a previously OPEN/HALF_OPEN circuit."""
        was_open = self.state != "CLOSED"
        self.consecutive_failures = 0
        self.last_failure = None
        self._trial_in_flight = False
        self.state = "CLOSED"
        return was_open

    def record_failure(self) -> bool:
        """Returns True if this failure just caused a fresh transition to OPEN."""
        was_open = self.state == "OPEN"
        self.consecutive_failures += 1
        self.last_failure = time.monotonic()
        self._trial_in_flight = False
        if self.consecutive_failures >= self.failure_threshold or self.state == "HALF_OPEN":
            self.state = "OPEN"
        return self.state == "OPEN" and not was_open

    def release_trial(self) -> None:
        """Call when a HALF_OPEN trial slot was acquired via allow_request()
        but the caller decided not to actually attempt generate() (e.g. the
        daily call cap was hit) — frees the slot for a future retry."""
        self._trial_in_flight = False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/agent_firm/providers/test_circuit_breaker.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add engine/agent_firm/providers/circuit_breaker.py tests/agent_firm/providers/test_circuit_breaker.py
git commit -m "feat(firm): add per-provider CircuitBreaker state machine"
```

---

### Task 4: Provider Registry

**Files:**
- Create: `engine/agent_firm/providers/registry.py`
- Test: `tests/agent_firm/providers/test_registry.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/agent_firm/providers/test_registry.py
import pytest

from engine.agent_firm.providers import registry


def test_register_and_build():
    @registry.register("fake")
    class FakeProvider:
        name = "fake"
        def __init__(self, x=1):
            self.x = x

    p = registry.build("fake", x=5)
    assert isinstance(p, FakeProvider)
    assert p.x == 5


def test_build_unknown_raises_value_error():
    with pytest.raises(ValueError, match="unknown provider"):
        registry.build("nonexistent")


def test_registered_names_includes_registered():
    @registry.register("another_fake")
    class AnotherFake:
        name = "another_fake"

    assert "another_fake" in registry.registered_names()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/agent_firm/providers/test_registry.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `registry.py`**

```python
# engine/agent_firm/providers/registry.py
"""Provider name -> class lookup (design doc §4a). The Router resolves
providers by name through this module — it never imports a concrete
provider class directly."""

from typing import Callable

_PROVIDERS: dict[str, Callable[..., "FirmLLMProvider"]] = {}  # noqa: F821 (forward ref, avoids import cycle)


def register(name: str):
    def deco(cls):
        _PROVIDERS[name] = cls
        return cls
    return deco


def build(name: str, **kwargs):
    if name not in _PROVIDERS:
        raise ValueError(f"unknown provider {name!r}; registered: {sorted(_PROVIDERS)}")
    return _PROVIDERS[name](**kwargs)


def registered_names() -> list[str]:
    return sorted(_PROVIDERS)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/agent_firm/providers/test_registry.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add engine/agent_firm/providers/registry.py tests/agent_firm/providers/test_registry.py
git commit -m "feat(firm): add provider registry (name -> class lookup)"
```

---

### Task 5: Structured Provider Events

**Files:**
- Create: `engine/agent_firm/providers/events.py`
- Test: `tests/agent_firm/providers/test_events.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/agent_firm/providers/test_events.py
import json
import logging
from datetime import datetime, timezone

from engine.agent_firm.providers.events import ProviderEvent, log_provider_event


def test_log_provider_event_writes_json_line(caplog):
    event = ProviderEvent(
        event_type="provider_failover", timestamp=datetime.now(timezone.utc),
        provider="claude", model="sonnet", reason="circuit open",
        duration_s=1.2, request_id="req-1", failover=True,
    )
    with caplog.at_level(logging.INFO, logger="agent_firm.providers"):
        log_provider_event(event)
    assert len(caplog.records) == 1
    parsed = json.loads(caplog.records[0].message)
    assert parsed["event_type"] == "provider_failover"
    assert parsed["provider"] == "claude"
    assert parsed["reason"] == "circuit open"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/agent_firm/providers/test_events.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `events.py`**

```python
# engine/agent_firm/providers/events.py
"""Structured, JSON-loggable provider decision events (design doc §7).
Machine-parseable for a future log shipper (ELK/Grafana/etc.) without
adding any new logging infra now."""

import logging
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel

logger = logging.getLogger("agent_firm.providers")

EventType = Literal[
    "provider_selected", "provider_failed", "provider_timeout",
    "provider_failover", "provider_circuit_open",
    "provider_circuit_closed", "provider_quota_exceeded",
]


class ProviderEvent(BaseModel):
    event_type: EventType
    timestamp: datetime
    provider: str
    model: Optional[str] = None
    reason: Optional[str] = None
    duration_s: Optional[float] = None
    request_id: Optional[str] = None
    failover: bool = False


def log_provider_event(event: ProviderEvent) -> None:
    logger.info(event.model_dump_json())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/agent_firm/providers/test_events.py -v`
Expected: PASS (1 test)

- [ ] **Step 5: Commit**

```bash
git add engine/agent_firm/providers/events.py tests/agent_firm/providers/test_events.py
git commit -m "feat(firm): add structured ProviderEvent + JSON logging"
```

---

### Task 6: Config — rename DEEPSEEK_* to ZAI_*, add provider/circuit/timeout/Claude vars

**Files:**
- Modify: `engine/agent_firm/config.py`
- Modify: `tests/agent_firm/test_config.py`

- [ ] **Step 1: Update the failing/changed test expectations first**

`test_pricing_defaults` currently asserts the stale `MODEL_ID == "deepseek-v4-pro"` default — update it, and add new tests for the provider/circuit/timeout config and the deprecated-var fallback:

```python
# tests/agent_firm/test_config.py — replace test_pricing_defaults with:
def test_pricing_defaults(monkeypatch):
    monkeypatch.delenv("AGENT_FIRM_PRICE_IN", raising=False)
    monkeypatch.delenv("AGENT_FIRM_PRICE_OUT", raising=False)
    monkeypatch.delenv("AGENT_FIRM_MODEL", raising=False)
    cfg = reload_config()
    assert cfg.PRICE_INPUT_PER_M == pytest.approx(0.435)
    assert cfg.PRICE_OUTPUT_PER_M == pytest.approx(0.870)
    assert cfg.MODEL_ID == "glm-5.2"


# — append at end of file —
def test_zai_key_from_new_var(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("ZAI_API_KEY", "zai-key-123")
    cfg = reload_config()
    assert cfg.ZAI_API_KEY == "zai-key-123"


def test_zai_key_falls_back_to_deprecated_deepseek_var(monkeypatch, caplog):
    monkeypatch.delenv("ZAI_API_KEY", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "old-deepseek-key")
    cfg = reload_config()
    assert cfg.ZAI_API_KEY == "old-deepseek-key"


def test_provider_mode_defaults_to_zai(monkeypatch):
    monkeypatch.delenv("AGENT_FIRM_PROVIDER", raising=False)
    cfg = reload_config()
    assert cfg.PROVIDER_MODE == "zai"


def test_provider_order_parses_csv(monkeypatch):
    monkeypatch.setenv("AGENT_FIRM_PROVIDER_ORDER", "claude,zai,openai")
    cfg = reload_config()
    assert cfg.PROVIDER_ORDER == ["claude", "zai", "openai"]


def test_circuit_breaker_defaults(monkeypatch):
    monkeypatch.delenv("AGENT_FIRM_CIRCUIT_FAILURES", raising=False)
    monkeypatch.delenv("AGENT_FIRM_CIRCUIT_COOLDOWN", raising=False)
    cfg = reload_config()
    assert cfg.CIRCUIT_FAILURES == 3
    assert cfg.CIRCUIT_COOLDOWN_S == pytest.approx(30.0)


def test_claude_config_defaults(monkeypatch):
    monkeypatch.delenv("AGENT_FIRM_CLAUDE_MODEL", raising=False)
    monkeypatch.delenv("AGENT_FIRM_CLAUDE_MAX_CONCURRENT", raising=False)
    monkeypatch.delenv("AGENT_FIRM_CLAUDE_MAX_CALLS_PER_DAY", raising=False)
    cfg = reload_config()
    assert cfg.CLAUDE_MODEL == "sonnet"
    assert cfg.CLAUDE_MAX_CONCURRENT == 4
    assert cfg.CLAUDE_MAX_CALLS_PER_DAY == 200
```

- [ ] **Step 2: Run to verify the new/changed tests fail**

Run: `pytest tests/agent_firm/test_config.py -v`
Expected: `test_pricing_defaults` FAILs (asserts `"glm-5.2"` against current `"deepseek-v4-pro"` default); the new tests FAIL with `AttributeError` (no such config attr yet)

- [ ] **Step 3: Update `config.py`**

```python
# engine/agent_firm/config.py
"""Agent firm configuration via environment variables.

All settings have sensible defaults. The firm is OFF by default to ensure
Phase 1 production deploy has zero behavioral impact.
"""

import logging
import os
from pathlib import Path

_log = logging.getLogger(__name__)


def _env_bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


FIRM_ENABLED = _env_bool("AGENT_FIRM_ENABLED", False)
FIRM_ENFORCE = _env_bool("AGENT_FIRM_ENFORCE", False)

DAILY_SPEND_CAP_USD = float(os.getenv("AGENT_FIRM_DAILY_CAP", "5.0"))
KILL_SWITCH_FILE = Path(os.getenv("AGENT_FIRM_KILL_FILE", "/tmp/agent_firm.disable"))

MODEL_ID = os.getenv("AGENT_FIRM_MODEL", "glm-5.2")

ZAI_API_KEY = os.getenv("ZAI_API_KEY", "")
ZAI_BASE_URL = os.getenv("ZAI_BASE_URL", "https://api.z.ai/api/coding/paas/v4")
if not ZAI_API_KEY and os.getenv("DEEPSEEK_API_KEY"):
    _log.warning("DEEPSEEK_API_KEY is deprecated — rename to ZAI_API_KEY")
    ZAI_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
if not os.getenv("ZAI_BASE_URL") and os.getenv("DEEPSEEK_BASE_URL"):
    _log.warning("DEEPSEEK_BASE_URL is deprecated — rename to ZAI_BASE_URL")
    ZAI_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", ZAI_BASE_URL)

PRICE_INPUT_PER_M = float(os.getenv("AGENT_FIRM_PRICE_IN", "0.435"))
PRICE_OUTPUT_PER_M = float(os.getenv("AGENT_FIRM_PRICE_OUT", "0.870"))

PER_AGENT_TIMEOUT_S = float(os.getenv("AGENT_FIRM_AGENT_TIMEOUT", "75"))

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
TAVILY_MAX_RESULTS = int(os.getenv("AGENT_FIRM_TAVILY_MAX", "5"))

# --- Provider routing (Firm LLM Provider Abstraction, 2026-07-08) ----------

PROVIDER_MODE = os.getenv("AGENT_FIRM_PROVIDER", "zai")
PROVIDER_ORDER = [
    p.strip() for p in os.getenv("AGENT_FIRM_PROVIDER_ORDER", "claude,zai").split(",")
    if p.strip()
]

CLAUDE_MODEL = os.getenv("AGENT_FIRM_CLAUDE_MODEL", "sonnet")
CLAUDE_MAX_CONCURRENT = int(os.getenv("AGENT_FIRM_CLAUDE_MAX_CONCURRENT", "4"))
CLAUDE_MAX_CALLS_PER_DAY = int(os.getenv("AGENT_FIRM_CLAUDE_MAX_CALLS_PER_DAY", "200"))

CIRCUIT_FAILURES = int(os.getenv("AGENT_FIRM_CIRCUIT_FAILURES", "3"))
CIRCUIT_COOLDOWN_S = float(os.getenv("AGENT_FIRM_CIRCUIT_COOLDOWN", "30"))

CONNECTION_TIMEOUT_S = float(os.getenv("AGENT_FIRM_CONNECTION_TIMEOUT", "10"))
READ_TIMEOUT_S = float(os.getenv("AGENT_FIRM_READ_TIMEOUT", "60"))
OVERALL_TIMEOUT_S = float(os.getenv("AGENT_FIRM_OVERALL_TIMEOUT", "75"))
CLAUDE_CONNECTION_TIMEOUT_S = os.getenv("AGENT_FIRM_CLAUDE_CONNECTION_TIMEOUT") or None
CLAUDE_READ_TIMEOUT_S = os.getenv("AGENT_FIRM_CLAUDE_READ_TIMEOUT") or None
CLAUDE_OVERALL_TIMEOUT_S = os.getenv("AGENT_FIRM_CLAUDE_OVERALL_TIMEOUT") or None


_runtime: dict | None = None


def set_mode(enabled: bool, enforce: bool) -> None:
    global _runtime
    _runtime = {"enabled": enabled, "enforce": enforce}


def get_enforce() -> bool:
    return _runtime["enforce"] if _runtime is not None else FIRM_ENFORCE


def get_enabled() -> bool:
    """Runtime-aware enabled flag (mirrors get_enforce); ignores the kill switch."""
    return _runtime["enabled"] if _runtime is not None else FIRM_ENABLED


def is_active() -> bool:
    enabled = _runtime["enabled"] if _runtime is not None else FIRM_ENABLED
    if not enabled:
        return False
    if KILL_SWITCH_FILE.exists():
        return False
    return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/agent_firm/test_config.py -v`
Expected: PASS (all tests, including the 6 new ones)

- [ ] **Step 5: Commit**

```bash
git add engine/agent_firm/config.py tests/agent_firm/test_config.py
git commit -m "feat(firm): rename DEEPSEEK_* config to ZAI_*, add provider/circuit/timeout vars"
```

---

### Task 7: `ZAIProvider` (renamed `DeepSeekClient`)

**Files:**
- Create: `engine/agent_firm/providers/zai.py`
- Test: `tests/agent_firm/providers/test_zai_provider.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/agent_firm/providers/test_zai_provider.py
import httpx
import pytest
import respx

from engine.agent_firm.providers.zai import ZAIProvider


@pytest.mark.asyncio
async def test_generate_returns_provider_response():
    client = ZAIProvider(api_key="sk-test", base_url="https://api.test.com/v1", model="glm-5.2")
    with respx.mock(base_url="https://api.test.com/v1") as router:
        router.post("/chat/completions").mock(return_value=httpx.Response(
            200,
            json={
                "id": "resp-1", "object": "chat.completion", "created": 0,
                "model": "glm-5.2",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "hi"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            },
        ))
        resp = await client.generate([{"role": "user", "content": "ping"}])
    assert resp.content == "hi"
    assert resp.provider == "zai"
    assert resp.tokens_in == 100
    assert resp.tokens_out == 50
    assert resp.request_id == "resp-1"
    assert resp.cost_usd == pytest.approx((100 / 1_000_000 * 0.435) + (50 / 1_000_000 * 0.870), rel=1e-9)


@pytest.mark.asyncio
async def test_generate_retries_on_500_then_succeeds():
    client = ZAIProvider(api_key="sk-test", base_url="https://api.test.com/v1")
    with respx.mock(base_url="https://api.test.com/v1") as router:
        route = router.post("/chat/completions")
        route.side_effect = [
            httpx.Response(500, json={"error": "server"}),
            httpx.Response(200, json={
                "id": "x", "object": "chat.completion", "created": 0,
                "model": "glm-5.2",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            }),
        ]
        resp = await client.generate([{"role": "user", "content": "ping"}])
    assert resp.content == "ok"
    assert route.call_count == 2


@pytest.mark.asyncio
async def test_generate_raises_provider_exception_after_retries_exhausted():
    from engine.agent_firm.providers.errors import ProviderException
    client = ZAIProvider(api_key="sk-test", base_url="https://api.test.com/v1")
    with respx.mock(base_url="https://api.test.com/v1") as router:
        router.post("/chat/completions").mock(return_value=httpx.Response(500, json={"error": "server"}))
        with pytest.raises(ProviderException):
            await client.generate([{"role": "user", "content": "ping"}], max_retries=1)


def test_cost_calc_zero_when_no_tokens():
    assert ZAIProvider._calc_cost(0, 0) == 0.0


def test_zai_capabilities():
    client = ZAIProvider(api_key="sk-test")
    assert client.capabilities.supports_json_mode is True
    assert client.capabilities.supports_json_schema is False
    assert client.name == "zai"
```

Note: `ZAIProvider.generate()` takes `max_retries` as a keyword param (matching the old `DeepSeekClient.chat(messages, timeout=None, max_retries=1)` signature) — this is provider-local retry config, separate from the `timeout` param on the `FirmLLMProvider.generate()` interface.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/agent_firm/providers/test_zai_provider.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'engine.agent_firm.providers.zai'`

- [ ] **Step 3: Write `zai.py`**

```python
# engine/agent_firm/providers/zai.py
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

import openai
from openai import AsyncOpenAI, APIError, APIStatusError, APITimeoutError, RateLimitError

from . import config
from .base import ProviderCapabilities, ProviderResponse
from .errors import (
    ProviderQuotaExceeded, ProviderRateLimited, ProviderTimeout, ProviderUnavailable,
)
from .registry import register


def _strip_fences(text: str) -> str:
    """Strip markdown code fences the model sometimes wraps around JSON."""
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    return m.group(1).strip() if m else text.strip()


def _classify(err: Exception) -> ProviderQuotaExceeded | ProviderRateLimited | ProviderTimeout | ProviderUnavailable:
    if isinstance(err, APITimeoutError):
        return ProviderTimeout(str(err))
    if isinstance(err, RateLimitError):
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
                 model: str | None = None) -> None:
        self._client = AsyncOpenAI(
            api_key=api_key or config.ZAI_API_KEY or "missing",
            base_url=base_url or config.ZAI_BASE_URL,
            max_retries=0,
        )
        self._model = model or config.MODEL_ID

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
                resp = await self._client.chat.completions.create(
                    model=self._model, messages=messages, timeout=timeout,
                    response_format={"type": "json_object"},
                )
                content = _strip_fences(resp.choices[0].message.content or "")
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/agent_firm/providers/test_zai_provider.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add engine/agent_firm/providers/zai.py tests/agent_firm/providers/test_zai_provider.py
git commit -m "feat(firm): add ZAIProvider (renamed from DeepSeekClient)"
```

---

### Task 8: Delete the old `DeepSeekClient` module and its test

**Files:**
- Delete: `engine/agent_firm/client.py`
- Delete: `tests/agent_firm/test_client.py`

- [ ] **Step 1: Confirm nothing outside this plan's later tasks still imports it**

Run: `grep -rln "agent_firm.client\|DeepSeekClient" --include="*.py" . | grep -v __pycache__`
Expected: only `engine/agent_firm/firm.py`, `engine/agent_firm/schemas.py`, and the 7 `engine/agent_firm/agents/*.py` files — all handled in Tasks 13/14/15 below. If anything else shows up, stop and investigate before deleting.

- [ ] **Step 2: Delete the old files**

```bash
git rm engine/agent_firm/client.py tests/agent_firm/test_client.py
```

- [ ] **Step 3: Commit**

```bash
git commit -m "chore(firm): delete DeepSeekClient — replaced by ZAIProvider"
```

(Full-suite verification that nothing is broken happens naturally in Task 15, once `firm.py` and the 7 agent modules stop referencing `DeepSeekClient` — don't run the full suite yet, it will show expected `ImportError`s until then.)

---

### Task 9: `ClaudeProvider`

**Files:**
- Create: `engine/agent_firm/providers/claude.py`
- Test: `tests/agent_firm/providers/test_claude_provider.py`

**Note:** the exact JSON shape of `claude -p ... --output-format json` is assumed here (`result`, `session_id`, `usage.input_tokens`/`usage.output_tokens`) based on the currently-installed CLI's documented behavior — Task 20 includes a live smoke call that verifies this and requires adjusting the field names below if the real output differs.

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent_firm/providers/test_claude_provider.py
import asyncio
import json
import subprocess
from unittest.mock import AsyncMock, patch

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
async def test_generate_raises_provider_timeout_on_wait_for_timeout():
    provider = ClaudeProvider(overall_timeout=0.01)

    async def _hang(*a, **k):
        await asyncio.sleep(10)
        return b"", b""

    hung_proc = AsyncMock()
    hung_proc.communicate = _hang
    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=hung_proc)):
        with pytest.raises(ProviderTimeout):
            await provider.generate([{"role": "user", "content": "x"}])


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/agent_firm/providers/test_claude_provider.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'engine.agent_firm.providers.claude'`

- [ ] **Step 3: Write `claude.py`**

```python
# engine/agent_firm/providers/claude.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/agent_firm/providers/test_claude_provider.py -v`
Expected: PASS (9 tests)

- [ ] **Step 5: Commit**

```bash
git add engine/agent_firm/providers/claude.py tests/agent_firm/providers/test_claude_provider.py
git commit -m "feat(firm): add ClaudeProvider via claude CLI subprocess"
```

---

### Task 10: Provider Factory (`TimeoutPolicy` + `build_router()` + config validation)

**Files:**
- Create: `engine/agent_firm/providers/factory.py`
- Test: `tests/agent_firm/providers/test_factory.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent_firm/providers/test_factory.py
import importlib

import pytest


def _reload_factory():
    from engine.agent_firm import config
    from engine.agent_firm.providers import factory
    importlib.reload(config)
    importlib.reload(factory)
    return factory


def test_build_router_single_provider_mode(monkeypatch):
    monkeypatch.setenv("AGENT_FIRM_PROVIDER", "zai")
    factory = _reload_factory()
    router = factory.build_router()
    assert len(router._routed) == 1
    assert router._routed[0][0].name == "zai"


def test_build_router_auto_mode_uses_provider_order(monkeypatch):
    monkeypatch.setenv("AGENT_FIRM_PROVIDER", "auto")
    monkeypatch.setenv("AGENT_FIRM_PROVIDER_ORDER", "claude,zai")
    factory = _reload_factory()
    router = factory.build_router()
    assert [p.name for p, _ in router._routed] == ["claude", "zai"]


def test_build_router_rejects_invalid_provider_mode(monkeypatch):
    monkeypatch.setenv("AGENT_FIRM_PROVIDER", "bogus")
    factory = _reload_factory()
    with pytest.raises(ValueError, match="invalid AGENT_FIRM_PROVIDER"):
        factory.build_router()


def test_build_router_rejects_unregistered_provider_in_order(monkeypatch):
    monkeypatch.setenv("AGENT_FIRM_PROVIDER", "auto")
    monkeypatch.setenv("AGENT_FIRM_PROVIDER_ORDER", "claude,openai")
    factory = _reload_factory()
    with pytest.raises(ValueError, match="unregistered"):
        factory.build_router()


def test_build_router_rejects_duplicate_names_in_order(monkeypatch):
    monkeypatch.setenv("AGENT_FIRM_PROVIDER", "auto")
    monkeypatch.setenv("AGENT_FIRM_PROVIDER_ORDER", "claude,claude")
    factory = _reload_factory()
    with pytest.raises(ValueError, match="duplicate"):
        factory.build_router()


def test_build_router_rejects_empty_order(monkeypatch):
    monkeypatch.setenv("AGENT_FIRM_PROVIDER", "auto")
    monkeypatch.setenv("AGENT_FIRM_PROVIDER_ORDER", "")
    factory = _reload_factory()
    with pytest.raises(ValueError, match="must not be empty"):
        factory.build_router()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/agent_firm/providers/test_factory.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'engine.agent_firm.providers.factory'`

- [ ] **Step 3: Write `factory.py`**

```python
# engine/agent_firm/providers/factory.py
"""Builds a ready-to-use ProviderRouter from AGENT_FIRM_* config (design doc
§5). The Router never constructs providers itself — this is the one place
that reads raw config, resolves provider names via the Registry, injects
every runtime dependency, and fails loud on invalid config."""

from . import config
from .circuit_breaker import CircuitBreaker
from .registry import build as _build_provider, registered_names
from .router import ProviderRouter


class TimeoutPolicy:
    def __init__(self, connection_timeout: float, read_timeout: float, overall_timeout: float):
        self.connection_timeout = connection_timeout
        self.read_timeout = read_timeout
        self.overall_timeout = overall_timeout


def _timeout_policy_for(name: str) -> TimeoutPolicy:
    if name == "claude":
        return TimeoutPolicy(
            connection_timeout=float(config.CLAUDE_CONNECTION_TIMEOUT_S or config.CONNECTION_TIMEOUT_S),
            read_timeout=float(config.CLAUDE_READ_TIMEOUT_S or config.READ_TIMEOUT_S),
            overall_timeout=float(config.CLAUDE_OVERALL_TIMEOUT_S or config.OVERALL_TIMEOUT_S),
        )
    return TimeoutPolicy(
        connection_timeout=config.CONNECTION_TIMEOUT_S,
        read_timeout=config.READ_TIMEOUT_S,
        overall_timeout=config.OVERALL_TIMEOUT_S,
    )


def _construct(name: str):
    if name == "claude":
        policy = _timeout_policy_for("claude")
        return _build_provider(
            "claude",
            model=config.CLAUDE_MODEL,
            max_concurrent=config.CLAUDE_MAX_CONCURRENT,
            overall_timeout=policy.overall_timeout,
        )
    return _build_provider(name)


def _validate() -> list[str]:
    mode = config.PROVIDER_MODE
    if mode not in ("claude", "zai", "auto"):
        raise ValueError(
            f"invalid AGENT_FIRM_PROVIDER={mode!r}; must be one of claude, zai, auto"
        )
    if mode != "auto":
        return [mode]

    order = config.PROVIDER_ORDER
    if not order:
        raise ValueError(
            "AGENT_FIRM_PROVIDER_ORDER must not be empty when AGENT_FIRM_PROVIDER=auto"
        )
    unknown = [n for n in order if n not in registered_names()]
    if unknown:
        raise ValueError(
            f"AGENT_FIRM_PROVIDER_ORDER contains unregistered provider(s) {unknown}; "
            f"registered: {registered_names()}"
        )
    if len(set(order)) != len(order):
        raise ValueError(f"AGENT_FIRM_PROVIDER_ORDER contains duplicate provider names: {order}")
    return order


def build_router() -> ProviderRouter:
    order = _validate()
    routed = [
        (_construct(name), CircuitBreaker(
            failure_threshold=config.CIRCUIT_FAILURES, cooldown_s=config.CIRCUIT_COOLDOWN_S,
        ))
        for name in order
    ]
    import data.db as _db
    return ProviderRouter(routed, db_path=str(_db.DB_PATH))
```

Note: `factory.py` imports `.router` (Task 11, not yet written) — this task and Task 11 must land together; write `router.py` (Task 11) immediately after this step, before running the factory tests, since `test_factory.py` exercises `build_router()` end-to-end (including the real `zai`/`claude` provider construction from the Registry, which requires `ProviderRouter` to exist for the import chain to resolve).

- [ ] **Step 4: Run test to verify it passes** (after Task 11 is also done)

Run: `pytest tests/agent_firm/providers/test_factory.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit** (combined with Task 11's commit, since they land together — see Task 11 Step 5)

---

### Task 11: Provider Router

**Files:**
- Create: `engine/agent_firm/providers/router.py`
- Test: `tests/agent_firm/providers/test_router.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent_firm/providers/test_router.py
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from engine.agent_firm.providers.base import ProviderCapabilities, ProviderResponse
from engine.agent_firm.providers.circuit_breaker import CircuitBreaker
from engine.agent_firm.providers.errors import ProviderTimeout, ProviderUnavailable
from engine.agent_firm.providers.router import ProviderRouter


def _resp(provider="claude") -> ProviderResponse:
    return ProviderResponse(
        content="ok", provider=provider, model="m", runtime_version="v",
        tokens_in=1, tokens_out=1, cost_usd=0.0, duration_s=0.1,
        timestamp=datetime.now(timezone.utc),
    )


def _fake_provider(name, generate_result=None, generate_error=None):
    p = AsyncMock()
    p.name = name
    p.capabilities = ProviderCapabilities(supports_json_mode=True, supports_json_schema=True, supports_tools=True)
    if generate_error is not None:
        p.generate.side_effect = generate_error
    else:
        p.generate.return_value = generate_result or _resp(name)
    return p


@pytest.mark.asyncio
async def test_generate_uses_first_provider_on_success():
    p1 = _fake_provider("claude")
    router = ProviderRouter([(p1, CircuitBreaker())])
    resp = await router.generate([{"role": "user", "content": "x"}])
    assert resp.provider == "claude"
    assert resp.failover is False


@pytest.mark.asyncio
async def test_generate_fails_over_to_second_provider_on_exception():
    p1 = _fake_provider("claude", generate_error=ProviderUnavailable("down"))
    p2 = _fake_provider("zai")
    router = ProviderRouter([(p1, CircuitBreaker()), (p2, CircuitBreaker())])
    resp = await router.generate([{"role": "user", "content": "x"}])
    assert resp.provider == "zai"
    assert resp.failover is True


@pytest.mark.asyncio
async def test_generate_raises_when_all_providers_fail():
    p1 = _fake_provider("claude", generate_error=ProviderUnavailable("down"))
    p2 = _fake_provider("zai", generate_error=ProviderTimeout("slow"))
    router = ProviderRouter([(p1, CircuitBreaker()), (p2, CircuitBreaker())])
    with pytest.raises(ProviderTimeout):
        await router.generate([{"role": "user", "content": "x"}])


@pytest.mark.asyncio
async def test_open_circuit_skips_provider_without_calling_generate():
    p1 = _fake_provider("claude")
    breaker = CircuitBreaker(failure_threshold=1, cooldown_s=999)
    breaker.record_failure()
    assert breaker.state == "OPEN"
    p2 = _fake_provider("zai")
    router = ProviderRouter([(p1, breaker), (p2, CircuitBreaker())])
    resp = await router.generate([{"role": "user", "content": "x"}])
    assert resp.provider == "zai"
    p1.generate.assert_not_called()


@pytest.mark.asyncio
async def test_single_provider_failure_propagates_with_no_fallback():
    p1 = _fake_provider("claude", generate_error=ProviderUnavailable("down"))
    router = ProviderRouter([(p1, CircuitBreaker())])
    with pytest.raises(ProviderUnavailable):
        await router.generate([{"role": "user", "content": "x"}])


@pytest.mark.asyncio
async def test_claude_daily_cap_reached_skips_to_next_provider(tmp_path, monkeypatch):
    import datetime as _dt
    import sqlite3
    from data.db import init_agent_firm_tables

    db_path = tmp_path / "t.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    import importlib
    from data import db as data_db
    importlib.reload(data_db)
    init_agent_firm_tables()

    conn = sqlite3.connect(db_path)
    today = _dt.date.today().isoformat()
    for _ in range(3):
        conn.execute(
            "INSERT INTO agent_traces (role, provider, created_at) VALUES (?,?,?)",
            ("technical", "claude", f"{today} 09:00:00"),
        )
    conn.commit()
    conn.close()

    from engine.agent_firm import config as _cfg
    monkeypatch.setattr(_cfg, "CLAUDE_MAX_CALLS_PER_DAY", 3)

    p1 = _fake_provider("claude")
    p2 = _fake_provider("zai")
    router = ProviderRouter([(p1, CircuitBreaker()), (p2, CircuitBreaker())], db_path=str(db_path))
    resp = await router.generate([{"role": "user", "content": "x"}])
    assert resp.provider == "zai"
    p1.generate.assert_not_called()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/agent_firm/providers/test_router.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'engine.agent_firm.providers.router'`

- [ ] **Step 3: Write `router.py`**

```python
# engine/agent_firm/providers/router.py
"""Owns provider selection, ordering, and cross-provider failover (design
doc §4). Providers stay dumb; the Router never constructs them (see
factory.py)."""

import datetime
import logging

from . import config
from .base import ProviderResponse
from .errors import ProviderException, ProviderUnavailable
from .events import ProviderEvent, log_provider_event

logger = logging.getLogger("agent_firm.providers.router")


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _claude_daily_call_count(db_path: str) -> int:
    from ..tools.sqlite_query import query
    try:
        rows = query(
            db_path,
            "SELECT COUNT(*) AS c FROM agent_traces WHERE provider='claude' "
            "AND DATE(created_at) = ?",
            (datetime.date.today().isoformat(),),
        )
        return int(rows[0]["c"]) if rows else 0
    except Exception:
        return 0


class ProviderRouter:
    name = "router"

    def __init__(self, routed, db_path: str | None = None):
        self._routed = routed  # list[tuple[FirmLLMProvider, CircuitBreaker]]
        self._db_path = db_path

    def model(self) -> str:
        return self._routed[0][0].model() if self._routed else ""

    async def health(self) -> bool:
        results = [await p.health() for p, _ in self._routed]
        return any(results)

    async def generate(self, messages, *, timeout=None) -> ProviderResponse:
        last_err: ProviderException | None = None
        for i, (provider, breaker) in enumerate(self._routed):
            if not breaker.allow_request():
                log_provider_event(ProviderEvent(
                    event_type="provider_failover", timestamp=_now(),
                    provider=provider.name, reason="circuit open",
                ))
                continue

            if provider.name == "claude" and self._db_path is not None:
                if _claude_daily_call_count(self._db_path) >= config.CLAUDE_MAX_CALLS_PER_DAY:
                    breaker.release_trial()
                    log_provider_event(ProviderEvent(
                        event_type="provider_quota_exceeded", timestamp=_now(),
                        provider=provider.name, reason="daily call cap reached",
                    ))
                    continue

            try:
                resp = await provider.generate(messages, timeout=timeout)
            except ProviderException as err:
                just_opened = breaker.record_failure()
                last_err = err
                event_type = (
                    "provider_timeout" if type(err).__name__ == "ProviderTimeout"
                    else "provider_failed"
                )
                log_provider_event(ProviderEvent(
                    event_type=event_type, timestamp=_now(),
                    provider=provider.name, reason=str(err),
                ))
                if just_opened:
                    log_provider_event(ProviderEvent(
                        event_type="provider_circuit_open", timestamp=_now(),
                        provider=provider.name, reason=str(err),
                    ))
                continue
            else:
                just_closed = breaker.record_success()
                if just_closed:
                    log_provider_event(ProviderEvent(
                        event_type="provider_circuit_closed", timestamp=_now(),
                        provider=provider.name,
                    ))
                resp.failover = i > 0
                log_provider_event(ProviderEvent(
                    event_type="provider_failover" if resp.failover else "provider_selected",
                    timestamp=_now(), provider=provider.name, model=resp.model,
                    duration_s=resp.duration_s, request_id=resp.request_id,
                    failover=resp.failover,
                ))
                return resp
        raise last_err or ProviderUnavailable("no providers available")
```

- [ ] **Step 4: Run both Router and Factory tests to verify they pass**

Run: `pytest tests/agent_firm/providers/test_router.py tests/agent_firm/providers/test_factory.py -v`
Expected: PASS (7 Router tests + 6 Factory tests)

- [ ] **Step 5: Commit both Task 10 and Task 11 together**

```bash
git add engine/agent_firm/providers/factory.py engine/agent_firm/providers/router.py \
        tests/agent_firm/providers/test_factory.py tests/agent_firm/providers/test_router.py
git commit -m "feat(firm): add ProviderRouter (ordered failover + circuit breaker + daily cap) and ProviderFactory"
```

---

### Task 12: Persistence migration — `agent_traces`/`agent_decisions` columns + `provider_events` table

**Files:**
- Modify: `data/db.py`
- Modify: `tests/agent_firm/test_migration.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/agent_firm/test_migration.py`:

```python
def test_agent_traces_has_provider_columns(tmp_db):
    conn = sqlite3.connect(tmp_db)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(agent_traces)")}
    assert {"provider", "model", "runtime_version", "failover", "error"}.issubset(cols)


def test_agent_decisions_has_providers_used(tmp_db):
    conn = sqlite3.connect(tmp_db)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(agent_decisions)")}
    assert "providers_used" in cols


def test_provider_events_table_exists(tmp_db):
    conn = sqlite3.connect(tmp_db)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(provider_events)")}
    expected = {"id", "event_type", "provider", "model", "reason",
                "duration_s", "request_id", "failover", "created_at"}
    assert expected.issubset(cols)


def test_provider_events_index_exists(tmp_db):
    conn = sqlite3.connect(tmp_db)
    idx = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}
    assert "idx_provider_events_provider_date" in idx


def test_migration_idempotent_on_existing_db(tmp_db):
    """Calling init_agent_firm_tables() twice must not error (existing columns)."""
    from data.db import init_agent_firm_tables
    init_agent_firm_tables()
    init_agent_firm_tables()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/agent_firm/test_migration.py -v`
Expected: FAIL — `test_agent_traces_has_provider_columns`, `test_agent_decisions_has_providers_used`, `test_provider_events_table_exists`, `test_provider_events_index_exists` all FAIL (columns/table don't exist yet)

- [ ] **Step 3: Update `init_agent_firm_tables()` in `data/db.py`**

```python
def init_agent_firm_tables():
    """Idempotent migration for Phase 1 agent firm tables. Safe to call repeatedly."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS agent_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_time TEXT NOT NULL,
            ticker TEXT NOT NULL,
            strategy TEXT NOT NULL,
            quant_score REAL,
            decision TEXT NOT NULL,
            confidence REAL,
            size_hint REAL,
            rationale TEXT,
            overridden INTEGER DEFAULT 0,
            tokens_in INTEGER,
            tokens_out INTEGER,
            cost_usd REAL,
            duration_s REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(scan_time, ticker, strategy)
        );
        CREATE INDEX IF NOT EXISTS idx_agent_decisions_ticker_date
            ON agent_decisions(ticker, scan_time);

        CREATE TABLE IF NOT EXISTS agent_traces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_id INTEGER REFERENCES agent_decisions(id) ON DELETE CASCADE,
            role TEXT NOT NULL,
            prompt_version TEXT,
            output TEXT,
            tools_called TEXT,
            tokens_in INTEGER,
            tokens_out INTEGER,
            duration_s REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_agent_traces_decision
            ON agent_traces(decision_id);

        CREATE TABLE IF NOT EXISTS scheduled_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_time TEXT NOT NULL,
            ticker TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS provider_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT,
            reason TEXT,
            duration_s REAL,
            request_id TEXT,
            failover INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_provider_events_provider_date
            ON provider_events(provider, created_at);
    """)

    cols = {r[1] for r in conn.execute("PRAGMA table_info(scheduled_signals)")}
    if "agent_decision_id" not in cols:
        conn.execute(
            "ALTER TABLE scheduled_signals ADD COLUMN agent_decision_id INTEGER "
            "REFERENCES agent_decisions(id)"
        )

    trace_cols = {r[1] for r in conn.execute("PRAGMA table_info(agent_traces)")}
    for col, ddl in [
        ("provider", "ALTER TABLE agent_traces ADD COLUMN provider TEXT"),
        ("model", "ALTER TABLE agent_traces ADD COLUMN model TEXT"),
        ("runtime_version", "ALTER TABLE agent_traces ADD COLUMN runtime_version TEXT"),
        ("failover", "ALTER TABLE agent_traces ADD COLUMN failover INTEGER DEFAULT 0"),
        ("error", "ALTER TABLE agent_traces ADD COLUMN error TEXT"),
    ]:
        if col not in trace_cols:
            conn.execute(ddl)

    decision_cols = {r[1] for r in conn.execute("PRAGMA table_info(agent_decisions)")}
    if "providers_used" not in decision_cols:
        conn.execute("ALTER TABLE agent_decisions ADD COLUMN providers_used TEXT")

    conn.commit()
    conn.close()
```

(Note the `error` column: not in the locked design doc's Persistence §11 — added here because Metrics §12 needs to compute `failures`/`timeouts` per provider, which requires knowing whether each trace failed; see the plan header's scope note.)

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/agent_firm/test_migration.py -v`
Expected: PASS (all tests, including the 5 new ones)

- [ ] **Step 5: Commit**

```bash
git add data/db.py tests/agent_firm/test_migration.py
git commit -m "feat(firm): migrate agent_traces/agent_decisions for provider tracking + add provider_events table"
```

---

### Task 13: Schema updates — `AgentResult`/`AgentDecision` new fields

**Files:**
- Modify: `engine/agent_firm/schemas.py`
- Test: `tests/agent_firm/test_schemas.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/agent_firm/test_schemas.py` (check the file first for existing import style/fixtures and match it):

```python
def test_agent_result_provider_fields_default_empty():
    from engine.agent_firm.schemas import AgentResult
    r = AgentResult(role="technical", status="ok")
    assert r.provider == ""
    assert r.model == ""
    assert r.runtime_version == ""
    assert r.failover is False
    assert r.cost_usd == 0.0


def test_agent_decision_providers_used_defaults_empty_list():
    from engine.agent_firm.schemas import AgentDecision
    d = AgentDecision(
        ticker="BBRI", strategy="x", scan_time="t", quant_score=1.0, decision="approve",
    )
    assert d.providers_used == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/agent_firm/test_schemas.py -v`
Expected: FAIL with `AttributeError` (no such field yet — pydantic ignores unset extras by default, so accessing `.provider` raises `AttributeError` since it's not defined)

- [ ] **Step 3: Update `schemas.py`**

```python
class AgentResult(BaseModel):
    role: str
    status: Literal["ok", "failed"]
    output: Optional[dict[str, Any]] = None
    prompt_version: str = "v1"
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    duration_s: float = 0.0
    tools_called: list[dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None
    provider: str = ""
    model: str = ""
    runtime_version: str = ""
    failover: bool = False


class AgentDecision(BaseModel):
    ticker: str
    strategy: str
    scan_time: str
    quant_score: float
    decision: Literal["approve", "veto", "bypassed", "degraded"]
    confidence: Optional[float] = None
    size_hint: Optional[float] = None
    rationale: Optional[str] = None
    traces: list[AgentResult] = Field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    duration_s: float = 0.0
    providers_used: list[str] = Field(default_factory=list)


class AgentState(TypedDict):
    candidate: SignalCandidate
    db_path: str
    context: dict[str, Any]
    client: Any  # FirmLLMProvider (in practice, the ProviderRouter) — in-memory only, not serialized
    technical_result: Optional[AgentResult]
    flow_result: Optional[AgentResult]
    regime_result: Optional[AgentResult]
    news_result: Optional[AgentResult]
    bull_result: Optional[AgentResult]
    bear_result: Optional[AgentResult]
    risk_result: Optional[AgentResult]
    decision: Optional[AgentDecision]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/agent_firm/test_schemas.py -v`
Expected: PASS (all tests, including the 2 new ones)

- [ ] **Step 5: Commit**

```bash
git add engine/agent_firm/schemas.py tests/agent_firm/test_schemas.py
git commit -m "feat(firm): add provider/model/runtime_version/failover/cost_usd fields to AgentResult, providers_used to AgentDecision"
```

---

### Task 14: Rename `client.chat()` → `client.generate()` across all 7 agent modules

**Files:**
- Modify: `engine/agent_firm/agents/bear.py`, `bull.py`, `flow.py`, `news.py`, `regime.py`, `risk.py`, `technical.py`
- Modify: `tests/agent_firm/test_bear.py`, `test_bull.py`, `test_flow.py`, `test_news.py`, `test_regime.py`, `test_risk.py`, `test_risk_v2.py`, `test_technical.py`

Each agent module currently imports `DeepSeekClient` only for a type hint, calls `client.chat(messages)`, and reads the response as a dict (`resp["content"]`, `resp["tokens_in"]`, ...). This task switches every one of them to `client.generate(messages)` returning a `ProviderResponse` (attribute access), and threads `provider`/`model`/`cost_usd`/`runtime_version`/`failover` from the response into the `AgentResult` they build.

- [ ] **Step 1: Update all 8 test files first (still failing — source not yet changed)**

```python
# tests/agent_firm/test_bear.py — full replacement
import json
from datetime import datetime, timezone

import pytest
from unittest.mock import AsyncMock

from engine.agent_firm.agents import bear
from engine.agent_firm.providers.base import ProviderResponse
from engine.agent_firm.schemas import AgentResult, SignalCandidate


def _make_candidate():
    return SignalCandidate(
        ticker="BBRI", strategy="vol_weighted",
        score=3.8, scan_time="2026-05-20T10:00:00+07:00",
    )


def _make_analysts():
    return [
        AgentResult(role="technical", status="ok",
                    output={"verdict": "BULLISH", "conviction": 0.7}),
        AgentResult(role="flow", status="ok",
                    output={"flow_verdict": "ACCUMULATING"}),
        AgentResult(role="regime", status="ok",
                    output={"regime_call": "BULL"}),
        AgentResult(role="news", status="ok",
                    output={"sentiment": "BULLISH"}),
    ]


def _make_bull():
    return AgentResult(
        role="bull", status="ok",
        output={"bull_case": "Strong flow + trend.", "key_strength": "Foreign accumulation"},
    )


def _response(content: str, tokens_in=1200, tokens_out=85) -> ProviderResponse:
    return ProviderResponse(
        content=content, provider="zai", model="glm-5.2", runtime_version="1.0.0",
        tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=0.0006, duration_s=3.2,
        timestamp=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_bear_returns_ok_on_success():
    fake_client = AsyncMock()
    fake_client.generate.return_value = _response(json.dumps({
        "bear_case": "Foreign flows can reverse rapidly if BI surprises.",
        "key_risk": "BI rate surprise causing sector rotation out of banks",
    }))
    result = await bear.run(_make_candidate(), _make_analysts(), _make_bull(), fake_client)
    assert result.role == "bear"
    assert result.status == "ok"
    assert "bear_case" in result.output
    assert result.tokens_in == 1200
    assert result.provider == "zai"


@pytest.mark.asyncio
async def test_bear_returns_failed_on_invalid_json():
    fake_client = AsyncMock()
    fake_client.generate.return_value = _response("nope", tokens_in=50, tokens_out=3)
    result = await bear.run(_make_candidate(), _make_analysts(), _make_bull(), fake_client)
    assert result.status == "failed"


@pytest.mark.asyncio
async def test_bear_returns_failed_on_client_exception():
    fake_client = AsyncMock()
    fake_client.generate.side_effect = RuntimeError("conn reset")
    result = await bear.run(_make_candidate(), _make_analysts(), _make_bull(), fake_client)
    assert result.status == "failed"
    assert "conn reset" in result.error
```

```python
# tests/agent_firm/test_bull.py — full replacement
import json
from datetime import datetime, timezone

import pytest
from unittest.mock import AsyncMock

from engine.agent_firm.agents import bull
from engine.agent_firm.providers.base import ProviderResponse
from engine.agent_firm.schemas import AgentResult, SignalCandidate


def _make_candidate():
    return SignalCandidate(
        ticker="BBRI", strategy="vol_weighted",
        score=3.8, scan_time="2026-05-20T10:00:00+07:00",
    )


def _make_analysts():
    return [
        AgentResult(role="technical", status="ok",
                    output={"verdict": "BULLISH", "conviction": 0.7}),
        AgentResult(role="flow", status="ok",
                    output={"flow_verdict": "ACCUMULATING", "smart_money_signal": "BUY"}),
        AgentResult(role="regime", status="ok",
                    output={"regime_call": "BULL", "sector_tailwind": True}),
        AgentResult(role="news", status="ok",
                    output={"sentiment": "BULLISH", "catalyst": "bullish"}),
    ]


def _response(content: str, tokens_in=1100, tokens_out=80) -> ProviderResponse:
    return ProviderResponse(
        content=content, provider="zai", model="glm-5.2", runtime_version="1.0.0",
        tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=0.0005, duration_s=3.0,
        timestamp=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_bull_returns_ok_on_success():
    fake_client = AsyncMock()
    fake_client.generate.return_value = _response(json.dumps({
        "bull_case": "Foreign accumulation + earnings beat creates strong entry.",
        "key_strength": "Smart money accumulation with bullish technicals",
    }))
    result = await bull.run(_make_candidate(), _make_analysts(), fake_client)
    assert result.role == "bull"
    assert result.status == "ok"
    assert "bull_case" in result.output
    assert result.tokens_in == 1100
    assert result.provider == "zai"


@pytest.mark.asyncio
async def test_bull_returns_failed_on_invalid_json():
    fake_client = AsyncMock()
    fake_client.generate.return_value = _response("bad", tokens_in=50, tokens_out=3)
    result = await bull.run(_make_candidate(), _make_analysts(), fake_client)
    assert result.status == "failed"


@pytest.mark.asyncio
async def test_bull_returns_failed_on_client_exception():
    fake_client = AsyncMock()
    fake_client.generate.side_effect = RuntimeError("llm down")
    result = await bull.run(_make_candidate(), _make_analysts(), fake_client)
    assert result.status == "failed"
    assert "llm down" in result.error
```

```python
# tests/agent_firm/test_flow.py — full replacement
import json
from datetime import datetime, timezone

import pytest
from unittest.mock import AsyncMock

from engine.agent_firm.agents import flow
from engine.agent_firm.providers.base import ProviderResponse
from engine.agent_firm.schemas import SignalCandidate


def _make_candidate():
    return SignalCandidate(
        ticker="BBRI", strategy="vol_weighted",
        score=3.8, scan_time="2026-05-20T10:00:00+07:00",
    )


def _make_context(verdict="ACCUMULATING"):
    return {
        "stockbit_flow": [
            {"trade_date": "2026-05-19", "buy_lot": 5000, "sell_lot": 2000,
             "net_lot": 3000, "net_value": 1500000000, "verdict": "BUY",
             "smart_money": "YES", "foreign_score": 2.5, "composite_score": 8},
        ],
        "broker_flow": [
            {"trade_date": "2026-05-19", "broker_code": "BK", "side": "BUY",
             "lot_value": 1000000000, "investor_type": "Asing"},
        ],
        "stockbit_flow_bars": [],
    }


def _response(content: str, tokens_in=800, tokens_out=60) -> ProviderResponse:
    return ProviderResponse(
        content=content, provider="zai", model="glm-5.2", runtime_version="1.0.0",
        tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=0.0004, duration_s=2.5,
        timestamp=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_flow_returns_ok_on_success():
    fake_client = AsyncMock()
    fake_client.generate.return_value = _response(json.dumps({
        "flow_verdict": "ACCUMULATING",
        "smart_money_signal": "BUY",
        "net_foreign_14d": 3000,
        "reasoning": "Consistent net buying with smart money",
    }))
    result = await flow.run(_make_candidate(), fake_client, _make_context())
    assert result.role == "flow"
    assert result.status == "ok"
    assert result.output["flow_verdict"] == "ACCUMULATING"
    assert result.tokens_in == 800


@pytest.mark.asyncio
async def test_flow_returns_failed_on_invalid_json():
    fake_client = AsyncMock()
    fake_client.generate.return_value = _response("not json", tokens_in=100, tokens_out=5)
    result = await flow.run(_make_candidate(), fake_client, _make_context())
    assert result.status == "failed"


@pytest.mark.asyncio
async def test_flow_returns_failed_on_client_exception():
    fake_client = AsyncMock()
    fake_client.generate.side_effect = RuntimeError("timeout")
    result = await flow.run(_make_candidate(), fake_client, _make_context())
    assert result.status == "failed"
    assert "timeout" in result.error
```

```python
# tests/agent_firm/test_news.py — full replacement
import json
from datetime import datetime, timezone

import pytest
from unittest.mock import AsyncMock

from engine.agent_firm.agents import news
from engine.agent_firm.providers.base import ProviderResponse
from engine.agent_firm.schemas import SignalCandidate


def _make_candidate():
    return SignalCandidate(
        ticker="BBRI", strategy="vol_weighted",
        score=3.8, scan_time="2026-05-20T10:00:00+07:00",
    )


def _make_context():
    return {
        "news_mentions": [
            {"ticker": "BBRI", "date": "2026-05-19", "count": 3,
             "headlines": ["BBRI earnings beat", "BI rate hold", "Foreign buy BBRI"]},
        ],
    }


def _response(content: str, tokens_in=900, tokens_out=70) -> ProviderResponse:
    return ProviderResponse(
        content=content, provider="zai", model="glm-5.2", runtime_version="1.0.0",
        tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=0.0005, duration_s=3.0,
        timestamp=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_news_returns_ok_on_success(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "")
    fake_client = AsyncMock()
    fake_client.generate.return_value = _response(json.dumps({
        "sentiment": "BULLISH",
        "catalyst": "bullish",
        "key_headline": "BBRI earnings beat",
        "summary": "Strong earnings and foreign inflow support bullish thesis",
    }))
    result = await news.run(_make_candidate(), fake_client, _make_context())
    assert result.role == "news"
    assert result.status == "ok"
    assert result.output["sentiment"] == "BULLISH"
    assert result.tokens_in == 900


@pytest.mark.asyncio
async def test_news_returns_failed_on_invalid_json(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "")
    fake_client = AsyncMock()
    fake_client.generate.return_value = _response("not json", tokens_in=50, tokens_out=3)
    result = await news.run(_make_candidate(), fake_client, _make_context())
    assert result.status == "failed"


@pytest.mark.asyncio
async def test_news_returns_failed_on_client_exception(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "")
    fake_client = AsyncMock()
    fake_client.generate.side_effect = RuntimeError("api down")
    result = await news.run(_make_candidate(), fake_client, _make_context())
    assert result.status == "failed"
    assert "api down" in result.error
```

```python
# tests/agent_firm/test_regime.py — full replacement
import json
from datetime import datetime, timezone

import pytest
from unittest.mock import AsyncMock

from engine.agent_firm.agents import regime
from engine.agent_firm.providers.base import ProviderResponse
from engine.agent_firm.schemas import SignalCandidate


def _make_candidate():
    return SignalCandidate(
        ticker="BBRI", strategy="vol_weighted",
        score=3.8, scan_time="2026-05-20T10:00:00+07:00",
        regime="BULL",
    )


def _make_context():
    return {
        "wf_scores": [
            {"strategy": "vol_weighted", "consistency_pct": 68.0,
             "avg_return_pct": 3.2, "avg_sharpe": 1.1, "weighted_score": 72.0},
        ],
        "sector_data": [
            {"date": "2026-05-19", "signal": "BUY", "vpin_label": "NORMAL", "vol_ratio": 1.8},
        ],
    }


def _response(content: str, tokens_in=700, tokens_out=55) -> ProviderResponse:
    return ProviderResponse(
        content=content, provider="zai", model="glm-5.2", runtime_version="1.0.0",
        tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=0.0003, duration_s=2.0,
        timestamp=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_regime_returns_ok_on_success():
    fake_client = AsyncMock()
    fake_client.generate.return_value = _response(json.dumps({
        "regime_call": "BULL",
        "sector_tailwind": True,
        "macro_risk": "LOW",
        "reasoning": "Consistent walk-forward with elevated VPIN",
    }))
    result = await regime.run(_make_candidate(), fake_client, _make_context())
    assert result.role == "regime"
    assert result.status == "ok"
    assert result.output["regime_call"] == "BULL"


@pytest.mark.asyncio
async def test_regime_returns_failed_on_invalid_json():
    fake_client = AsyncMock()
    fake_client.generate.return_value = _response("bad json", tokens_in=50, tokens_out=3)
    result = await regime.run(_make_candidate(), fake_client, _make_context())
    assert result.status == "failed"


@pytest.mark.asyncio
async def test_regime_returns_failed_on_client_exception():
    fake_client = AsyncMock()
    fake_client.generate.side_effect = RuntimeError("network down")
    result = await regime.run(_make_candidate(), fake_client, _make_context())
    assert result.status == "failed"
    assert "network down" in result.error
```

```python
# tests/agent_firm/test_technical.py — full replacement
import json
import sqlite3
from datetime import datetime, timezone

import pytest
from unittest.mock import AsyncMock

from engine.agent_firm.agents import technical
from engine.agent_firm.providers.base import ProviderResponse
from engine.agent_firm.schemas import SignalCandidate


def _seed(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ohlcv (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT, date TEXT, open REAL, high REAL,
            low REAL, close REAL, volume REAL
        )
    """)
    rows = [("BBRI", f"2026-05-{d:02d}", 5000+d, 5100+d, 4950+d, 5050+d, 1e6) for d in range(1, 20)]
    conn.executemany(
        "INSERT INTO ohlcv (ticker, date, open, high, low, close, volume) VALUES (?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()
    conn.close()


def _response(content: str, tokens_in=1200, tokens_out=80) -> ProviderResponse:
    return ProviderResponse(
        content=content, provider="zai", model="glm-5.2", runtime_version="1.0.0",
        tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=0.0006, duration_s=3.2,
        timestamp=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_technical_returns_ok_result_on_success(tmp_path):
    db = tmp_path / "t.db"
    _seed(db)
    candidate = SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=4.2, scan_time="2026-05-19T16:00:00+07:00",
    )
    fake_client = AsyncMock()
    fake_client.generate.return_value = _response(json.dumps({
        "verdict": "BULLISH",
        "conviction": 0.75,
        "key_levels": {"support": 5000, "resistance": 5200},
        "reasoning": "Higher highs and rising volume",
    }))
    result = await technical.run(candidate, fake_client, str(db))
    assert result.role == "technical"
    assert result.status == "ok"
    assert result.output["verdict"] == "BULLISH"
    assert result.tokens_in == 1200
    assert result.tools_called[0]["tool"] == "sqlite_query"
    assert result.tools_called[0]["rows"] == 19


@pytest.mark.asyncio
async def test_technical_returns_failed_on_invalid_json(tmp_path):
    db = tmp_path / "t.db"
    _seed(db)
    candidate = SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=4.2, scan_time="2026-05-19T16:00:00+07:00",
    )
    fake_client = AsyncMock()
    fake_client.generate.return_value = _response("not valid json", tokens_in=100, tokens_out=5)
    result = await technical.run(candidate, fake_client, str(db))
    assert result.status == "failed"
    assert "json" in result.error.lower() or "decode" in result.error.lower()


@pytest.mark.asyncio
async def test_technical_returns_failed_on_client_exception(tmp_path):
    db = tmp_path / "t.db"
    _seed(db)
    candidate = SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=4.2, scan_time="2026-05-19T16:00:00+07:00",
    )
    fake_client = AsyncMock()
    fake_client.generate.side_effect = RuntimeError("network down")
    result = await technical.run(candidate, fake_client, str(db))
    assert result.status == "failed"
    assert "network down" in result.error
```

```python
# tests/agent_firm/test_risk.py — full replacement
import json
from datetime import datetime, timezone

import pytest
from unittest.mock import AsyncMock

from engine.agent_firm.agents import risk
from engine.agent_firm.providers.base import ProviderResponse
from engine.agent_firm.schemas import AgentResult, SignalCandidate


def _response(content: str, tokens_in=1500, tokens_out=90) -> ProviderResponse:
    return ProviderResponse(
        content=content, provider="zai", model="glm-5.2", runtime_version="1.0.0",
        tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=0.0007, duration_s=4.0,
        timestamp=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_risk_approve_on_bullish_input():
    candidate = SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=4.2, scan_time="2026-05-19T16:00:00+07:00",
    )
    technical = AgentResult(
        role="technical", status="ok",
        output={
            "verdict": "BULLISH", "conviction": 0.75,
            "key_levels": {"support": 5000, "resistance": 5200},
            "reasoning": "Higher highs",
        },
    )
    fake_client = AsyncMock()
    fake_client.generate.return_value = _response(json.dumps({
        "decision": "approve",
        "confidence": 0.7,
        "size_hint": 1.0,
        "rationale": "Risk: trend intact.\nBull/Bear: bull case dominates",
    }))
    result = await risk.run(candidate, [technical], fake_client)
    assert result.role == "risk"
    assert result.status == "ok"
    assert result.output["decision"] == "approve"
    assert result.output["size_hint"] == 1.0


@pytest.mark.asyncio
async def test_risk_veto_on_bearish_input():
    candidate = SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=2.5, scan_time="2026-05-19T16:00:00+07:00",
    )
    technical = AgentResult(
        role="technical", status="ok",
        output={
            "verdict": "BEARISH", "conviction": 0.8,
            "key_levels": {"support": 4800, "resistance": 5050},
            "reasoning": "Lower lows",
        },
    )
    fake_client = AsyncMock()
    fake_client.generate.return_value = _response(json.dumps({
        "decision": "veto",
        "confidence": 0.85,
        "size_hint": 0.0,
        "rationale": "Risk: clear downtrend.\nBull/Bear: bear case dominant",
    }), tokens_in=1400, tokens_out=80)
    result = await risk.run(candidate, [technical], fake_client)
    assert result.status == "ok"
    assert result.output["decision"] == "veto"


@pytest.mark.asyncio
async def test_risk_returns_failed_on_invalid_json():
    candidate = SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=4.2, scan_time="2026-05-19T16:00:00+07:00",
    )
    fake_client = AsyncMock()
    fake_client.generate.return_value = _response("garbage", tokens_in=100, tokens_out=5)
    result = await risk.run(candidate, [], fake_client)
    assert result.status == "failed"


@pytest.mark.asyncio
async def test_risk_propagates_analyst_failures_in_payload():
    candidate = SignalCandidate(
        ticker="BBRI", strategy="momentum_following",
        score=4.2, scan_time="2026-05-19T16:00:00+07:00",
    )
    failed_technical = AgentResult(role="technical", status="failed", error="network")
    captured_messages = {}

    async def capture_generate(messages, **kwargs):
        captured_messages["body"] = messages
        return _response(json.dumps({
            "decision": "approve", "confidence": 0.3, "size_hint": 0.5,
            "rationale": "Risk: analyst down, low conviction.\nBull/Bear: n/a",
        }), tokens_in=50, tokens_out=30)

    fake_client = AsyncMock()
    fake_client.generate.side_effect = capture_generate
    result = await risk.run(candidate, [failed_technical], fake_client)
    assert result.status == "ok"
    payload = captured_messages["body"][1]["content"]
    assert "failed" in payload
    assert result.output["confidence"] == 0.3
```

```python
# tests/agent_firm/test_risk_v2.py — full replacement
import json
from datetime import datetime, timezone

import pytest
from unittest.mock import AsyncMock

from engine.agent_firm.agents import risk
from engine.agent_firm.providers.base import ProviderResponse
from engine.agent_firm.schemas import AgentResult, SignalCandidate


def _make_candidate(score=4.0):
    return SignalCandidate(
        ticker="BBRI", strategy="vol_weighted",
        score=score, scan_time="2026-05-20T10:00:00+07:00",
    )


def _make_all_analysts():
    return [
        AgentResult(role="technical", status="ok",
                    output={"verdict": "BULLISH", "conviction": 0.75}),
        AgentResult(role="flow", status="ok",
                    output={"flow_verdict": "ACCUMULATING", "smart_money_signal": "BUY"}),
        AgentResult(role="regime", status="ok",
                    output={"regime_call": "BULL", "sector_tailwind": True}),
        AgentResult(role="news", status="ok",
                    output={"sentiment": "BULLISH", "catalyst": "bullish"}),
        AgentResult(role="bull", status="ok",
                    output={"bull_case": "Strong case.", "key_strength": "Accumulation"}),
        AgentResult(role="bear", status="ok",
                    output={"bear_case": "Rate risk.", "key_risk": "BI surprise"}),
    ]


def _response(content: str, tokens_in=2000, tokens_out=100) -> ProviderResponse:
    return ProviderResponse(
        content=content, provider="zai", model="glm-5.2", runtime_version="1.0.0",
        tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=0.0009, duration_s=5.0,
        timestamp=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_risk_v2_approve_on_full_bullish_committee():
    fake_client = AsyncMock()
    fake_client.generate.return_value = _response(json.dumps({
        "decision": "approve", "confidence": 0.82,
        "size_hint": 1.2,
        "rationale": "Risk: all analysts aligned.\nBull/Bear: bull case dominates.",
    }))
    result = await risk.run(_make_candidate(), _make_all_analysts(), fake_client)
    assert result.status == "ok"
    assert result.output["decision"] == "approve"
    assert result.output["size_hint"] == 1.2
    assert result.tokens_in == 2000


@pytest.mark.asyncio
async def test_risk_v2_all_6_reports_in_payload():
    captured = {}

    async def capture_generate(messages, **kwargs):
        captured["body"] = messages
        return _response(json.dumps({
            "decision": "approve", "confidence": 0.6,
            "size_hint": 1.0, "rationale": "ok.\nok.",
        }), tokens_in=50, tokens_out=30)

    fake_client = AsyncMock()
    fake_client.generate.side_effect = capture_generate
    await risk.run(_make_candidate(), _make_all_analysts(), fake_client)
    payload = json.loads(captured["body"][1]["content"])
    roles = [r["role"] for r in payload["analyst_reports"]]
    assert "bull" in roles
    assert "bear" in roles
    assert len(roles) == 6
```

- [ ] **Step 2: Run all 8 test files to verify they fail**

Run: `pytest tests/agent_firm/test_bear.py tests/agent_firm/test_bull.py tests/agent_firm/test_flow.py tests/agent_firm/test_news.py tests/agent_firm/test_regime.py tests/agent_firm/test_risk.py tests/agent_firm/test_risk_v2.py tests/agent_firm/test_technical.py -v`
Expected: FAIL — `AttributeError: 'AsyncMock' object has no attribute 'generate'` won't actually trigger (AsyncMock auto-creates attributes), but assertions on `result.provider`, and the sources still calling `.chat()` on a mock that only has `.generate` configured, will fail (`resp["content"]` style access also breaks since `_response()` returns a `ProviderResponse`, not a dict, once combined with unchanged source — actual failure mode: source calls `client.chat(...)` which returns an auto-generated `AsyncMock`, then `resp["content"]` raises `TypeError: 'AsyncMock' object is not subscriptable` inside the `try/except`, so `result.status == "failed"` unexpectedly for the "ok" tests)

- [ ] **Step 3: Update all 7 source files**

```python
# engine/agent_firm/agents/bear.py — full replacement
"""Bear Researcher agent. Steelmans the bear case from analyst + bull outputs."""

import json
import time
from pathlib import Path

from ..providers.base import FirmLLMProvider
from ..schemas import AgentResult, SignalCandidate

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "bear_v1.md"
PROMPT_VERSION = "v1"


async def run(
    candidate: SignalCandidate,
    analyst_results: list[AgentResult],
    bull_result: AgentResult,
    client: FirmLLMProvider,
) -> AgentResult:
    start = time.monotonic()
    try:
        user_msg = json.dumps({
            "candidate": candidate.model_dump(),
            "analyst_reports": [
                {"role": r.role, "status": r.status, "output": r.output, "error": r.error}
                for r in analyst_results
            ],
            "bull_case": {"status": bull_result.status, "output": bull_result.output},
        })
        resp = await client.generate([
            {"role": "system", "content": _PROMPT_PATH.read_text()},
            {"role": "user", "content": user_msg},
        ])
        try:
            output = json.loads(resp.content)
        except json.JSONDecodeError as e:
            raise ValueError(f"json decode error: {e}") from e
        return AgentResult(
            role="bear", status="ok", output=output,
            prompt_version=PROMPT_VERSION,
            tokens_in=resp.tokens_in, tokens_out=resp.tokens_out,
            cost_usd=resp.cost_usd, duration_s=resp.duration_s,
            provider=resp.provider, model=resp.model,
            runtime_version=resp.runtime_version, failover=resp.failover,
        )
    except Exception as err:
        return AgentResult(
            role="bear", status="failed",
            prompt_version=PROMPT_VERSION,
            error=str(err),
            duration_s=time.monotonic() - start,
        )
```

```python
# engine/agent_firm/agents/bull.py — full replacement
"""Bull Researcher agent. Steelmans the bull case from all analyst outputs."""

import json
import time
from pathlib import Path

from ..providers.base import FirmLLMProvider
from ..schemas import AgentResult, SignalCandidate

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "bull_v1.md"
PROMPT_VERSION = "v1"


async def run(
    candidate: SignalCandidate,
    analyst_results: list[AgentResult],
    client: FirmLLMProvider,
) -> AgentResult:
    start = time.monotonic()
    try:
        user_msg = json.dumps({
            "candidate": candidate.model_dump(),
            "analyst_reports": [
                {"role": r.role, "status": r.status, "output": r.output, "error": r.error}
                for r in analyst_results
            ],
        })
        resp = await client.generate([
            {"role": "system", "content": _PROMPT_PATH.read_text()},
            {"role": "user", "content": user_msg},
        ])
        try:
            output = json.loads(resp.content)
        except json.JSONDecodeError as e:
            raise ValueError(f"json decode error: {e}") from e
        return AgentResult(
            role="bull", status="ok", output=output,
            prompt_version=PROMPT_VERSION,
            tokens_in=resp.tokens_in, tokens_out=resp.tokens_out,
            cost_usd=resp.cost_usd, duration_s=resp.duration_s,
            provider=resp.provider, model=resp.model,
            runtime_version=resp.runtime_version, failover=resp.failover,
        )
    except Exception as err:
        return AgentResult(
            role="bull", status="failed",
            prompt_version=PROMPT_VERSION,
            error=str(err),
            duration_s=time.monotonic() - start,
        )
```

```python
# engine/agent_firm/agents/flow.py — full replacement
"""Flow Specialist agent. Reads Stockbit and broker flow, returns smart-money verdict."""

import json
import time
from pathlib import Path
from typing import Any

from ..providers.base import FirmLLMProvider
from ..schemas import AgentResult, SignalCandidate

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "flow_v1.md"
PROMPT_VERSION = "v1"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text()


async def run(
    candidate: SignalCandidate,
    client: FirmLLMProvider,
    context: dict[str, Any],
) -> AgentResult:
    start = time.monotonic()
    try:
        user_msg = json.dumps({
            "candidate": candidate.model_dump(),
            "stockbit_flow_14d": context.get("stockbit_flow", []),
            "broker_flow_14d": context.get("broker_flow", []),
            "stockbit_flow_bars_7d": context.get("stockbit_flow_bars", []),
        })
        resp = await client.generate([
            {"role": "system", "content": _load_prompt()},
            {"role": "user", "content": user_msg},
        ])
        try:
            output = json.loads(resp.content)
        except json.JSONDecodeError as e:
            raise ValueError(f"json decode error: {e}") from e
        return AgentResult(
            role="flow",
            status="ok",
            output=output,
            prompt_version=PROMPT_VERSION,
            tokens_in=resp.tokens_in,
            tokens_out=resp.tokens_out,
            cost_usd=resp.cost_usd, duration_s=resp.duration_s,
            provider=resp.provider, model=resp.model,
            runtime_version=resp.runtime_version, failover=resp.failover,
        )
    except Exception as err:
        return AgentResult(
            role="flow",
            status="failed",
            prompt_version=PROMPT_VERSION,
            error=str(err),
            duration_s=time.monotonic() - start,
        )
```

```python
# engine/agent_firm/agents/news.py — full replacement
"""News/Sentiment agent. Reads news_mentions + optional Tavily web search."""

import json
import time
from pathlib import Path
from typing import Any

from ..providers.base import FirmLLMProvider
from ..schemas import AgentResult, SignalCandidate
from ..tools import web_search as _web_search

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "news_v1.md"
PROMPT_VERSION = "v1"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text()


async def run(
    candidate: SignalCandidate,
    client: FirmLLMProvider,
    context: dict[str, Any],
) -> AgentResult:
    start = time.monotonic()
    tools_called: list[dict] = []
    try:
        tavily_results = await _web_search.search(
            f"{candidate.ticker} IDX saham berita terbaru site:idx.co.id OR site:bisnis.com OR site:kontan.co.id"
        )
        tools_called.append({"tool": "tavily_search", "results": len(tavily_results)})
        user_msg = json.dumps({
            "candidate": candidate.model_dump(),
            "news_mentions_7d": context.get("news_mentions", []),
            "web_search_results": tavily_results,
        })
        resp = await client.generate([
            {"role": "system", "content": _load_prompt()},
            {"role": "user", "content": user_msg},
        ])
        try:
            output = json.loads(resp.content)
        except json.JSONDecodeError as e:
            raise ValueError(f"json decode error: {e}") from e
        return AgentResult(
            role="news",
            status="ok",
            output=output,
            prompt_version=PROMPT_VERSION,
            tokens_in=resp.tokens_in,
            tokens_out=resp.tokens_out,
            cost_usd=resp.cost_usd, duration_s=resp.duration_s,
            provider=resp.provider, model=resp.model,
            runtime_version=resp.runtime_version, failover=resp.failover,
            tools_called=tools_called,
        )
    except Exception as err:
        return AgentResult(
            role="news",
            status="failed",
            prompt_version=PROMPT_VERSION,
            error=str(err),
            duration_s=time.monotonic() - start,
            tools_called=tools_called,
        )
```

```python
# engine/agent_firm/agents/regime.py — full replacement
"""Regime Analyst agent. Reads WF scores and daily screen data."""

import json
import time
from pathlib import Path
from typing import Any

from ..providers.base import FirmLLMProvider
from ..schemas import AgentResult, SignalCandidate

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "regime_v1.md"
PROMPT_VERSION = "v1"


async def run(
    candidate: SignalCandidate,
    client: FirmLLMProvider,
    context: dict[str, Any],
) -> AgentResult:
    start = time.monotonic()
    try:
        user_msg = json.dumps({
            "candidate": candidate.model_dump(),
            "wf_scores": context.get("wf_scores", []),
            "sector_data_10d": context.get("sector_data", []),
        })
        resp = await client.generate([
            {"role": "system", "content": _PROMPT_PATH.read_text()},
            {"role": "user", "content": user_msg},
        ])
        try:
            output = json.loads(resp.content)
        except json.JSONDecodeError as e:
            raise ValueError(f"json decode error: {e}") from e
        return AgentResult(
            role="regime", status="ok", output=output,
            prompt_version=PROMPT_VERSION,
            tokens_in=resp.tokens_in, tokens_out=resp.tokens_out,
            cost_usd=resp.cost_usd, duration_s=resp.duration_s,
            provider=resp.provider, model=resp.model,
            runtime_version=resp.runtime_version, failover=resp.failover,
        )
    except Exception as err:
        return AgentResult(
            role="regime", status="failed",
            prompt_version=PROMPT_VERSION,
            error=str(err),
            duration_s=time.monotonic() - start,
        )
```

```python
# engine/agent_firm/agents/risk.py — full replacement
"""Risk Manager agent. Final approve/veto decision."""

import json
import time
from pathlib import Path

from ..guardrails import normalize_quant
from ..providers.base import FirmLLMProvider
from ..schemas import AgentResult, SignalCandidate

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "risk_v2.md"
PROMPT_VERSION = "v2"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text()


async def run(
    candidate: SignalCandidate,
    analyst_results: list[AgentResult],
    client: FirmLLMProvider,
) -> AgentResult:
    start = time.monotonic()
    try:
        cand = candidate.model_dump()
        # quant_score normalized to 0-1 so the prompt's gate is scale-consistent
        # across callers (flow -5..+5, premarket/eod 0-100). Raw stays as `score`.
        cand["quant_score"] = round(normalize_quant(cand.get("score"), candidate.strategy), 3)
        user_msg = json.dumps({
            "candidate": cand,
            "analyst_reports": [
                {"role": r.role, "status": r.status, "output": r.output, "error": r.error}
                for r in analyst_results
            ],
        })
        resp = await client.generate([
            {"role": "system", "content": _load_prompt()},
            {"role": "user", "content": user_msg},
        ])
        try:
            output = json.loads(resp.content)
        except json.JSONDecodeError as json_err:
            raise ValueError(f"json decode error: {json_err}") from json_err
        return AgentResult(
            role="risk",
            status="ok",
            output=output,
            prompt_version=PROMPT_VERSION,
            tokens_in=resp.tokens_in,
            tokens_out=resp.tokens_out,
            cost_usd=resp.cost_usd, duration_s=resp.duration_s,
            provider=resp.provider, model=resp.model,
            runtime_version=resp.runtime_version, failover=resp.failover,
        )
    except Exception as err:
        return AgentResult(
            role="risk",
            status="failed",
            prompt_version=PROMPT_VERSION,
            error=str(err),
            duration_s=time.monotonic() - start,
        )
```

```python
# engine/agent_firm/agents/technical.py — full replacement
"""Technical Analyst agent. Reads OHLCV, returns technical conviction call."""

import json
import time
from pathlib import Path

from ..providers.base import FirmLLMProvider
from ..schemas import AgentResult, SignalCandidate
from ..tools.sqlite_query import query

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "technical_v1.md"
PROMPT_VERSION = "v1"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text()


async def run(
    candidate: SignalCandidate,
    client: FirmLLMProvider,
    db_path: str,
) -> AgentResult:
    start = time.monotonic()
    tools_called: list[dict] = []
    try:
        ohlcv = query(
            db_path,
            "SELECT date, open, high, low, close, volume FROM ohlcv "
            "WHERE ticker = ? ORDER BY date DESC LIMIT 60",
            (candidate.ticker,),
        )
        tools_called.append({"tool": "sqlite_query", "rows": len(ohlcv)})
        user_msg = json.dumps({
            "candidate": candidate.model_dump(),
            "ohlcv_recent_60d": ohlcv,
        })
        resp = await client.generate([
            {"role": "system", "content": _load_prompt()},
            {"role": "user", "content": user_msg},
        ])
        try:
            output = json.loads(resp.content)
        except json.JSONDecodeError as json_err:
            raise ValueError(f"json decode error: {json_err}") from json_err
        return AgentResult(
            role="technical",
            status="ok",
            output=output,
            prompt_version=PROMPT_VERSION,
            tokens_in=resp.tokens_in,
            tokens_out=resp.tokens_out,
            cost_usd=resp.cost_usd, duration_s=resp.duration_s,
            provider=resp.provider, model=resp.model,
            runtime_version=resp.runtime_version, failover=resp.failover,
            tools_called=tools_called,
        )
    except Exception as err:
        return AgentResult(
            role="technical",
            status="failed",
            prompt_version=PROMPT_VERSION,
            error=str(err),
            duration_s=time.monotonic() - start,
            tools_called=tools_called,
        )
```

- [ ] **Step 4: Run all 8 test files to verify they pass**

Run: `pytest tests/agent_firm/test_bear.py tests/agent_firm/test_bull.py tests/agent_firm/test_flow.py tests/agent_firm/test_news.py tests/agent_firm/test_regime.py tests/agent_firm/test_risk.py tests/agent_firm/test_risk_v2.py tests/agent_firm/test_technical.py -v`
Expected: PASS (all tests across all 8 files)

- [ ] **Step 5: Commit**

```bash
git add engine/agent_firm/agents/bear.py engine/agent_firm/agents/bull.py \
        engine/agent_firm/agents/flow.py engine/agent_firm/agents/news.py \
        engine/agent_firm/agents/regime.py engine/agent_firm/agents/risk.py \
        engine/agent_firm/agents/technical.py \
        tests/agent_firm/test_bear.py tests/agent_firm/test_bull.py \
        tests/agent_firm/test_flow.py tests/agent_firm/test_news.py \
        tests/agent_firm/test_regime.py tests/agent_firm/test_risk.py \
        tests/agent_firm/test_risk_v2.py tests/agent_firm/test_technical.py
git commit -m "refactor(firm): rename client.chat() to client.generate() across all 7 agent modules"
```

---

### Task 15: Wire `firm.py` to the new provider abstraction

**Files:**
- Modify: `engine/agent_firm/firm.py`

- [ ] **Step 1: Update imports and default client construction**

```python
# engine/agent_firm/firm.py — top of file
"""Agent firm orchestrator. Phase 2: LangGraph DAG, 7 agents.

Public API:
  evaluate(candidates) -> list[AgentDecision]            # sync, full pipeline
  evaluate_staged(candidates) -> list[AgentDecision]     # sync, 2-stage pre-scan (Phase 3)
  evaluate_async(candidates, client) -> ...              # async, for tests
  reset_market_ctx() -> None                             # call at scan start to flush cache
"""

import asyncio
import json
import time

from langgraph.graph import END, StateGraph

from . import config
from .agents import bear, bull, flow, news, regime, risk, technical
from .guardrails import apply_guardrails
from .providers.base import FirmLLMProvider
from .providers.factory import build_router
from .schemas import AgentDecision, AgentResult, AgentState, SignalCandidate
from .tools import news_lookup
from .tools.sqlite_query import query
```

(remove the old `from .client import DeepSeekClient` line entirely)

- [ ] **Step 2: Update `_run_risk`'s cost/provider rollup**

Replace:
```python
    traces = [
        state["technical_result"], state["flow_result"],
        state["regime_result"], state["news_result"],
        state["bull_result"], state["bear_result"], result,
    ]
    tokens_in = sum(t.tokens_in for t in traces)
    tokens_out = sum(t.tokens_out for t in traces)
    cost_usd = DeepSeekClient._calc_cost(tokens_in, tokens_out)
    candidate = state["candidate"]

    decision = AgentDecision(
        ticker=candidate.ticker,
        strategy=candidate.strategy,
        scan_time=candidate.scan_time,
        quant_score=candidate.score,
        decision=decision_str,
        confidence=confidence,
        size_hint=size_hint,
        rationale=rationale,
        traces=traces,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=cost_usd,
        duration_s=0.0,
    )
    return {"risk_result": result, "decision": decision}
```

with:
```python
    traces = [
        state["technical_result"], state["flow_result"],
        state["regime_result"], state["news_result"],
        state["bull_result"], state["bear_result"], result,
    ]
    tokens_in = sum(t.tokens_in for t in traces)
    tokens_out = sum(t.tokens_out for t in traces)
    cost_usd = sum(t.cost_usd for t in traces)
    providers_used = sorted({t.provider for t in traces if t.provider})
    candidate = state["candidate"]

    decision = AgentDecision(
        ticker=candidate.ticker,
        strategy=candidate.strategy,
        scan_time=candidate.scan_time,
        quant_score=candidate.score,
        decision=decision_str,
        confidence=confidence,
        size_hint=size_hint,
        rationale=rationale,
        traces=traces,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=cost_usd,
        duration_s=0.0,
        providers_used=providers_used,
    )
    return {"risk_result": result, "decision": decision}
```

(This is the important correctness fix noted in the plan header: summing each trace's own `cost_usd` — 0.0 for Claude, real for Z.ai — instead of re-deriving a single decision-level cost from `DeepSeekClient._calc_cost(sum(tokens))`, which would have mispriced any batch mixing providers.)

- [ ] **Step 3: Update the stage-1 veto path in `evaluate_staged_async`**

Replace:
```python
    for candidate, (tech_r, reg_r) in zip(candidates, stage1_pairs):
        if _is_both_bearish(tech_r, reg_r):
            tokens_in = tech_r.tokens_in + reg_r.tokens_in
            tokens_out = tech_r.tokens_out + reg_r.tokens_out
            decision = AgentDecision(
                ticker=candidate.ticker,
                strategy=candidate.strategy,
                scan_time=candidate.scan_time,
                quant_score=candidate.score,
                decision="veto",
                rationale="Stage 1 pre-screen: technical BEARISH + regime BEAR",
                traces=[tech_r, reg_r],
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd=DeepSeekClient._calc_cost(tokens_in, tokens_out),
                duration_s=0.0,
            )
            vetoed.append(decision)
            _persist(decision)
        else:
            stage2_candidates.append(candidate)
```

with:
```python
    for candidate, (tech_r, reg_r) in zip(candidates, stage1_pairs):
        if _is_both_bearish(tech_r, reg_r):
            tokens_in = tech_r.tokens_in + reg_r.tokens_in
            tokens_out = tech_r.tokens_out + reg_r.tokens_out
            cost_usd = tech_r.cost_usd + reg_r.cost_usd
            providers_used = sorted({p for p in (tech_r.provider, reg_r.provider) if p})
            decision = AgentDecision(
                ticker=candidate.ticker,
                strategy=candidate.strategy,
                scan_time=candidate.scan_time,
                quant_score=candidate.score,
                decision="veto",
                rationale="Stage 1 pre-screen: technical BEARISH + regime BEAR",
                traces=[tech_r, reg_r],
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd=cost_usd,
                duration_s=0.0,
                providers_used=providers_used,
            )
            vetoed.append(decision)
            _persist(decision)
        else:
            stage2_candidates.append(candidate)
```

- [ ] **Step 4: Update the 4 public API function signatures**

Change every occurrence of `client: DeepSeekClient | None = None` to `client: FirmLLMProvider | None = None`, and every `if client is None: client = DeepSeekClient()` to `if client is None: client = build_router()`. There are two such pairs — in `evaluate_async` and in `evaluate_staged_async`:

```python
async def evaluate_async(
    candidates: list[SignalCandidate],
    client: FirmLLMProvider | None = None,
) -> list[AgentDecision]:
    if client is None:
        client = build_router()
    ...
```

```python
async def evaluate_staged_async(
    candidates: list[SignalCandidate],
    client: FirmLLMProvider | None = None,
) -> list[AgentDecision]:
    """..."""
    if client is None:
        client = build_router()
    ...
```

`evaluate()` and `evaluate_staged()` (the sync wrappers) already just forward `client` through unchanged — update their type hints too (`client: FirmLLMProvider | None = None`) but no logic change.

- [ ] **Step 5: Update `_persist()` to write the new columns**

```python
def _persist(decision: AgentDecision) -> int:
    import data.db as _db
    conn = _db.get_db()
    try:
        cur = conn.execute(
            "INSERT OR REPLACE INTO agent_decisions "
            "(scan_time, ticker, strategy, quant_score, decision, confidence, "
            "size_hint, rationale, tokens_in, tokens_out, cost_usd, duration_s, providers_used) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                decision.scan_time, decision.ticker, decision.strategy,
                decision.quant_score, decision.decision, decision.confidence,
                decision.size_hint, decision.rationale,
                decision.tokens_in, decision.tokens_out, decision.cost_usd,
                decision.duration_s, json.dumps(decision.providers_used),
            ),
        )
        decision_id = cur.lastrowid
        for trace in decision.traces:
            conn.execute(
                "INSERT INTO agent_traces "
                "(decision_id, role, prompt_version, output, tools_called, "
                "tokens_in, tokens_out, duration_s, provider, model, "
                "runtime_version, failover, error) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    decision_id, trace.role, trace.prompt_version,
                    None if trace.output is None else json.dumps(trace.output),
                    json.dumps(trace.tools_called),
                    trace.tokens_in, trace.tokens_out, trace.duration_s,
                    trace.provider, trace.model, trace.runtime_version,
                    int(trace.failover), trace.error,
                ),
            )
        conn.commit()
        return decision_id
    finally:
        conn.close()
```

- [ ] **Step 6: Run the full agent_firm test suite**

Run: `pytest tests/agent_firm/ -v`
Expected: PASS — all tests across the whole `tests/agent_firm/` tree (this is the first point where everything touched by Tasks 1–15 is exercised together)

- [ ] **Step 7: Commit**

```bash
git add engine/agent_firm/firm.py
git commit -m "feat(firm): wire firm.py to ProviderFactory/Router — per-trace cost/provider rollup, no more DeepSeekClient"
```

---

### Task 16: Provider metrics (query-based, from `agent_traces` + `provider_events`)

**Files:**
- Create: `engine/agent_firm/providers/metrics.py`
- Test: `tests/agent_firm/providers/test_metrics.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/agent_firm/providers/test_metrics.py
import sqlite3

from engine.agent_firm.providers.metrics import provider_stats


def _seed_traces(db_path, rows):
    conn = sqlite3.connect(db_path)
    for provider, duration_s, error, created_at in rows:
        conn.execute(
            "INSERT INTO agent_traces (role, provider, duration_s, error, created_at) "
            "VALUES ('technical', ?, ?, ?, ?)",
            (provider, duration_s, error, created_at),
        )
    conn.commit()
    conn.close()


def test_provider_stats_basic_rates(tmp_db):
    _seed_traces(tmp_db, [
        ("claude", 1.0, None, "2026-07-08 09:00:00"),
        ("claude", 2.0, None, "2026-07-08 09:01:00"),
        ("claude", 3.0, "claude CLI timed out after 75s", "2026-07-08 09:02:00"),
        ("claude", 4.0, "some other failure", "2026-07-08 09:03:00"),
    ])
    stats = provider_stats(str(tmp_db), "claude", since="2026-07-08 00:00:00")
    assert stats.calls == 4
    assert stats.failures == 2
    assert stats.timeouts == 1
    assert stats.success_rate == 0.5
    assert stats.failure_rate == 0.5
    assert stats.timeout_rate == 0.25
    assert stats.avg_latency_s == 2.5


def test_provider_stats_empty_defaults_to_healthy():
    import tempfile
    from data.db import init_agent_firm_tables
    import os
    db_path = tempfile.mktemp(suffix=".db")
    os.environ["DB_PATH"] = db_path
    import importlib
    from data import db as data_db
    importlib.reload(data_db)
    init_agent_firm_tables()
    stats = provider_stats(db_path, "claude", since="2026-07-08 00:00:00")
    assert stats.calls == 0
    assert stats.success_rate == 1.0
    assert stats.failure_rate == 0.0
    assert stats.circuit_state == "CLOSED"


def test_provider_stats_circuit_state_from_latest_event(tmp_db):
    conn = sqlite3.connect(tmp_db)
    conn.execute(
        "INSERT INTO provider_events (event_type, provider, created_at) "
        "VALUES ('provider_circuit_open', 'claude', '2026-07-08 09:00:00')"
    )
    conn.commit()
    conn.close()
    stats = provider_stats(str(tmp_db), "claude", since="2026-07-08 00:00:00")
    assert stats.circuit_state == "OPEN"


def test_provider_stats_zai_includes_cost_and_tokens(tmp_db):
    conn = sqlite3.connect(tmp_db)
    conn.execute(
        "INSERT INTO agent_traces (role, provider, duration_s, cost_usd, tokens_in, "
        "tokens_out, created_at) VALUES ('technical', 'zai', 1.0, 0.001, 100, 50, "
        "'2026-07-08 09:00:00')"
    )
    conn.commit()
    conn.close()
    stats = provider_stats(str(tmp_db), "zai", since="2026-07-08 00:00:00")
    assert stats.cost_usd == 0.001
    assert stats.tokens_in == 100
    assert stats.tokens_out == 50


def test_provider_stats_claude_cost_is_none(tmp_db):
    _seed_traces(tmp_db, [("claude", 1.0, None, "2026-07-08 09:00:00")])
    stats = provider_stats(str(tmp_db), "claude", since="2026-07-08 00:00:00")
    assert stats.cost_usd is None
```

Note: this test file uses the `tmp_db` fixture from `tests/agent_firm/conftest.py` — copy `tests/agent_firm/providers/conftest.py` re-exporting it, or move `test_metrics.py` under `tests/agent_firm/` directly instead of `tests/agent_firm/providers/` if fixture resolution across the subdirectory doesn't pick it up automatically (pytest fixtures defined in a parent directory's `conftest.py` ARE visible to child directories by default, so `tests/agent_firm/providers/test_metrics.py` should already see `tests/agent_firm/conftest.py`'s `tmp_db` fixture with no extra file needed — verify this in Step 2).

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/agent_firm/providers/test_metrics.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'engine.agent_firm.providers.metrics'`

- [ ] **Step 3: Write `metrics.py`**

```python
# engine/agent_firm/providers/metrics.py
"""Query-based provider health/ops metrics, computed from agent_traces +
provider_events (design doc §12). No live metrics infra (Prometheus/StatsD)
— same report-time-query pattern as engine/health_report.py."""

import datetime
import statistics
from typing import Literal, Optional

from pydantic import BaseModel

from ..tools.sqlite_query import query


class ProviderStats(BaseModel):
    calls: int
    failures: int
    timeouts: int
    daily_calls: int
    success_rate: float
    failure_rate: float
    timeout_rate: float
    failover_rate: float
    avg_latency_s: float
    p50_latency_s: float
    p95_latency_s: float
    circuit_state: Literal["CLOSED", "OPEN", "HALF_OPEN"]
    cost_usd: Optional[float] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None


def _percentile(sorted_vals: list[float], pct: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = min(len(sorted_vals) - 1, int(len(sorted_vals) * pct))
    return sorted_vals[idx]


def provider_stats(db_path: str, provider: str, since: str) -> ProviderStats:
    rows = query(
        db_path,
        "SELECT duration_s, error, cost_usd, tokens_in, tokens_out FROM agent_traces "
        "WHERE provider = ? AND created_at >= ?",
        (provider, since),
    )
    calls = len(rows)
    failures = sum(1 for r in rows if r["error"] is not None)
    timeouts = sum(1 for r in rows if r["error"] and "timed out" in r["error"].lower())
    durations = sorted(float(r["duration_s"] or 0.0) for r in rows)

    today = datetime.date.today().isoformat()
    daily_rows = query(
        db_path,
        "SELECT COUNT(*) AS c FROM agent_traces WHERE provider = ? AND DATE(created_at) = ?",
        (provider, today),
    )
    daily_calls = int(daily_rows[0]["c"]) if daily_rows else 0

    failover_rows = query(
        db_path,
        "SELECT COUNT(*) AS c FROM provider_events "
        "WHERE provider = ? AND event_type = 'provider_failover' AND created_at >= ?",
        (provider, since),
    )
    failovers = int(failover_rows[0]["c"]) if failover_rows else 0

    circuit_rows = query(
        db_path,
        "SELECT event_type FROM provider_events WHERE provider = ? "
        "AND event_type IN ('provider_circuit_open', 'provider_circuit_closed') "
        "ORDER BY created_at DESC LIMIT 1",
        (provider,),
    )
    circuit_state = "CLOSED"
    if circuit_rows and circuit_rows[0]["event_type"] == "provider_circuit_open":
        circuit_state = "OPEN"

    is_zai = provider == "zai"
    cost_usd = sum(float(r["cost_usd"] or 0.0) for r in rows) if is_zai else None
    tokens_in = sum(int(r["tokens_in"] or 0) for r in rows) if is_zai else None
    tokens_out = sum(int(r["tokens_out"] or 0) for r in rows) if is_zai else None

    return ProviderStats(
        calls=calls,
        failures=failures,
        timeouts=timeouts,
        daily_calls=daily_calls,
        success_rate=(calls - failures) / calls if calls else 1.0,
        failure_rate=failures / calls if calls else 0.0,
        timeout_rate=timeouts / calls if calls else 0.0,
        failover_rate=failovers / calls if calls else 0.0,
        avg_latency_s=statistics.fmean(durations) if durations else 0.0,
        p50_latency_s=_percentile(durations, 0.50),
        p95_latency_s=_percentile(durations, 0.95),
        circuit_state=circuit_state,
        cost_usd=cost_usd, tokens_in=tokens_in, tokens_out=tokens_out,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/agent_firm/providers/test_metrics.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add engine/agent_firm/providers/metrics.py tests/agent_firm/providers/test_metrics.py
git commit -m "feat(firm): add query-based provider_stats() metrics"
```

---

### Task 17: Telegram — `engine/trade_plan.py` provider-line support

**Files:**
- Modify: `engine/trade_plan.py`
- Test: `tests/test_trade_plan.py` (create if it doesn't already exist — check first with `find tests -iname "*trade_plan*"`; if a file exists, append to it and match its existing style)

- [ ] **Step 1: Write the failing tests**

```python
# add to (or create) tests/test_trade_plan.py
from engine.trade_plan import build_message, provider_line


class _FakeDecision:
    def __init__(self, decision, providers_used):
        self.decision = decision
        self.providers_used = providers_used


def test_provider_line_all_claude():
    decisions = [_FakeDecision("approve", ["claude"]), _FakeDecision("veto", ["claude"])]
    assert provider_line(decisions) == "Firm Provider:\nClaude"


def test_provider_line_all_zai():
    decisions = [_FakeDecision("approve", ["zai"])]
    assert provider_line(decisions) == "Firm Provider:\nZ.ai"


def test_provider_line_mixed_is_failover():
    decisions = [_FakeDecision("approve", ["claude"]), _FakeDecision("approve", ["zai"])]
    assert provider_line(decisions) == "Firm Provider:\nClaude → Z.ai (Auto Failover)"


def test_provider_line_empty_returns_none():
    assert provider_line([]) is None
    assert provider_line([_FakeDecision("bypassed", [])]) is None


def test_build_message_appends_provider_line_when_given():
    msg = build_message([], ("BULL", 70.0), "08/07", degraded=False,
                        provider_line="Firm Provider:\nClaude")
    assert msg.endswith("Firm Provider:\nClaude")


def test_build_message_omits_provider_line_when_none():
    msg = build_message([], ("BULL", 70.0), "08/07", degraded=False, provider_line=None)
    assert "Firm Provider" not in msg
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_trade_plan.py -v`
Expected: FAIL — `ImportError: cannot import name 'provider_line'`, and `build_message()` raises `TypeError: unexpected keyword argument 'provider_line'`

- [ ] **Step 3: Add `provider_line()` and the `build_message()` parameter**

Add this function anywhere in `engine/trade_plan.py` (e.g. just above `build_message`):

```python
def provider_line(decisions: list) -> Optional[str]:
    """Firm-provider summary line for the Telegram footer, derived from the
    batch's AgentDecision.providers_used. Duck-typed (no agent_firm import)
    to preserve this module's lean-venv, LLM-import-free contract. None
    when the firm didn't actually run — callers should pass provider_line=
    None for degraded/bypassed batches rather than calling this at all."""
    used: set[str] = set()
    for d in decisions:
        used.update(getattr(d, "providers_used", None) or [])
    if not used:
        return None
    if used == {"claude"}:
        return "Firm Provider:\nClaude"
    if used == {"zai"}:
        return "Firm Provider:\nZ.ai"
    if "claude" in used and "zai" in used:
        return "Firm Provider:\nClaude → Z.ai (Auto Failover)"
    return "Firm Provider:\n" + ", ".join(sorted(used))
```

Update `build_message`'s signature and both return points:

```python
def build_message(ranked: list[dict[str, Any]],
                  regime: tuple[str, Optional[float]],
                  date_str: str,
                  degraded: bool = False,
                  vpin_summary: Optional[dict] = None,
                  provider_line: Optional[str] = None) -> str:
    """..."""
    ...
    if not ranked:
        L.append("No firm-approved long setups today.")
        L.append("")
        L.append("<i>broker_flow/VPIN settle ~20:15; flow on last settled day.</i>")
        if provider_line:
            L.append("")
            L.append(provider_line)
        return "\n".join(L)

    L.append("<b>🏆 TOP LONGS</b>")
    for i, c in enumerate(ranked, 1):
        ...
    L.append("")
    L.append("<i>R=reversal S=screen V=volume P=premarket · "
             "broker_flow/VPIN settle ~20:15.</i>")
    if provider_line:
        L.append("")
        L.append(provider_line)
    return "\n".join(L)
```

(The parameter name `provider_line` shadows the module-level function name inside `build_message`'s own scope — that's fine, they're never both needed in the same scope at once, but rename the parameter to `provider_line_text` if this trips a linter; functionally harmless either way since Python resolves the local parameter first.)

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_trade_plan.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add engine/trade_plan.py tests/test_trade_plan.py
git commit -m "feat(firm): add Firm Provider line to EOD trade plan Telegram message"
```

---

### Task 18: Telegram — `scheduler/jobs.py` wiring (premarket scan + EOD trade plan)

**Files:**
- Modify: `scheduler/jobs.py`
- Test: `tests/test_premarket_firm_scan.py` (existing — extend it)

- [ ] **Step 1: Write the failing test**

Check `tests/test_premarket_firm_scan.py` first for its existing style around `_build_premarket_firm_message`, then append (matching its fixture/decision-object style):

```python
def test_premarket_message_includes_provider_line():
    class _D:
        def __init__(self, ticker, decision, confidence, providers_used):
            self.ticker = ticker
            self.decision = decision
            self.confidence = confidence
            self.rationale = None
            self.providers_used = providers_used

    from scheduler.jobs import _build_premarket_firm_message
    decisions = [_D("BBRI", "approve", 0.8, ["claude"])]
    msg = _build_premarket_firm_message(decisions, [], "08/07 08:35")
    assert "Firm Provider:\nClaude" in msg


def test_premarket_message_omits_provider_line_when_no_providers_used():
    class _D:
        def __init__(self, ticker, decision):
            self.ticker = ticker
            self.decision = decision
            self.confidence = None
            self.rationale = None
            self.providers_used = []

    from scheduler.jobs import _build_premarket_firm_message
    decisions = [_D("BBRI", "bypassed")]
    msg = _build_premarket_firm_message(decisions, [], "08/07 08:35")
    assert "Firm Provider" not in msg
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_premarket_firm_scan.py -v`
Expected: FAIL — `test_premarket_message_includes_provider_line` fails because the message doesn't yet contain "Firm Provider"

- [ ] **Step 3: Update `_build_premarket_firm_message` and `run_eod_trade_plan`**

```python
def _build_premarket_firm_message(decisions: list, rows: list, header: str) -> str:
    """Pure Telegram-message builder for the premarket firm shortlist.

    decisions: list[AgentDecision] from firm.evaluate_staged.
    rows: the unified-watchlist long rows (dicts) used for source/strength lookup.
    header: pre-formatted "dd/mm HH:MM" string.
    Kept import-free (no langgraph) so it's unit-testable on the Windows venv.
    """
    from engine import trade_plan as tp

    by_ticker = {r["ticker"]: r for r in rows}
    approved = sorted(
        [d for d in decisions if d.decision == "approve"],
        key=lambda d: d.confidence or 0.0, reverse=True,
    )
    vetoed   = [d for d in decisions if d.decision == "veto"]
    passthru = [d for d in decisions if d.decision in ("degraded", "bypassed")]

    msg = f"🌅 <b>Premarket Shortlist — {header}</b>\n"
    msg += f"<i>Unified EOD watchlist → agent firm ({len(decisions)} setups)</i>\n\n"

    if approved:
        msg += "<b>✅ Firm-approved (long):</b>\n"
        for d in approved:
            conf = f"{d.confidence:.2f}" if d.confidence is not None else "N/A"
            size = f" ×{d.size_hint:.2f}" if d.size_hint else ""
            srcs = by_ticker.get(d.ticker, {}).get("sources") or []
            tag = "+".join(s[0] for s in srcs)
            tag = f" [{tag}]" if tag else ""
            msg += f"  <b>{d.ticker}</b> conv {conf}{size}{tag}\n"
            if d.rationale:
                msg += f"     <i>{d.rationale[:140]}</i>\n"
    else:
        msg += "<b>✅ No firm-approved longs this morning</b>\n"

    if passthru:
        msg += "\n<b>➡️ Passed through (firm degraded/off):</b>\n"
        msg += "  " + ", ".join(d.ticker for d in passthru) + "\n"

    if vetoed:
        msg += f"\n<b>⛔ Vetoed ({len(vetoed)}):</b> " + ", ".join(d.ticker for d in vetoed) + "\n"

    p_line = tp.provider_line(decisions)
    if p_line:
        msg += "\n" + p_line + "\n"

    return msg
```

In `run_eod_trade_plan`, replace:
```python
    try:
        send_telegram(tp.build_message(ranked, regime, now.strftime('%d/%m'),
                                       degraded=degraded, vpin_summary=vpin_summary))
    except Exception as e:
        print(f"[eod_trade_plan] Telegram error: {e}")
```
with:
```python
    p_line = None if degraded else tp.provider_line(decisions)
    try:
        send_telegram(tp.build_message(ranked, regime, now.strftime('%d/%m'),
                                       degraded=degraded, vpin_summary=vpin_summary,
                                       provider_line=p_line))
    except Exception as e:
        print(f"[eod_trade_plan] Telegram error: {e}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_premarket_firm_scan.py -v`
Expected: PASS (all tests, including the 2 new ones)

- [ ] **Step 5: Commit**

```bash
git add scheduler/jobs.py tests/test_premarket_firm_scan.py
git commit -m "feat(firm): wire Firm Provider line into premarket + EOD Telegram messages"
```

---

### Task 19: `.env.example` update

**Files:**
- Modify: `.env.example`

- [ ] **Step 1: Update the agent-firm section**

Replace:
```
# Agent firm LLM (OpenAI-compatible endpoint — currently z.ai)
DEEPSEEK_API_KEY=your_zai_api_key_here
DEEPSEEK_BASE_URL=https://api.z.ai/api/coding/paas/v4
AGENT_FIRM_MODEL=glm-5.2
AGENT_FIRM_ENABLED=true
```

with:
```
# Agent firm LLM providers
# Z.ai (OpenAI-compatible endpoint)
ZAI_API_KEY=your_zai_api_key_here
ZAI_BASE_URL=https://api.z.ai/api/coding/paas/v4
AGENT_FIRM_MODEL=glm-5.2
AGENT_FIRM_ENABLED=true

# Provider routing (claude | zai | auto)
AGENT_FIRM_PROVIDER=zai
AGENT_FIRM_PROVIDER_ORDER=claude,zai   # only used when AGENT_FIRM_PROVIDER=auto

# Claude (via Claude Code Subscription CLI — no API key needed)
AGENT_FIRM_CLAUDE_MODEL=sonnet
AGENT_FIRM_CLAUDE_MAX_CONCURRENT=4
AGENT_FIRM_CLAUDE_MAX_CALLS_PER_DAY=200

# Circuit breaker (per provider)
AGENT_FIRM_CIRCUIT_FAILURES=3
AGENT_FIRM_CIRCUIT_COOLDOWN=30

# Timeouts (seconds) — generic defaults; AGENT_FIRM_CLAUDE_* overrides optional
AGENT_FIRM_CONNECTION_TIMEOUT=10
AGENT_FIRM_READ_TIMEOUT=60
AGENT_FIRM_OVERALL_TIMEOUT=75
```

- [ ] **Step 2: Commit**

```bash
git add .env.example
git commit -m "docs(firm): update .env.example for ZAI_* rename + provider routing config"
```

(No production `.env` change here — that's a manual, separate step the user does themselves before deploy, since it's a live credentials file. Task 20 calls this out explicitly.)

---

### Task 20: Full suite run, live Claude CLI smoke check, deploy note

**Files:** none (verification only)

- [ ] **Step 1: Run the complete test suite**

Run: `pytest -q`
Expected: PASS, 0 failures. If anything outside `engine/agent_firm/`, `scheduler/`, or `engine/trade_plan.py` fails, investigate before proceeding — it means something imported `DeepSeekClient` from outside the areas this plan touched (checked in Task 8 Step 1, but re-verify here against the full, up-to-date tree).

- [ ] **Step 2: Live smoke call — verify the real `claude -p --output-format json` shape**

Run manually (uses one real Claude Code Subscription call — not part of the automated suite):

```bash
claude -p "Respond with exactly this JSON: {\"ok\": true}" \
  --append-system-prompt "You are a test harness. Output only valid JSON, no prose." \
  --model sonnet --output-format json --disallowedTools "*" --strict-mcp-config
```

Inspect the raw output. Confirm it has top-level `result` (the text content), `session_id`, and `usage.input_tokens`/`usage.output_tokens` — the exact fields `ClaudeProvider.generate()` reads in Task 9. If any field name differs from what's assumed, update `engine/agent_firm/providers/claude.py`'s `result.get(...)`/`usage.get(...)` calls to match, re-run `pytest tests/agent_firm/providers/test_claude_provider.py -v`, and commit the fix as its own small commit (`fix(firm): correct claude CLI JSON field names per live smoke test`).

- [ ] **Step 3: Manual production `.env` migration note (do not automate — live credentials file)**

On the production host, rename the two live env vars (keeping the same value) — either edit `.env` directly or run:

```bash
grep -q '^ZAI_API_KEY=' .env || sed -i 's/^DEEPSEEK_API_KEY=/ZAI_API_KEY=/' .env
grep -q '^ZAI_BASE_URL=' .env || sed -i 's/^DEEPSEEK_BASE_URL=/ZAI_BASE_URL=/' .env
```

This is optional for correctness (Task 6's fallback-with-warning keeps `DEEPSEEK_API_KEY`/`DEEPSEEK_BASE_URL` working for one release), but should be done before that fallback is removed in a follow-up cleanup task.

- [ ] **Step 4: Confirm default behavior is unchanged pre-deploy**

With no `AGENT_FIRM_PROVIDER` env var set, `config.PROVIDER_MODE` defaults to `"zai"` (Task 6) — i.e. this refactor is a no-op for production behavior until someone explicitly sets `AGENT_FIRM_PROVIDER=claude` or `=auto`. Confirm this is still true by running:

```bash
python3 -c "
import importlib
from engine.agent_firm import config
importlib.reload(config)
assert config.PROVIDER_MODE == 'zai'
print('OK: default provider mode unchanged (zai)')
"
```

Expected output: `OK: default provider mode unchanged (zai)`
