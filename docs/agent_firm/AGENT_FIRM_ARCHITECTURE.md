# Agent Firm — Current Architecture and Independent-Releasability Blockers

**Date:** 2026-07-28
**Purpose:** Describe what Agent Firm is today, and enumerate everything preventing it from becoming
an independently versioned, independently releasable subsystem — each with severity, rationale,
proposed solution, and implementation effort. Basis: `AGENT_FIRM_DEPENDENCY_AUDIT.md`.

---

## 1. What Agent Firm Is Today

A multi-agent LLM signal-review pipeline living entirely inside `engine/agent_firm/`:

- **`firm.py`** — the LangGraph-orchestrated evaluation graph: Technical/Flow/Regime/News analyst
  agents run in parallel, feed Bull/Bear debate agents, which feed a Risk Manager agent that produces
  the final `approve`/`veto`/`degraded` decision. Persists to `agent_decisions`/`agent_traces`.
- **`agents/`** — the individual agent role implementations (bull, bear, flow, news, regime, risk,
  technical).
- **`providers/`** — a provider-abstraction layer (Z.ai primary, Claude CLI fallback) with its own
  circuit breaker, quota-aware routing/governor, rate limiting, and telemetry (`provider_events`).
- **`schemas.py`** — the Pydantic contract (`SignalCandidate`, `AgentResult`, `AgentDecision`,
  `AgentState`) described in full in `AGENT_FIRM_INTERFACE_SPEC.md`.
- **`tools/`** — LLM-callable tools (news lookup, SQLite query, web search) that give agents direct
  read access to the production database and external web search.
- **`config.py`** — a fully independent configuration module (own `load_dotenv()`, own env-var
  surface) — already decoupled from Production Engine's root `config.py`.
- **`analytics.py`, `smoke.py`, `guardrails.py`** — reporting, smoke-testing, and output-sanitization
  utilities.

It is invoked from three places in Production Engine (`scheduler/jobs.py`, `scheduler/scanner.py`,
`monitor.py`) via the stable interface, and reached into directly from a fourth (`routes/backtest.py`'s
three `/api/agent/*` routes) via internal functions that are not part of that interface.

---

## 2. Blockers to Independent Releasability

### Blocker 1 — Shared, un-versioned database schema (`agent_decisions`, `agent_traces`, `provider_events`)

**Severity: P0 (release-blocking for independence)**
**Rationale:** these three tables are defined in Production Engine's `data/db.py`, written
exclusively by Agent Firm's `firm.py`/`providers/events.py`, and read directly via hand-written SQL
from both sides (`scheduler/scanner.py`, `routes/backtest.py` on the Production Engine side;
`analytics.py`, `providers/metrics.py`, `providers/router.py` on the Agent Firm side). There is no
query abstraction layer, no schema version, and no contract — a column rename on either side breaks
the other silently, and neither side can evolve its own schema without coordinating with the other's
release cycle. This is the single largest structural obstacle to Agent Firm being independently
versionable: its own data model is not actually its own.
**Proposed solution:** introduce a thin data-access layer Agent Firm owns exclusively (e.g.
`engine/agent_firm/storage.py` with typed read functions), and have Production Engine's two call
sites (`scheduler/scanner.py:1070`, `routes/backtest.py:835`) call through it instead of raw SQL.
Once that abstraction exists, Agent Firm's schema becomes something *it* can version, and Production
Engine depends on a function signature instead of column names.
**Effort:** Medium — no schema change required, purely introducing an abstraction layer over
existing tables and redirecting ~3 call sites.

### Blocker 2 — Direct, unmediated database file access from LLM tools

**Severity: P1**
**Rationale:** `tools/news_lookup.py` and `tools/sqlite_query.py` give a live LLM agent direct
`sqlite3` read access to the entire production database via `data.db.connect`. This works fine
in-process today, but it means Agent Firm's tool layer has no notion of "its own data boundary" —
if Agent Firm ever runs in a separate process or container from Production Engine, these tools break
entirely (no shared filesystem access to the DB file), and even today, nothing scopes what an LLM
tool call can actually query.
**Proposed solution:** define a narrow, read-only data API (even if implemented as a same-process
Python function to start) that these tools call instead of opening the database directly — the
function decides what's queryable, not the LLM-constructed SQL.
**Effort:** Medium — two tool files, needs careful design of what queries actually need to stay
supported (this is agent-facing behavior, not purely internal, so scope reduction risk exists).

