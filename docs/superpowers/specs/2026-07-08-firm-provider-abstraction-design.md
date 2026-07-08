# Firm LLM Provider Abstraction — Design

Date: 2026-07-08
Status: Approved, pending implementation plan

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

Goal: make the Firm engine fully provider-independent, supporting exactly
two active providers (Claude, Z.ai) today, with a clean seam for future
providers (OpenAI, Gemini, Ollama, local vLLM, ...) that requires **zero**
changes to Firm business logic — prompts, scoring, thresholds, validation,
JSON schema, LangGraph flow, and Telegram signal logic must all remain
identical.

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
    → Provider Router (providers/router.py)
      → FirmLLMProvider (providers/base.py — interface)
        → ClaudeProvider (providers/claude.py)
        → ZAIProvider (providers/zai.py)
        → [future: OpenAIProvider, GeminiProvider, ...]
    → Unified ProviderResponse
  → Firm Decision → Production
```

Providers never know about each other and never contain failover logic —
that's the Router's job. The Firm engine never knows which provider is
active; it only ever holds an object satisfying `FirmLLMProvider` (in
practice, the Router itself, which also satisfies the interface).

## 1. Provider interface

`engine/agent_firm/providers/base.py`, kept deliberately small:

```python
class FirmLLMProvider(Protocol):
    name: str                                   # "claude" | "zai"

    async def generate(
        self, messages: list[dict], *, timeout: float | None = None,
    ) -> ProviderResponse: ...

    async def health(self) -> bool: ...          # diagnostics only, see §2

    def model(self) -> str: ...
```

No `availability()`, no `retry()` on the interface (see §2, §3).

### ProviderResponse

```python
class ProviderResponse(BaseModel):
    content: str
    provider: str          # "claude" | "zai" — who actually served this
    model: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    duration_s: float
    request_id: str | None = None   # Claude: session_id; Z.ai: response.id
    timestamp: str                  # ISO8601, set at response time
    failover: bool = False          # True if this is a fallback response
                                     # after the primary provider failed
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
`auto` mode).

## 2. No availability() in the inference path

`generate()` simply attempts generation and returns a `ProviderResponse`,
or raises a `ProviderException` subclass. No pre-flight `availability()`
check before every call — that would double provider round-trips for no
benefit, since `generate()` failing *is* the availability signal.

`health()` remains on the interface for out-of-band diagnostics (e.g. a
future ops script or dashboard querying "is Claude reachable right now"),
but is never called as part of the request path. Not wired into a
scheduled job in this refactor — out of scope until there's an actual
consumer for it (YAGNI).

## 3. Provider Router

`engine/agent_firm/providers/router.py`. Owns all selection and failover
logic; providers stay dumb.

```python
class ProviderRouter:
    def __init__(self, primary: FirmLLMProvider, fallback: FirmLLMProvider | None): ...
    async def generate(self, messages, *, timeout=None) -> ProviderResponse:
        try:
            return await self.primary.generate(messages, timeout=timeout)
        except ProviderException as err:
            if self.fallback is None:
                raise
            log.info("Provider: %s → %s\nReason: %s",
                      self.primary.name, self.fallback.name, err)
            resp = await self.fallback.generate(messages, timeout=timeout)
            resp.failover = True
            return resp
```

Single-mode (`claude` or `zai`) constructs the Router with `fallback=None`
— a failure propagates straight up to the calling agent's existing
try/except (each agent module already wraps its call and returns
`AgentResult(status="failed", error=...)` — this fail-open behavior is
unchanged).

`ZAIProvider` keeps its own existing internal retry-once-on-5xx (unchanged,
provider-local resilience for transient errors); that is distinct from the
Router's cross-provider failover.

## 4. Configuration

All env-var based, matching the existing all-`os.getenv` pattern in
`engine/agent_firm/config.py` — no new config file format introduced.

