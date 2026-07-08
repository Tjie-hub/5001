# Firm LLM Provider Abstraction — Design

Date: 2026-07-08
Status: Approved — locked, pending implementation plan

## Background

`engine/agent_firm/` (the Firm validation layer) currently has one real LLM
integration: `DeepSeekClient` in `engine/agent_firm/client.py`, an
`AsyncOpenAI` client. Despite the name, `.env` / `.env.example` show it has
already been repointed at Z.ai's OpenAI-compatible endpoint
(`https://api.z.ai/api/coding/paas/v4`, model `glm-5.2`) — "DeepSeek" is a
stale name for what is actually the Z.ai integration. True DeepSeek
(`api.deepseek.com`) is not wired to anything.

Production reality per the user:
- **Claude** — accessed via Claude Code Subscription (the `claude` CLI,
  confirmed installed at v2.1.204 and authenticated via
  `~/.claude/.credentials.json`), not the Anthropic API. No `anthropic` SDK
  or API key exists anywhere in this repo.
- **Z.ai (GLM)** — accessed via its API, today mislabeled as "DeepSeek".
- DeepSeek is not part of the production workflow.
- The app runs as a single long-lived process (systemd `Restart=always`,
  per existing ops docs) — so in-memory, per-process runtime state (the
  Circuit Breaker, §3) is sufficient; there is no multi-worker fan-out that
  would require shared/distributed breaker state.

Goal: make the Firm engine fully provider-independent, supporting Claude
and Z.ai today via an **ordered list of N providers** (not a hardcoded
pair), with a clean seam for future providers (OpenAI, Gemini, Ollama,
local vLLM, ...) that requires **zero** changes to Firm business logic —
prompts, scoring, thresholds, validation, JSON schema, LangGraph flow,
Telegram signal logic, and the research/production workflow boundary must
all remain identical. Only infrastructure changes; no behavioral
regression is allowed, and every change is additive (no destructive
migration, no breaking API, existing tests keep passing).

## Current seam (why this refactor is low-risk)

Every one of the 7 agent modules (`bear.py`, `bull.py`, `flow.py`,
`news.py`, `regime.py`, `risk.py`, `technical.py`) depends on exactly one
method: `client.chat(messages: list[dict]) -> dict`, returning
`{content, tokens_in, tokens_out, cost_usd, duration_s}`. `firm.py` already
dependency-injects this client (`client: DeepSeekClient | None = None`,
defaulting to `DeepSeekClient()` when not supplied). `AgentState.client` is
already typed as `Any`. This means swapping in a provider abstraction
touches the injection points and the 7 call sites uniformly — no LangGraph
node, prompt, or scoring logic needs to change.

## Architecture

```
Research
  → Firm Engine (firm.py, agents/*)
    → Provider Factory (providers/factory.py)    — builds from config
      → Provider Registry (providers/registry.py) — name → class
      → Provider Router (providers/router.py)     — ordered list + circuit breakers
        → FirmLLMProvider (providers/base.py — interface)
          → ClaudeProvider (providers/claude.py)
          → ZAIProvider (providers/zai.py)
          → [future: OpenAIProvider, GeminiProvider, ...]
    → Unified ProviderResponse
  → Firm Decision → Production
```

Providers never know about each other and never contain failover logic —
that's the Router's job, and the Router never constructs a provider
itself — that's the Factory's job (§5). The Firm engine never knows which
provider is active; it only ever holds an object satisfying
`FirmLLMProvider` (in practice, the Router itself, which also satisfies
the interface).

## 1. Provider interface

`engine/agent_firm/providers/base.py`, kept deliberately small:

```python
class FirmLLMProvider(Protocol):
    name: str                                   # "claude" | "zai"
    capabilities: ProviderCapabilities           # see below

    async def generate(
        self, messages: list[dict], *, timeout: TimeoutPolicy | None = None,
    ) -> ProviderResponse: ...

    async def health(self) -> bool: ...          # diagnostics only, see §2

    def model(self) -> str: ...
```

No `availability()`, no `retry()` on the interface (see §2, §4). No
provider-construction parameters (config, semaphore, logger, metrics) on
the interface either — those are injected by the Factory (§5) at
construction time, not passed per-call.

### ProviderCapabilities

Static metadata each provider declares about itself, so future providers
(e.g. a tool-less local model, or one without native JSON mode) can be
added — and the Router/Firm can make informed decisions about them — without
ever changing the `FirmLLMProvider` method signatures themselves:

```python
class ProviderCapabilities(BaseModel):
    supports_json_mode: bool        # can force valid-JSON output natively
    supports_json_schema: bool      # can enforce a specific JSON Schema
    supports_tools: bool            # can be given tool/function definitions
    max_context_tokens: int | None = None
```

`ZAIProvider.capabilities` → `supports_json_mode=True` (already sets
`response_format={"type": "json_object"}`), `supports_json_schema=False`,
`supports_tools=True` (unused by Firm today, but true of the underlying
API). `ClaudeProvider.capabilities` → `supports_json_mode=True`,
`supports_json_schema=True` (CLI's `--json-schema` flag), `supports_tools=
True` (deliberately disabled per-call via `--disallowedTools`, see §9 — a
capability being *true* doesn't mean Firm chooses to use it). Nothing in
this refactor currently branches on capabilities — they're declared now so
a future provider lacking one of them has a documented contract to satisfy
instead of requiring a `FirmLLMProvider` interface change.

### ProviderResponse

```python
class ProviderResponse(BaseModel):
    content: str
    provider: str          # "claude" | "zai" — who actually served this
    model: str
    runtime_version: str   # see §9 — e.g. claude CLI "2.1.204", openai SDK "1.x.y"
    tokens_in: int
    tokens_out: int
    cost_usd: float
    duration_s: float
    request_id: str | None = None   # Claude: session_id; Z.ai: response.id
    timestamp: datetime             # UTC, set at response time — not a
                                     # string, so callers can do time-range
                                     # math/comparisons without reparsing
    failover: bool = False          # True if this is a fallback response
                                     # after an earlier provider in the
                                     # routing order failed
```

### Exceptions

`engine/agent_firm/providers/errors.py`:

```python
class ProviderException(Exception): ...
class ProviderQuotaExceeded(ProviderException): ...
class ProviderRateLimited(ProviderException): ...
class ProviderTimeout(ProviderException): ...
class ProviderUnavailable(ProviderException): ...
```

Each provider's `generate()` catches its own SDK/subprocess-specific errors
and re-raises as one of these four. Unclassified failures default to
`ProviderUnavailable` (safe default — still triggers Router failover in
`auto` mode, and still counts as a failure against that provider's Circuit
Breaker, §3).

## 2. No availability() in the inference path

`generate()` simply attempts generation and returns a `ProviderResponse`,
or raises a `ProviderException` subclass. No pre-flight `availability()`
check before every call — that would double provider round-trips for no
benefit, since `generate()` failing *is* the availability signal (and the
Circuit Breaker, §3, already remembers recent failures so the Router
doesn't even need to attempt a call it already knows will fail).

`health()` remains on the interface for out-of-band diagnostics (e.g. a
future ops script or dashboard querying "is Claude reachable right now"),
but is never called as part of the request path. Not wired into a
scheduled job in this refactor — out of scope until there's an actual
consumer for it (YAGNI).

## 3. Circuit Breaker

One `CircuitBreaker` instance per provider, owned by the Router (assembled
by the Factory, §5), in-memory only (single-process app, per Background).
Purpose: once a provider is known to be down, stop paying its
timeout/latency cost on every single request — skip it immediately and go
straight to the next provider in the routing order, exactly as the user's
requirement states: *"the Firm Engine must never wait for a provider
already known to be unavailable."*

```python
class CircuitBreaker:
    consecutive_failures: int = 0
    last_failure: datetime | None = None
    state: Literal["CLOSED", "OPEN", "HALF_OPEN"] = "CLOSED"
```

State machine:

- **CLOSED** — normal routing; every `generate()` call is attempted.
- On failure, `consecutive_failures += 1`. Once it reaches
  `AGENT_FIRM_CIRCUIT_FAILURES`, state → **OPEN**, `last_failure` set, and
  a `provider_circuit_open` event fires (§7).
- **OPEN** — the Router skips this provider without calling `generate()`
  at all and routes to the next provider in the list (a `provider_failover`
  event fires with `reason="circuit open"`). After
  `AGENT_FIRM_CIRCUIT_COOLDOWN` seconds have elapsed since `last_failure`,
  the *next* routing attempt transitions the breaker to **HALF_OPEN**
  first.
- **HALF_OPEN** — allows exactly one trial `generate()` call through.
  Guarded by an `asyncio.Lock` so that concurrent callers (this codebase
  fans out up to 7 agent calls × N candidates concurrently via
  `asyncio.gather`) don't all pile onto the trial simultaneously —
  whichever call acquires the lock first performs the trial; every other
  concurrent caller during that window is treated as still OPEN (skips
  straight to fallback). Trial **success** → state → CLOSED,
  `consecutive_failures = 0`, `provider_circuit_closed` event fires. Trial
  **failure** → state → OPEN again, `last_failure` refreshed, cooldown
  restarts.

Configuration:

```
AGENT_FIRM_CIRCUIT_FAILURES=3    # consecutive failures before OPEN
AGENT_FIRM_CIRCUIT_COOLDOWN=30   # seconds before a HALF_OPEN trial is allowed
```

One breaker per *provider name*, shared across all concurrent candidates
in a scan (not one breaker per call) — that's what makes "known
unavailable" a meaningful, remembered state rather than something
re-discovered on every request.

## 4. Provider Router

`engine/agent_firm/providers/router.py`. Owns all selection, ordering, and
failover logic; providers stay dumb; the Router does not construct
providers (that's the Factory, §5) and does not decide *which* providers
exist (that's the Registry, §4a).

Router holds an **ordered list**, not a primary/fallback pair — adding a
third provider to the routing order is a config change, never a Router
code change:

```python
class ProviderRouter:
    def __init__(self, routed: list[tuple[FirmLLMProvider, CircuitBreaker]]): ...

    async def generate(self, messages, *, timeout=None) -> ProviderResponse:
        last_err: ProviderException | None = None
        for i, (provider, breaker) in enumerate(self._routed):
            if not breaker.allow_request():          # CLOSED or HALF_OPEN trial slot
                continue
            if provider.name == "claude" and _claude_daily_cap_reached():
                log_provider_event("provider_quota_exceeded", provider=provider.name,
                                    reason="daily call cap reached")
                continue
            try:
                resp = await provider.generate(messages, timeout=timeout)
                breaker.record_success()
                resp.failover = i > 0
                if resp.failover:
                    log_provider_event("provider_failover", provider=provider.name, ...)
                return resp
            except ProviderException as err:
                breaker.record_failure()
                last_err = err
                log_provider_event("provider_failed", provider=provider.name,
                                    reason=str(err), ...)
                continue
        raise last_err or ProviderUnavailable("no providers configured")
```

Single-provider mode (`AGENT_FIRM_PROVIDER=claude` or `=zai`) is just a
routing order of length 1 — a failure propagates straight up to the
calling agent's existing try/except (each agent module already wraps its
call and returns `AgentResult(status="failed", error=...)` — this
fail-open behavior is unchanged). The Circuit Breaker still applies even
with a length-1 order: while OPEN it fails fast (raises immediately
without attempting the call); the periodic HALF_OPEN trial still probes
for recovery. There's simply nothing to fail over *to*.

`ZAIProvider` keeps its own existing internal retry-once-on-5xx (unchanged,
provider-local resilience for transient errors); that is distinct from —
and happens before — the Router's cross-provider failover.

### 4a. Provider Registry

`engine/agent_firm/providers/registry.py` holds the name → constructor
mapping. `router.py` never imports `ClaudeProvider`/`ZAIProvider`
directly — the Registry is the only place that knows concrete provider
classes exist:

```python
_PROVIDERS: dict[str, Callable[[], FirmLLMProvider]] = {}

def register(name: str):
    def deco(cls):
        _PROVIDERS[name] = cls
        return cls
    return deco

def build(name: str) -> FirmLLMProvider:
    if name not in _PROVIDERS:
        raise ValueError(f"unknown provider {name!r}; registered: {list(_PROVIDERS)}")
    return _PROVIDERS[name]()
```

`ClaudeProvider`/`ZAIProvider` self-register via `@register("claude")` /
`@register("zai")` class decorators. A future `OpenAIProvider` does the
same in its own file. `firm.py`'s existing lazy-import pattern
(`__init__.py` already avoids eager `langgraph` import) extends naturally
here: only the provider module(s) actually named in config get imported,
via the Registry's lazy `build()`.

## 5. Provider Factory

`engine/agent_firm/providers/factory.py`. The Router must never construct
a provider — the Factory is the single place that reads configuration,
resolves the routing order via the Registry, and injects every runtime
dependency each provider needs:

- reads `AGENT_FIRM_PROVIDER` / `AGENT_FIRM_PROVIDER_ORDER` (§6) and
  resolves the ordered list of provider **names**
- calls `registry.build(name)` for each to get a bare provider instance
- injects the concurrency semaphore (`AGENT_FIRM_CLAUDE_MAX_CONCURRENT`,
  Claude only — §6)
- injects the timeout policy (§8, generic + provider-specific overrides)
- injects the shared `logging.Logger` used for structured events (§7)
- injects the metrics recorder (§12) each provider calls into on
  completion
- wraps each provider with a fresh `CircuitBreaker` (§3)
- returns a fully-assembled `ProviderRouter`

```python
def build_router() -> ProviderRouter:
    ...
```

`firm.py`'s `evaluate()`/`evaluate_async()` call `factory.build_router()`
in place of today's `if client is None: client = DeepSeekClient()` — same
injection point, same call sites in the 7 agent modules, nothing else
changes. Config validation (§6) lives in the Factory, since it's the only
component that reads raw env vars.

## 6. Configuration

All env-var based, matching the existing all-`os.getenv` pattern in
`engine/agent_firm/config.py` — no new config file format introduced.

```
AGENT_FIRM_PROVIDER=auto              # claude | zai | auto   (default: zai — preserves current prod behavior)
AGENT_FIRM_PROVIDER_ORDER=claude,zai  # comma-separated, only read when PROVIDER=auto;
                                       # routing policy today is Claude -> Z.ai, but this
                                       # is an ordered list of arbitrary length, not a
                                       # primary/fallback pair — adding a 3rd provider is
                                       # a config-only change (supersedes the previous
                                       # draft's AGENT_FIRM_PRIMARY/_FALLBACK pair)

ZAI_API_KEY=...                 # was DEEPSEEK_API_KEY
ZAI_BASE_URL=...                # was DEEPSEEK_BASE_URL
AGENT_FIRM_MODEL=glm-5.2        # unchanged — Z.ai model id

AGENT_FIRM_CLAUDE_MODEL=sonnet  # claude CLI --model value
AGENT_FIRM_CLAUDE_MAX_CONCURRENT=4     # subprocess semaphore
AGENT_FIRM_CLAUDE_MAX_CALLS_PER_DAY=200

AGENT_FIRM_CIRCUIT_FAILURES=3   # see §3
AGENT_FIRM_CIRCUIT_COOLDOWN=30  # seconds, see §3

# Timeout policy — generic defaults, per-provider overrides optional (§8)
AGENT_FIRM_CONNECTION_TIMEOUT=10
AGENT_FIRM_READ_TIMEOUT=60
AGENT_FIRM_OVERALL_TIMEOUT=75          # matches today's PER_AGENT_TIMEOUT_S
AGENT_FIRM_CLAUDE_CONNECTION_TIMEOUT=  # optional override, falls back to generic
AGENT_FIRM_CLAUDE_READ_TIMEOUT=
AGENT_FIRM_CLAUDE_OVERALL_TIMEOUT=
```

**Startup validation, fail loud** (performed by the Factory, §5, when
`build_router()` is first called — matching the existing lazy-import
pattern in `__init__.py`):

1. `AGENT_FIRM_PROVIDER ∈ {claude, zai, auto}`.
2. If `auto`: `AGENT_FIRM_PROVIDER_ORDER` is non-empty, every name in it is
   registered in the Provider Registry (§4a) — so this check automatically
   covers future providers too, not just `{claude, zai}` — and **contains
   no duplicate names** (the generalization of "primary != fallback" to an
   arbitrary-length list: a provider appearing twice in the routing order
   is a config error, since retrying the same provider instance via the
   Router is meaningless — that's the Circuit Breaker's HALF_OPEN retry's
   job, not the routing order's).

Any violation raises immediately with a clear message identifying which
check failed — never silently falls back to a default provider or order.

## 7. Structured Provider Events

Every Router/Circuit-Breaker decision emits a structured event, not just a
free-text log line. `engine/agent_firm/providers/events.py`:

```python
class ProviderEvent(BaseModel):
    event_type: Literal[
        "provider_selected", "provider_failed", "provider_timeout",
        "provider_failover", "provider_circuit_open",
        "provider_circuit_closed", "provider_quota_exceeded",
    ]
    timestamp: datetime
    provider: str
    model: str | None = None
    reason: str | None = None
    duration_s: float | None = None
    request_id: str | None = None
    failover: bool = False
```

`log_provider_event(event: ProviderEvent)` writes it through the existing
`logging` module as a single JSON-serialized line (`logger.info(event.
model_dump_json())`) — machine-parseable for a future log shipper (ELK/
Grafana/etc.) without adding any new logging dependency or infra now. This
is in addition to, not instead of, the existing human-readable summary
format for the two Telegram-adjacent log lines your original spec called
out (`Provider: Claude → Z.ai\nReason: ...`) — that formatting is derived
from the same event, not a separate code path.

Circuit-breaker transition events (`provider_circuit_open`/`_closed`) and
routing-skip events (`provider_failover`, `provider_quota_exceeded`) are
also persisted to a new `provider_events` table (§11) — these are
Router-level occurrences that aren't 1:1 with a single agent LLM call, so
they don't fit naturally into the existing per-call `agent_traces` row
(which already captures `provider`/`model`/`failover`/`duration_s` for
every actual call — see §11). `provider_selected`/`provider_failed`/
`provider_timeout` are call-level and their outcome is already fully
captured by the corresponding `agent_traces` row; they're logged (for
real-time diagnostics) but not double-persisted into `provider_events`.

## 8. Timeout policy

Split into three configurable phases (§6) instead of one flat timeout,
injected by the Factory (§5) as a `TimeoutPolicy`:

```python
class TimeoutPolicy(BaseModel):
    connection_timeout: float
    read_timeout: float
    overall_timeout: float
```

**ZAIProvider** — the underlying `openai`/`httpx` client natively supports
per-phase timeouts; maps directly:
`httpx.Timeout(connect=connection_timeout, read=read_timeout, timeout=overall_timeout)`.

**ClaudeProvider** — the `claude` CLI is a subprocess, not a raw HTTP
client we control, so the three phases don't map with the same precision:
`overall_timeout` is the binding constraint, enforced via
`asyncio.wait_for(proc.communicate(), timeout=overall_timeout)` — this is
the one that actually protects the app from a hung subprocess.
`connection_timeout`/`read_timeout` are honored on a best-effort basis
(time-to-first-output vs. time-between-output-chunks, where the CLI's
`--output-format stream-json` would be needed to observe incremental
output at all; plain `--output-format json` only yields output at process
exit). Documented here explicitly rather than implying false symmetry with
`ZAIProvider`: implementation should not over-engineer partial-timeout
enforcement for a subprocess that doesn't stream by default — verify
during build whether `--output-format stream-json` is worth adopting for
that reason, or whether `overall_timeout` alone is sufficient (it is the
correctness-critical one either way).

Provider-specific overrides (`AGENT_FIRM_CLAUDE_*_TIMEOUT`) take
precedence over the generic `AGENT_FIRM_*_TIMEOUT` defaults when set,
per-provider, at Factory construction time (§5).

## 9. ClaudeProvider

`engine/agent_firm/providers/claude.py`. No SDK — shells out to the
`claude` CLI per call via `asyncio.create_subprocess_exec` (non-blocking,
compatible with the existing `asyncio.gather` fan-out in `firm.py`):

```
claude -p "<user message>" \
  --append-system-prompt "<system>" \
  --model <AGENT_FIRM_CLAUDE_MODEL> \
  --output-format json \
  --disallowedTools "*" \
  --strict-mcp-config
```

`--disallowedTools "*" --strict-mcp-config` keep each call a pure
structured-reasoning request — no file/bash/web tool use, no inherited MCP
servers (tradingview/obsidian/etc. from the interactive session) — matching
what Firm agents actually need (JSON in, JSON out).

Tokens/cost/`session_id` parsed from the CLI's JSON result. `cost_usd` is
always forced to `0.0` in the returned `ProviderResponse` (see §14 —
subscription is flat-rate, not metered per call). `runtime_version` is
captured once at provider construction (`claude --version` output, e.g.
`"2.1.204 (Claude Code)"`), cached for the process lifetime — not
re-shelled on every call. Non-zero exit / timeout / malformed output
classified into the four `ProviderException` subclasses on a best-effort
basis (pattern-matching known usage-limit / rate-limit phrasing in
stderr); anything unrecognized becomes `ProviderUnavailable`. Flag
classification is implementation-detail, verified empirically during build
(exact CLI error text isn't documented and will be confirmed with a live
smoke call).

**Concurrency guard:** `asyncio.Semaphore(AGENT_FIRM_CLAUDE_MAX_CONCURRENT)`
inside `ClaudeProvider` (injected by the Factory, §5), so it self-throttles
regardless of how many candidates/agents `firm.py` fans out concurrently —
protects the subscription from being hammered by 100+ simultaneous
subprocess spawns on a large batch. Z.ai keeps its current unbounded
concurrency.

**Daily call cap:** enforced by the Router (§4, not the provider) by
counting today's `agent_traces` rows with `provider='claude'` before
dispatching to Claude. Once `AGENT_FIRM_CLAUDE_MAX_CALLS_PER_DAY` is
reached, the Router skips Claude entirely for the rest of the day and
routes to the next provider in the order, emitting a
`provider_quota_exceeded` event (§7). In single-provider mode
(`AGENT_FIRM_PROVIDER=claude`, routing order length 1), the cap does not
block — there's nowhere else to route, matching "the production pipeline
should continue operating whenever at least one provider is available."

## 10. ZAIProvider (rename, not rewrite)

`engine/agent_firm/client.py` → `providers/zai.py`. `DeepSeekClient` →
`ZAIProvider`. Internals unchanged (same `AsyncOpenAI` call, same
retry-once-on-5xx). `chat()` renamed/aliased to satisfy `generate()`;
response now carries `provider="zai"`, `request_id` from the OpenAI
response's `id`, `runtime_version` from the installed `openai` package
(`openai.__version__` — there is no separate "GLM SDK"; Z.ai is accessed
through the standard OpenAI-compatible client, same as today), `timestamp`
at response time.

Env vars: `DEEPSEEK_API_KEY`/`DEEPSEEK_BASE_URL` → `ZAI_API_KEY`/
`ZAI_BASE_URL`. One release of fallback: if the new vars are unset but the
old ones are present, read them with a `logging.warning` startup notice;
remove the fallback in a follow-up cleanup once `.env` is confirmed
migrated. `DeepSeekClient` class name and all "DeepSeek" references in
docstrings/comments across `engine/agent_firm/` are renamed to Z.ai.
`tests/agent_firm/test_client.py` → `test_zai_provider.py`, same
assertions against the renamed class.

## 11. Persistence

All changes additive — no destructive migration, no column removal, no
breaking change to existing rows (new columns default to `NULL`/`0`,
existing readers unaffected).

`agent_traces` gets four additive columns (same migration pattern as
existing schema growth in `data/db.py`):

```sql
ALTER TABLE agent_traces ADD COLUMN provider TEXT;
ALTER TABLE agent_traces ADD COLUMN model TEXT;
ALTER TABLE agent_traces ADD COLUMN runtime_version TEXT;
ALTER TABLE agent_traces ADD COLUMN failover INTEGER DEFAULT 0;
```

`agent_decisions` gets:

```sql
ALTER TABLE agent_decisions ADD COLUMN providers_used TEXT;  -- JSON list, e.g. ["claude"] or ["claude","zai"]
```

New table for Router-level events that aren't 1:1 with a single agent call
(§7 — circuit breaker transitions, quota-triggered routing skips):

```sql
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
```

`AgentResult` (schemas.py) gains `provider: str = ""`, `model: str = ""`,
`runtime_version: str = ""`, `failover: bool = False`. `AgentDecision`
gains `providers_used: list[str] = Field(default_factory=list)`, computed
in `firm.py`'s `_run_risk` as the distinct `provider` values across that
decision's 7 traces (same place `tokens_in`/`tokens_out`/`cost_usd` are
already rolled up today).

Persisting `runtime_version` alongside `provider`/`model` lets a future
audit distinguish "the model changed" from "the CLI/SDK runtime changed"
from "the provider changed" — three independently-varying facts that would
otherwise be conflated into one.

## 12. Metrics

No new metrics infrastructure (no Prometheus/StatsD in this codebase
today, confirmed by search) — remains fully query-based from SQLite, per
call-level data in `agent_traces` and Router-level data in
`provider_events` (§11).

`engine/agent_firm/providers/metrics.py`, following the same pattern as
`engine/health_report.py`'s report-time queries — not a live/streaming
metrics system:

```python
class ProviderStats(BaseModel):
    calls: int
    failures: int
    timeouts: int
    daily_calls: int          # calls today specifically (for the cap, §9)
    success_rate: float       # (calls - failures) / calls, 1.0 if calls == 0
    failure_rate: float       # failures / calls, 0.0 if calls == 0
    timeout_rate: float       # timeouts / calls, 0.0 if calls == 0
    failover_rate: float      # failovers-out-of-this-provider / calls, from provider_events
    avg_latency_s: float
    p50_latency_s: float
    p95_latency_s: float
    circuit_state: Literal["CLOSED", "OPEN", "HALF_OPEN"]  # most recent
                                                            # provider_events transition
                                                            # for this provider, else CLOSED
    cost_usd: float | None = None    # zai only
    tokens_in: int | None = None     # zai only
    tokens_out: int | None = None    # zai only

def provider_stats(db_path: str, provider: str, since: str) -> ProviderStats: ...
```

Call-level rates (`success_rate`, `failure_rate`, `timeout_rate`,
`avg`/`p50`/`p95` latency, cost/tokens) computed from `agent_traces`;
`failover_rate` and `circuit_state` computed from `provider_events`. P50/
P95 computed in Python from the queried `duration_s` list (SQLite has no
native percentile function) — consistent with how other stats in this
codebase (e.g. WF metrics) are computed post-query rather than in SQL.
`circuit_state` here is a **reporting reconstruction** from the event log,
not the live authority — the Router's actual in-memory `CircuitBreaker`
(§3) is what governs real-time routing decisions, so a live process never
takes a DB round-trip to decide whether to skip a provider.

Available for ad-hoc use (a future ops script, or folded into an existing
report) — no new scheduled job or dashboard is being added in this
refactor unless a follow-up specifically asks for one.

## 13. Telegram

Both `scheduler/jobs.py::_build_premarket_firm_message` (08:35 premarket
scan) and the EOD trade-plan Telegram builder in `engine/trade_plan.py`
(16:40) get one appended line, derived from the union of `providers_used`
across the batch's decisions:

- All-Claude → `Firm Provider:\nClaude`
- All-Z.ai → `Firm Provider:\nZ.ai`
- Any failover present in the batch → `Firm Provider:\nClaude → Z.ai (Auto Failover)`

No other formatting or signal-logic changes to either message.

## 14. Cost accounting

- Z.ai: real per-token `cost_usd`, gated by existing `DAILY_SPEND_CAP_USD`
  (unchanged — `_spend_today()`/`_over_daily_cap()` logic in `firm.py` stays
  exactly as-is, still summing `agent_decisions.cost_usd`).
- Claude: `cost_usd` always `0.0` (flat-rate subscription), gated instead
  by `AGENT_FIRM_CLAUDE_MAX_CALLS_PER_DAY` (§9).

## 15. Removal

- `DeepSeekClient` class deleted (replaced by `ZAIProvider`).
- `DEEPSEEK_API_KEY` / `DEEPSEEK_BASE_URL` removed from `.env.example` and
  config docs after the one-release compatibility window (§10); a
  follow-up cleanup task removes the fallback-read code itself.
- All "DeepSeek" strings in docstrings, log messages, and comments under
  `engine/agent_firm/` renamed to Z.ai or genericized.

## 16. What does not change

Prompts (`prompts/*.md`), agent reasoning, scoring, guardrails
(`guardrails.py`), decision thresholds, the LangGraph DAG shape
(`_build_graph()` in `firm.py`), the JSON output schema each agent expects
back, the Telegram signal-selection logic, and the research/production
workflow boundary (this refactor lives entirely inside
`engine/agent_firm/`, the production-side consumer of Firm decisions — it
does not touch `research/` or the write-fence boundary between them).
Trading decisions produced by the same provider before and after this
refactor should be identical — verified by re-running existing
`tests/agent_firm/test_firm.py` / `test_firm_v2.py` unmodified (they
inject a fake client satisfying the new interface) plus the `smoke.py`
harness. Existing tests must continue to pass unmodified except where they
directly reference the renamed `DeepSeekClient` class (§10).

## Future providers

Adding e.g. `OpenAIProvider` means: implement `FirmLLMProvider` (including
declaring its `ProviderCapabilities`), self-register via
`@register("openai")` in the Provider Registry (§4a), add its env vars,
and add its name to `AGENT_FIRM_PROVIDER_ORDER` (§6). No change to
`router.py` (it already iterates an arbitrary-length list, §4), the
Factory (§5 — it already resolves names generically via the Registry), the
config validation logic (§6 — it already validates against the Registry,
not a hardcoded set), `firm.py`, any `agents/*.py` module, prompts,
schemas beyond the interface, or Telegram builders.