### Blocker 3 — `routes/backtest.py`'s three `/api/agent/*` routes reach into internals, not the interface

**Severity: P1**
**Rationale:** `/api/agent/status`, `/api/agent/config`, `/api/agent/audit` call
`engine.agent_firm.config`'s module functions and `engine.agent_firm.analytics`'s functions directly,
and one of them does its own raw SQL against `agent_decisions`. These are legitimate operational
needs (status, control, audit) but are implemented as direct internal imports rather than through
any interface boundary — meaning Production Engine's own web layer is exactly as tightly coupled to
Agent Firm's internals as the LLM tools are to the database.
**Proposed solution:** define these three operations (status, set-mode, audit) as part of a small,
explicit "operations" interface (alongside `evaluate`/`evaluate_staged`/`reset_market_ctx` in the
stable contract), backed by Blocker 1's data-access layer for the audit route's DB reads.
**Effort:** Small — three routes, mostly a matter of naming the existing functions as contract rather
than rewriting them.

### Blocker 4 — Agent Firm has no logging configuration of its own

**Severity: P1**
**Rationale:** `providers/router.py` and other modules use `logging.getLogger("agent_firm...")`,
which only gets JSON structuring and secret redaction because it's a child of the root logger
Production Engine's `app.py` configures at import time. If Agent Firm ever runs standalone, its logs
would be unstructured, unrotated, and — critically — **unredacted**, since `SecretRedactionFilter` is
attached to Production Engine's handlers, not a property of the logger name.
**Proposed solution:** Agent Firm should own its own `setup_logging()`-equivalent (even if it
delegates to a shared library function once one exists), so its logging correctness doesn't depend on
which process imports it first.
**Effort:** Small — one new module, following the exact pattern `utils/logging_config.py` already
established.

### Blocker 5 — Test-layer coupling to internal package structure

**Severity: P2**
**Rationale:** Several Production Engine tests monkeypatch `engine.agent_firm`'s package attributes
directly (`import engine.agent_firm as _pkg; monkeypatch.setattr(_pkg, "firm", ...)`) rather than
mocking at the interface boundary — an artifact of the current lazy-import pattern
(`from engine.agent_firm import firm` inside function bodies rather than at module top level, done
deliberately to avoid import cycles/heavy dependencies at import time). This means Agent Firm can't
freely restructure its own internal module layout without also updating Production Engine's test
suite, which is exactly backwards for an independent subsystem.
**Proposed solution:** once the interface is formally versioned (`AGENT_FIRM_GOVERNANCE.md`),
provide a lightweight test double / fixture Production Engine's tests can depend on instead of
monkeypatching real internals.
**Effort:** Small–Medium — mostly test-file changes, no production code risk, but touches ~10 test
files.

### Blocker 6 — No independent CI, versioning, or release artifact exists for Agent Firm

**Severity: P0 (definitional — this is what "independently releasable" means)**
**Rationale:** Agent Firm today ships exactly when Production Engine ships, from the same commit,
tested by the same `pytest -q` run, with no independent version number, changelog, or compatibility
guarantee. There is currently no way to answer "what version of Agent Firm is running" independent of
"what git commit of the whole repo is deployed."
**Proposed solution:** the entire subject of `AGENT_FIRM_GOVERNANCE.md` and
`AGENT_FIRM_IMPLEMENTATION_ROADMAP.md` — versioning policy, its own test suite gate, and (eventually,
per the standing instruction already in place) its own repository.
**Effort:** Large — this is the roadmap itself, not a single fix.

---

## 3. Blocker Summary

| Blocker | Severity | Effort |
|---|---|---|
| 1. Shared, un-versioned DB schema | P0 | Medium |
| 2. Unmediated DB access from LLM tools | P1 | Medium |
| 3. `/api/agent/*` routes bypass the interface | P1 | Small |
| 4. No independent logging configuration | P1 | Small |
| 5. Test-layer package-attribute coupling | P2 | Small–Medium |
| 6. No independent CI/versioning/release artifact | P0 | Large |

Blockers 1 and 6 are the two genuinely structural obstacles; 2–5 are real but individually small.
None require touching Production Engine's frozen v1 baseline in a way that changes its behavior —
every proposed solution is additive (a new abstraction layer, a new logging module, a renamed
contract) rather than a change to what Production Engine already does today.
