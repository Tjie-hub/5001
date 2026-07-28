# AF-1 — Implementation Spec (Master Synthesis)

**Date:** 2026-07-28
**Purpose:** the single document AF-2 implements against. Synthesizes
`AF1_RESPONSIBILITY_MATRIX.md`, `AF1_SCHEMA_OWNERSHIP_DECISION.md`, `AF1_DATA_ACCESS_LAYER.md`,
`AF1_CONTEXT_API.md`, and `AF1_FAILURE_CONTRACT.md` into one dependency-by-dependency disposition
(KEEP / REPLACE / REMOVE / DEFER), and closes the small number of items those five documents left
open — this document's decisions on those items are final and supersede any hedging language
elsewhere in the AF-1 set, the same way `AF1_SCHEMA_OWNERSHIP_DECISION.md` superseded
`AGENT_FIRM_MIGRATION_PLAN.md`'s earlier deferral.

---

## Part 1 — Final Decisions on Every Item the Other Five Documents Left Open

### Decision A — Timeout Contract (was open in `AF1_FAILURE_CONTRACT.md` §8)

**Resolved: Option (a).** Agent Firm commits to an explicit per-`evaluate()` timeout, with an internal
fallback to `degraded` on timeout — exactly the same resolution every other failure mode in the
Failure Contract already converges to. Leaving this "unbounded" (option b) would be the one
inconsistent failure mode in an otherwise uniform contract, and would leave every caller (scheduler
jobs, `monitor.py`) exposed to an unbounded hang with no documented ceiling. **Specific value is an
AF-2 implementation detail** (informed by existing operational bounds — e.g. `gunicorn.conf.py`'s
300s worker timeout as an outer ceiling — but the number itself doesn't need to be fixed in
architecture); the architectural commitment (bounded, fails to `degraded`, never hangs the caller
indefinitely) is decided now.

### Decision B — `tools/sqlite_query.py`'s Free-Form SQL Capability (was DEFER-leaning in earlier drafts)

**Resolved: REPLACE, not DEFER.** A tool that lets an LLM construct and execute arbitrary SQL against
the live production database is the single most direct violation possible of this document's own
stated principle ("Agent Firm must never open production databases directly"). This is decided now,
not left open: free-form SQL execution as an LLM-callable capability does not survive AF-1/AF-2.
**What replaces it** (AF-4 scope, per the Roadmap) is a bounded set of parameterized query functions
covering whatever real usage patterns exist today — determining the exact set of needed queries is
implementation work for AF-4, but the architectural boundary (no arbitrary SQL, ever, from an LLM
tool call) is fixed now.

### Decision C — Does Moving Schema Ownership Violate the Production Engine Freeze?

**Resolved: No.** `AF1_SCHEMA_OWNERSHIP_DECISION.md` hedged this as possibly needing separate sign-off;
this document removes that hedge. The Production Engine freeze applies to *behavior and interfaces*
Production Engine exposes — not to which Python module contains a `CREATE TABLE` statement for a
table Production Engine never writes and only reads through two call sites (both already being
redirected to the Data Access Layer regardless). No observable behavior, no API response shape, no
scheduled job's timing or output changes. This is an internal code-organization change and proceeds
under AF-1 without requiring a separate freeze exception.

### Decision D — Partial-Consensus Weighting (Failure Contract §4)

**Resolved: intentionally left as agent discretion, not an open ambiguity.** Unlike A–C, this was
never actually blocking — it's a deliberate design choice (the Risk agent's own reasoning decides how
much a partial analyst failure matters) that AF-2 does not need to resolve to proceed. Restated here
only to confirm it is not on the list of things blocking implementation.

---

## Part 2 — Every Dependency, Final Disposition