```
AGENT_FIRM_PROVIDER=auto        # claude | zai | auto   (default: zai — preserves current prod behavior)
AGENT_FIRM_PRIMARY=claude       # only read when PROVIDER=auto
AGENT_FIRM_FALLBACK=zai         # only read when PROVIDER=auto

ZAI_API_KEY=...                 # was DEEPSEEK_API_KEY
ZAI_BASE_URL=...                # was DEEPSEEK_BASE_URL
AGENT_FIRM_MODEL=glm-5.2        # unchanged — Z.ai model id

AGENT_FIRM_CLAUDE_MODEL=sonnet  # claude CLI --model value
AGENT_FIRM_CLAUDE_MAX_CONCURRENT=4     # subprocess semaphore
AGENT_FIRM_CLAUDE_MAX_CALLS_PER_DAY=200

AGENT_FIRM_PROVIDER_TIMEOUT=75  # generic default (matches today's PER_AGENT_TIMEOUT_S)
AGENT_FIRM_CLAUDE_TIMEOUT=      # optional override; falls back to PROVIDER_TIMEOUT
```

**Startup validation, fail loud:** when the Router is constructed (lazily,
first call into `firm.evaluate()` — matching the existing lazy-import
pattern in `__init__.py`), validate `AGENT_FIRM_PROVIDER ∈
{claude, zai, auto}` and, if `auto`, that `AGENT_FIRM_PRIMARY` /
`AGENT_FIRM_FALLBACK` are each in `{claude, zai}` and distinct. An invalid
value raises immediately with a clear message — never silently falls back
to a default provider.

## 5. ClaudeProvider

`engine/agent_firm/providers/claude.py`. No SDK — shells out to the `claude`
CLI per call via `asyncio.create_subprocess_exec` (non-blocking, compatible
with the existing `asyncio.gather` fan-out in `firm.py`):

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
always forced to `0.0` in the returned `ProviderResponse` (see §12 —
subscription is flat-rate, not metered per call). Non-zero exit / timeout /
malformed output classified into the four `ProviderException` subclasses
on a best-effort basis (pattern-matching known usage-limit / rate-limit
phrasing in stderr); anything unrecognized becomes `ProviderUnavailable`.
Flag classification is implementation-detail, verified empirically during
build (exact CLI error text isn't documented and will be confirmed with a
live smoke call).

**Concurrency guard:** `asyncio.Semaphore(AGENT_FIRM_CLAUDE_MAX_CONCURRENT)`
inside `ClaudeProvider`, so it self-throttles regardless of how many
candidates/agents `firm.py` fans out concurrently — protects the
subscription from being hammered by 100+ simultaneous subprocess spawns on
a large batch. Z.ai keeps its current unbounded concurrency.

**Daily call cap:** enforced by the Router (not the provider) by counting
today's `agent_traces` rows with `provider='claude'` before dispatching to
Claude in `auto` mode — mirrors the existing `_spend_today()` pattern in
`firm.py`. Once `AGENT_FIRM_CLAUDE_MAX_CALLS_PER_DAY` is reached, the
Router routes straight to the fallback without attempting Claude, logging
`Provider: Claude → Z.ai\nReason: Claude daily call cap reached`. In
single-mode `AGENT_FIRM_PROVIDER=claude` (no fallback configured), the cap
does not block — there's nowhere else to route, matching "the production
pipeline should continue operating whenever at least one provider is
available."

## 6. ZAIProvider (rename, not rewrite)

`engine/agent_firm/client.py` → `providers/zai.py`. `DeepSeekClient` →
`ZAIProvider`. Internals unchanged (same `AsyncOpenAI` call, same
retry-once-on-5xx). `chat()` renamed/aliased to satisfy `generate()`;
response now carries `provider="zai"`, `request_id` from the OpenAI
response's `id`, `timestamp` at response time.

Env vars: `DEEPSEEK_API_KEY`/`DEEPSEEK_BASE_URL` → `ZAI_API_KEY`/
`ZAI_BASE_URL`. One release of fallback: if the new vars are unset but the
old ones are present, read them with a `logging.warning` startup notice;
remove the fallback in a follow-up cleanup once `.env` is confirmed
migrated. `DeepSeekClient` class name, `DeepSeekProvider` (never existed,
n/a), and all "DeepSeek" references in docstrings/comments across
`engine/agent_firm/` are renamed to Z.ai. `tests/agent_firm/test_client.py`
→ `test_zai_provider.py`, same assertions against the renamed class.

## 7. Persistence

`agent_traces` gets three additive columns (same migration pattern as
existing schema growth in `data/db.py`):

```sql
ALTER TABLE agent_traces ADD COLUMN provider TEXT;
ALTER TABLE agent_traces ADD COLUMN model TEXT;
ALTER TABLE agent_traces ADD COLUMN failover INTEGER DEFAULT 0;
```

