# Agent Firm — Migration Plan (What Stays, What Moves)

**Date:** 2026-07-28
**Basis:** `AGENT_FIRM_DEPENDENCY_AUDIT.md`, `AGENT_FIRM_ARCHITECTURE.md`.
**Purpose:** for every piece of code touched by this analysis, an explicit recommendation — remain
permanently inside Production Engine, or move into Agent Firm — with rationale. No code is moved as
part of producing this document; this is the plan the AF milestones execute against.

---

## Remains Permanently Inside Production Engine

| Code | Rationale |
|---|---|
| `engine/trade_plan.py` | Already duck-types `AgentDecision` with no import — this is Production Engine's own reporting logic consuming an external decision, exactly the shape a clean boundary should have. Nothing to move; this is the model to replicate elsewhere. |
| `scheduler/jobs.py`, `scheduler/scanner.py`'s call sites | These are Production Engine's own orchestration — *calling* Agent Firm's interface is Production Engine's job, not Agent Firm's. Only the call sites' *internals* (raw SQL against `agent_decisions`) need to change (move to calling AF-1's data layer instead), not the call sites themselves. |
| `monitor.py`'s `_agent_confirms_exit` | Production Engine's own exit-review logic that happens to consult Agent Firm as one input among others — stays, for the same reason as `trade_plan.py`. |
| `data/db.py`'s `init_agent_firm_tables()` **schema definition** | Contentious at first glance, but: this function's *presence* (the migration/idempotency machinery) belongs to Production Engine's single-schema-owner discipline (`CLAUDE.md`'s own stated invariant: "one SQLite file... `data.db.connect()` is the one entry point"). What should change is *how* the tables are read (AF-1's data layer), not *where* they're created. Splitting schema ownership across two files would violate the repository's own centralization invariant more than it would help. |
| `utils/telegram.py::send_telegram` | Already correctly classified "Shared utility, acceptable to keep" in the Dependency Audit — a working, redaction-hardened alerting path. No reason to fork it. |
| `security/route_policy.py`'s classification of `/api/agent/*` | Auth/RBAC policy for anything HTTP-exposed belongs to whichever process actually serves HTTP — today and for the foreseeable future, that's Production Engine's Flask app, regardless of where the underlying logic lives. |

## Should Move Into Agent Firm (or already lives there, but needs the boundary formalized)

| Code | Rationale |
|---|---|
| `engine/agent_firm/` in its entirety | Already physically located under `engine/agent_firm/` — the "move" here is organizational/versioning (per the Governance doc), not a file relocation within this repository today. |
| `routes/backtest.py`'s three `/api/agent/*` route **bodies** (not the Flask route registration itself) | The route registration (URL, method, auth classification) stays in Production Engine's web layer per the table above — but the *logic* each route executes (status computation, config mutation, audit assembly) should be a call into Agent Firm's own formalized operations contract (AF-2), not inline Production Engine code reaching into Agent Firm internals. |
| `tools/news_lookup.py`, `tools/sqlite_query.py`'s **direct DB access** | The tools themselves are Agent Firm's (LLM-callable, agent-facing) — but their current implementation reaches directly into Production Engine's database file. Once AF-4 defines the narrow read-only data API, the *tool* stays in Agent Firm; only its data-access implementation changes. |
| Agent Firm's own logging configuration (once written, per Blocker 4 / AF-1) | New code, belongs entirely to Agent Firm — it should not depend on Production Engine's `app.py` having run first. |
| The proposed `agent_decisions`/`agent_traces`/`provider_events` **data-access layer** (AF-1) | This is new code that should be written and owned inside `engine/agent_firm/`, even though the underlying tables' *schema definitions* remain in `data/db.py` per the table above — Agent Firm owns how its own data is queried, Production Engine owns where the file and connection-safety machinery live. |

## The One Genuinely Ambiguous Case

**`agent_decisions`/`agent_traces`/`provider_events` schema ownership** is the one item this plan
does not resolve unilaterally, and is called out explicitly rather than silently decided:

- **Argument for keeping schema in `data/db.py`:** consistent with the repository's stated single-
  schema-owner invariant; avoids a second migration-management system; the tables are just SQLite
  tables in the one shared file today, and splitting "schema ownership" across two Python files while
  the underlying file stays one database doesn't actually achieve isolation, just adds indirection.
- **Argument for moving schema ownership to Agent Firm:** if Agent Firm ever needs its own release
  cadence and its own versioned schema migrations independent of Production Engine's, this becomes
  necessary eventually — not for AF-1 through AF-6, but likely for AF-7 or beyond, especially if the
  "repository split" (already agreed to happen after the Operations Dashboard phase) becomes a
  literal separate database, not just a separate codebase.

**Recommendation:** defer this specific decision to AF-7 (Production Certification), by which point
it will be clear whether Agent Firm is moving to a genuinely separate deployment (needing its own
schema) or remaining a same-process, same-database subsystem with a cleaner internal API boundary
(in which case the current schema-in-`data/db.py` arrangement, combined with AF-1's data-access
layer, is sufficient and this ambiguity resolves itself without further action).

---

## Summary

Nothing in this plan requires moving a single file today. Every "should move" item in this plan is
either (a) already physically located in `engine/agent_firm/` and just needs its *boundary* formalized
per the roadmap, or (b) a piece of new code (the data-access layer, the logging setup) that should be
written inside `engine/agent_firm/` from the start rather than added to Production Engine and moved
later. The "remains permanently" column is deliberately the larger, more stable set — consistent with
this being a boundary-hardening exercise, not a wholesale extraction.