| Dependency | Disposition | Rationale (cross-referenced, not repeated in full) |
|---|---|---|
| `scheduler/jobs.py` → `firm.evaluate_staged()`, `SignalCandidate` | **KEEP** | Public API, unchanged — Interface Spec |
| `scheduler/scanner.py` → `reset_market_ctx()` | **KEEP** | Public API, unchanged lifecycle hook |
| `scheduler/scanner.py` → `evaluate()`/`evaluate_staged()`, `SignalCandidate` | **KEEP** | Public API, unchanged |
| `scheduler/scanner.py`, `monitor.py` → `engine.agent_firm.config` (read-only state checks) | **DEFER** | Acceptable narrow reads of Agent Firm's own active/enabled state for orchestration purposes; formalize alongside the `/api/agent/status` work in AF-2 rather than duplicating that effort now |
| `monitor.py` → `firm`, `SignalCandidate` (exit-veto check) | **KEEP** | Public API, already fail-open-verified |
| `routes/backtest.py` → `/api/agent/status`, `/api/agent/config`, `/api/agent/audit` | **REPLACE** | Becomes a formalized ops contract (Architecture doc Blocker 3), backed by the Data Access Layer for the audit route's reads |
| `scheduler/scanner.py:1070`, `routes/backtest.py:835` raw SQL on `agent_decisions` | **REPLACE** | Redirect to `AgentFirmRepo` per Data Access Layer |
| `engine/trade_plan.py`'s duck-typed `AgentDecision` consumption | **KEEP** | Already correctly built — the model, not a problem |
| Test-layer package-attribute monkeypatching (~10 test files) | **REPLACE** | Official test double at the interface boundary, per Architecture doc Blocker 5 |
| `analytics.py`, `providers/events.py` → `data.db.connect` | **REPLACE** | Redirect through `AgentFirmRepo`, which itself still calls `data.db.connect()` for the actual connection — infrastructure unchanged, access pattern formalized |
| `tools/news_lookup.py` → `data.db.connect` | **REPLACE** | Becomes a Context API-provided `RecentHistory.news_mentions` field, or a narrowly-scoped query function if a live lookup is still needed — bounded either way |
| `tools/sqlite_query.py` → `data.db.connect` (arbitrary SQL) | **REPLACE** | See Decision B above — the free-form capability is removed; a bounded replacement lands in AF-4 |
| `firm.py`'s `agent_decisions`/`agent_traces` writes | **REPLACE** | Redirect through `AgentFirmRepo.record_decision()`/`record_trace()` |
| `providers/metrics.py`, `providers/router.py` → `agent_traces` reads | **REPLACE** | Redirect through `AgentFirmRepo` — internal callers, same repository as everyone else |
| `providers/alerts.py` → `utils.telegram.send_telegram` | **KEEP** | Shared utility, already redaction-hardened, correctly classified acceptable in the Dependency Audit |
| `engine/agent_firm/config.py`'s independence from root `config.py` | **KEEP** | Already correct, zero coupling today |
| Implicit root-logger inheritance (no explicit Agent Firm logging setup) | **REPLACE** | Agent Firm gets its own explicit logging configuration, per Architecture doc Blocker 4 / Responsibility Matrix |
| `agent_decisions`/`agent_traces`/`provider_events` schema location | **REPLACE** | Moves from `data/db.py` to an Agent-Firm-owned module, per Schema Ownership Decision |
| `scheduled_signals.agent_decision_id` foreign key into `agent_decisions` | **DEFER** | Explicitly out of AF-1/AF-2 scope — a schema-level wrinkle, not a query-pattern problem the Data Access Layer needs to solve; revisit only if/when a genuine physical DB split is pursued |
| `security/route_policy.py`'s classification of `/api/agent/*` | **KEEP** | Auth/RBAC stays with whoever serves HTTP — Responsibility Matrix |
| `firm.py`'s `_market_ctx` process-level cache (lifecycle) | **KEEP** | Caching lifecycle and `reset_market_ctx()` hook are correct and unchanged |
| `_build_context()`'s 7 raw SQL queries populating that cache | **REPLACE** | Entirely superseded by the Context API's `MarketContext`/`RecentHistory`/`PortfolioState` objects |
| `langgraph`, `openai`, `pydantic`, `httpx`, `subprocess` (Claude CLI) | **KEEP** | Fully self-contained external dependencies, zero Production Engine coupling |
| Timeout contract | **RESOLVED (Decision A)** | See above |

**Zero items remain classified as unresolved ambiguity.** Every dependency in the audit has a final
disposition; every open question the five prior AF-1 documents raised has a decision recorded in
Part 1.

---

## Part 3 — What AF-2 Implements, In Order

1. Agent Firm's own logging setup module (small, no dependencies on the rest of this list).
2. `AgentFirmRepo` (Data Access Layer) — write path first (`record_decision`, `record_trace`,
   `record_provider_event`), then read path, then redirect `firm.py`'s existing raw SQL through it.
3. Move the three tables' schema/migration definitions out of `data/db.py` into Agent Firm's own
   module (Schema Ownership Decision) — mechanical, low-risk, no data migration required.
4. Redirect the two remaining Production Engine raw-SQL call sites
   (`scanner.py:1070`, `backtest.py:835`) through `AgentFirmRepo`'s typed read functions.
5. Formalize the three `/api/agent/*` routes as the ops contract (status/set-mode/audit), backed by
   step 2's repository.
6. Build the Context API's six typed objects and redirect `_build_context()` to consume them instead
   of running its own raw SQL — the largest single implementation item, since it touches the highest-
   traffic code path (every evaluation).
7. Wire `RiskLimits.entries_blocked` into the guardrail layer — the one genuinely new behavior in this
   entire spec (everything else is reorganization of existing behavior).
8. Implement the per-`evaluate()` timeout (Decision A) with fallback to `degraded`.
9. Replace `tools/sqlite_query.py`'s free-form SQL with the bounded query set (Decision B) —
   sequenced last since it depends on understanding real usage patterns from steps 2–6 having
   already formalized what queries actually matter.
10. Replace test-layer monkeypatching with the official test double, once the interface it targets
    (steps 2–7) is stable enough to have one.

This ordering respects the Roadmap's AF-1→AF-4 sequencing (`AGENT_FIRM_IMPLEMENTATION_ROADMAP.md`)
while resolving the specific dependency graph within AF-2's own scope.
