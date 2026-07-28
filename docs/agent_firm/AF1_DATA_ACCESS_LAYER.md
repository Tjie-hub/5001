# AF-1 — Data Access Layer Design

**Date:** 2026-07-28
**Basis:** `AF1_SCHEMA_OWNERSHIP_DECISION.md` (Agent Firm owns `agent_decisions`/`agent_traces`/
`provider_events`), `AGENT_FIRM_DEPENDENCY_AUDIT.md` (every raw-SQL cross-reach this layer must
eliminate).
**Scope:** design only — repository interfaces and contracts, no implementation.

---

## Every Raw-SQL Cross-Reach This Layer Must Eliminate

| Location | Current raw SQL | Replacement |
|---|---|---|
| `scheduler/scanner.py:1070` | `SELECT ticker FROM agent_decisions ...` | `AgentFirmRepo.recent_approved_tickers(...)` |
| `routes/backtest.py:835` | `SELECT COUNT(*), SUM(...) FROM agent_decisions WHERE DATE(created_at)=?` | `AgentFirmRepo.daily_decision_stats(date)` |
| `engine/agent_firm/analytics.py:18,25,68,69,137` | Various `agent_decisions`/`agent_traces` joins | `AgentFirmRepo`'s own internal use of its own repository — no external caller change, but now going through the same typed layer as everyone else, not ad hoc SQL |
| `engine/agent_firm/providers/metrics.py:49,61` | `agent_traces` queries | Same — internal caller, same repository |
| `engine/agent_firm/providers/router.py:35` | `agent_traces` query | Same |
| `engine/agent_firm/firm.py:445,460` | `INSERT OR REPLACE INTO agent_decisions`, `INSERT INTO agent_traces` | `AgentFirmRepo.record_decision(decision: AgentDecision)` — the one write path |
| `engine/agent_firm/providers/events.py` | `provider_events` insert | `AgentFirmRepo.record_provider_event(event: ProviderEvent)` |

---

## Repository Design

### `AgentFirmRepo` — the single object both sides depend on

Lives in `engine/agent_firm/` (per the Schema Ownership Decision). Production Engine imports this
repository's read-only query functions; it never constructs SQL against these three tables again.

**Write operations** (Agent Firm-internal only — Production Engine never calls these):
```
record_decision(decision: AgentDecision) -> None
record_trace(decision_id: int, trace: AgentResult) -> None
record_provider_event(event: ProviderEvent) -> None
```
**Invariant:** every write is idempotent at the storage layer the same way `_job_sentinel`-style
dedup guards work elsewhere in this codebase — a retried write for the same decision must not create
a duplicate row (`firm.py` already uses `INSERT OR REPLACE`; this invariant is preserved, not
introduced new).

**Read operations** (Production Engine's two current call sites, reduced to typed functions):
```
recent_approved_tickers(strategy: str, since: str) -> list[str]
daily_decision_stats(date: str) -> DecisionStats
```
where `DecisionStats` is a small typed value (`evaluated: int, approved: int, vetoed: int,
cost_usd: float`) — replacing the current ad hoc dict `routes/backtest.py` builds by hand from raw
row tuples.

**Read operations** (Agent Firm-internal — used by `analytics.py`, `providers/metrics.py`,
`providers/router.py`, but now through this one repository instead of each module writing its own
SQL):
```
decision_history(ticker: str, since: str) -> list[AgentDecision]
trace_history(provider: str, since: str) -> list[AgentResult]
provider_event_history(provider: str, event_type: str, since: str) -> list[ProviderEvent]
```

### Contract Guarantees

- **No caller — Production Engine or Agent Firm-internal — constructs SQL against these three tables
  outside `AgentFirmRepo`.** This is the one rule that actually closes Blocker 1; everything else in
  this design exists to make that rule followable without anyone needing to write raw SQL to get
  something done.
- **The repository's read functions return typed objects, never raw rows/tuples/dicts assembled ad
  hoc at the call site** — this is what makes a future schema change (adding a column, renaming
  one) safe: callers depend on a function signature and a typed return value, not column positions.
- **The repository is the only thing that needs to know these three tables share one SQLite file with
  Production Engine's own tables.** Callers on both sides depend on the repository, not on
  `data.db.connect()` directly, for anything touching these three tables specifically — `connect()`
  remains available for connections generally.

---

## What Stays Explicitly Out of This Layer's Scope

- `agent_decisions`'s foreign-key relationship from `scheduled_signals.agent_decision_id` (a
  Production Engine-owned table referencing an Agent Firm-owned one) is a cross-schema FK that
  predates this design and is not resolved by it — flagged as a known, accepted wrinkle: Production
  Engine's own schema has one column that reaches into Agent Firm's data model. Removing this FK is
  out of scope for AF-1 (would require a Production Engine schema change, which is frozen); the
  repository layer does not need to fix it to close Blocker 1, since it's a schema-level reference,
  not a raw-SQL query pattern.
- This design does not address `tools/news_lookup.py`/`tools/sqlite_query.py`'s direct database
  access — that is `AF1_CONTEXT_API.md`'s scope, a different problem (LLM tool access to arbitrary
  production data, not Agent Firm's own decision/telemetry tables).
