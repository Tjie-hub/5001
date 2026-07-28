# AF-1 — Schema Ownership Decision

**Date:** 2026-07-28
**Status:** DECIDED. This document supersedes the deferral in
`AGENT_FIRM_MIGRATION_PLAN.md` ("defer this specific decision to AF-7") — that deferral was correct
under the prior document's mandate to avoid unilateral decisions on genuinely ambiguous items; AF-1's
explicit mandate is to eliminate exactly this kind of ambiguity before AF-2 begins. No further owner
decision is required on this question.

---

## The Decision

# Option B: Agent Firm owns the schema. Production Engine consumes through an interface.

`agent_decisions`, `agent_traces`, and `provider_events` move to being defined, migrated, and
versioned by Agent Firm. Production Engine's two remaining direct-SQL readers
(`scheduler/scanner.py:1070`, `routes/backtest.py:835`) are redirected through the Data Access Layer
(`AF1_DATA_ACCESS_LAYER.md`) instead.

---

## Justification

**1. It follows the Primary Principle directly, not by analogy.** `agent_decisions` is not a
Production Engine operational record that Agent Firm happens to write into — it *is* the decision,
literally the output of "Agent Firm owns decisions." `agent_traces` and `provider_events` are the
telemetry of how that decision was reached. All three tables are Agent Firm's own data model by
definition, not data Production Engine defines and Agent Firm merely populates.

**2. Production Engine v1 is frozen — Option A would require breaking that freeze on Agent Firm's
schedule, not Production Engine's.** If Production Engine owns the schema (`data/db.py`), then every
future Agent Firm change that needs a new column — a new provider's metadata field, a new decision
lifecycle nuance, a new telemetry dimension — requires touching Production Engine's now-frozen
codebase. That is a direct contradiction of the stated freeze ("any future enhancement must go
through a formal release process" — for Production Engine, not Agent Firm). Option B lets Agent Firm
evolve its own data model under its own governance (`AGENT_FIRM_GOVERNANCE.md`'s versioning policy)
without ever requiring a Production Engine release.

**3. It resolves Blocker 1 and Blocker 6 from the Architecture document together.** Blocker 1 (shared,
un-versioned schema) and Blocker 6 (no independent versioning) are actually the same underlying
problem viewed from two angles — a subsystem cannot be independently versioned while its own core
data model is defined by someone else's frozen codebase. Option B closes both at once.

**4. It does not violate Production Engine's single-connection-point invariant.** `CLAUDE.md`'s
invariant is about *connection safety* (`data.db.connect()` is the one place `busy_timeout`+WAL get
configured) — not about *schema content*. Agent Firm's migration logic still calls
`data.db.connect()` for the actual connection (see the Responsibility Matrix's Persistence/Migrations
rows) — it just owns the `CREATE TABLE`/`ALTER TABLE` statements and the idempotency logic for its
own three tables, exactly matching the pattern `research/tracking.py` and `forward_testing/storage/db.py`
already use today for *their own* schema, migrated through the same shared connection helper. This is
not a new pattern being invented for Agent Firm — it is the pattern the codebase already applies to
every other subsystem-owned schema.

**5. It's the smaller, safer change today.** Only two Production Engine call sites currently read
these tables directly with raw SQL (`scanner.py:1070`, `backtest.py:835`) — both already identified,
both already scoped for redirection in the Data Access Layer regardless of which option was chosen.
Option A would have required *more* work overall: Agent Firm's own six current internal readers
(`analytics.py`, `providers/metrics.py`, `providers/router.py`) would all need to call back into
Production Engine's schema module instead of using their own data layer, which is backwards from
where the codebase already is today (Agent Firm's own internal reads already treat these tables as
its own).

---

## What This Decision Requires (scoped to AF-1/AF-2, not implemented here)

- A new schema/migration module inside `engine/agent_firm/` (e.g. `storage.py`) taking over the
  `CREATE TABLE IF NOT EXISTS`/`ALTER TABLE ADD COLUMN` logic for these three tables — identical
  idempotent-migration pattern to what `data/db.py::init_agent_firm_tables()` uses today, just moved.
- `data/db.py::init_agent_firm_tables()` stops defining these three tables. (Production Engine v1 is
  frozen for *behavior* — this is an internal reorganization of where migration code lives, not a
  behavior change to anything Production Engine does or any interface it exposes. If this distinction
  is judged too fine for a "frozen" codebase, it is the one item in this decision that may need
  explicit owner sign-off before AF-1's implementation phase — flagged here for transparency, not
  silently assumed.)
- `scheduler/scanner.py:1070` and `routes/backtest.py:835` redirect to the Data Access Layer's
  read functions instead of raw SQL against tables Production Engine no longer defines.
- No data migration is required — this is a code-ownership change, not a schema change; the tables'
  actual columns and content are unaffected.

## What This Decision Does Not Require

- No change to the physical database file, connection mechanism, or backup/restore tooling — all of
  that remains exactly as `AF1_RESPONSIBILITY_MATRIX.md`'s Persistence row states.
- No change to `AgentDecision`/`SignalCandidate`'s Pydantic schema (the API contract) — this decision
  is about SQL table ownership, not the versioned interface contract.
- No repository split — this decision is scoped entirely within the current single-repository,
  same-process arrangement.