`agent_decisions` gets:

```sql
ALTER TABLE agent_decisions ADD COLUMN providers_used TEXT;  -- JSON list, e.g. ["claude"] or ["claude","zai"]
```

`AgentResult` (schemas.py) gains `provider: str = ""`, `model: str = ""`,
`failover: bool = False`. `AgentDecision` gains
`providers_used: list[str] = Field(default_factory=list)`, computed in
`firm.py`'s `_run_risk` as the distinct `provider` values across that
decision's 7 traces (same place `tokens_in`/`tokens_out`/`cost_usd` are
already rolled up today).

Persisting `model` alongside `provider` (not just provider) is required per
the user's explicit ask, for historical auditing across future model
changes (e.g. `glm-5.2` → a later GLM version, or a Claude model bump)
without conflating that with a provider swap.

## 8. Metrics

No new metrics infrastructure (no Prometheus/StatsD in this codebase
today, confirmed by search) — computed on demand from `agent_traces`, which
now carries `provider`, `model`, `duration_s`, and (via the existing
`error` handling in each agent's except-block) failure classification.

`engine/agent_firm/providers/metrics.py`: pure SQL-aggregate functions,
following the same pattern as `engine/health_report.py`'s report-time
queries — not a live/streaming metrics system.

```python
def provider_stats(db_path: str, provider: str, since: str) -> ProviderStats:
    """calls, failures, timeouts, failovers, avg/p50/p95 duration_s,
    (zai only) total cost_usd + tokens, computed from agent_traces."""
```

P50/P95 computed in Python from the queried `duration_s` list (SQLite has
no native percentile function) — consistent with how other stats in this
codebase (e.g. WF metrics) are computed post-query rather than in SQL.

This is available for ad-hoc use (a future ops script, or folded into an
existing report) — no new scheduled job or dashboard is being added in
this refactor unless a follow-up specifically asks for one.

## 9. Telegram

Both `scheduler/jobs.py::_build_premarket_firm_message` (08:35 premarket
scan) and the EOD trade-plan Telegram builder in `engine/trade_plan.py`
(16:40) get one appended line, derived from the union of `providers_used`
across the batch's decisions:

- All-Claude → `Firm Provider:\nClaude`
- All-Z.ai → `Firm Provider:\nZ.ai`
- Any failover present in the batch → `Firm Provider:\nClaude → Z.ai (Auto Failover)`

No other formatting or signal-logic changes to either message.

## 10. Cost accounting (unchanged from prior review round)

- Z.ai: real per-token `cost_usd`, gated by existing `DAILY_SPEND_CAP_USD`
  (unchanged — `_spend_today()`/`_over_daily_cap()` logic in `firm.py` stays
  exactly as-is, still summing `agent_decisions.cost_usd`).
- Claude: `cost_usd` always `0.0` (flat-rate subscription), gated instead
  by `AGENT_FIRM_CLAUDE_MAX_CALLS_PER_DAY` (§5).

## 11. Removal

- `DeepSeekClient` class deleted (replaced by `ZAIProvider`).
- `DEEPSEEK_API_KEY` / `DEEPSEEK_BASE_URL` removed from `.env.example` and
  config docs after the one-release compatibility window (§6); a follow-up
  cleanup task removes the fallback-read code itself.
- All "DeepSeek" strings in docstrings, log messages, and comments under
  `engine/agent_firm/` renamed to Z.ai or genericized (e.g. firm.py's
  module docstring "Phase 2: LangGraph DAG, 7 agents" already provider-
  agnostic, unaffected).

## 12. What does not change

Prompts (`prompts/*.md`), agent reasoning, scoring, guardrails
(`guardrails.py`), decision thresholds, the LangGraph DAG shape
(`_build_graph()` in `firm.py`), the JSON output schema each agent expects
back, and all Telegram signal-selection logic. Trading decisions produced
by the same provider before and after this refactor should be identical —
verified by re-running existing `tests/agent_firm/test_firm.py` /
`test_firm_v2.py` unmodified (they inject a fake client satisfying the new
interface) plus the `smoke.py` harness.

## Future providers

Adding e.g. `OpenAIProvider` means: implement `FirmLLMProvider`, register
it in the Router's provider-name lookup, add its env vars. No change to
`firm.py`, any `agents/*.py` module, prompts, schemas beyond the interface,
or Telegram builders.
