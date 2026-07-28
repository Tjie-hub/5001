# AF-1 — Responsibility Matrix

**Date:** 2026-07-28
**Primary principle:** Production Engine owns operations. Agent Firm owns decisions. Every row below
resolves to exactly one owner, or an explicit, non-ambiguous split where a concern genuinely spans
both (stated as a rule, not left open).

---

| Concern | Owner | Rule |
|---|---|---|
| **Scheduler** | Production Engine | APScheduler, all cron-equivalent timing, all job registration. Agent Firm has no scheduling of its own — it is invoked synchronously, in-process, by Production Engine's own scheduled jobs. This never changes, even after a repository split. |
| **Runtime** (process lifecycle: start/stop/restart, gunicorn, systemd) | Production Engine | Agent Firm is a library Production Engine's runtime loads, not a runtime of its own, for as long as it lives in-process. If it ever becomes a separate service (out of scope for AF-1/AF-2), this row is revisited then, not now. |
| **Lifecycle** *(process lifecycle — not decision lifecycle, which is Evaluation/Consensus below)* | Production Engine | Same as Runtime. Agent Firm has no independent startup/shutdown sequence to design in AF-1. |
| **Configuration** | Split — each subsystem owns its own | Not ambiguous: `config.py` (Production Engine) and `engine/agent_firm/config.py` (Agent Firm) are already fully independent — confirmed zero cross-imports in the Dependency Audit. Neither reads the other's env-var surface. This split is correct and requires no further decision. |
| **Logging** | Agent Firm (target state) | **Changes from today.** Currently Agent Firm's loggers are children of Production Engine's root logger by accident of Python's logging hierarchy (Architecture doc, Blocker 4). Target: Agent Firm configures its own logging explicitly (own handler, own redaction call, structurally identical JSON format to Production Engine's for operational consistency, but not dependent on Production Engine having run `setup_logging()` first). |
| **Metrics** | Split by domain | Agent Firm owns and computes all decision/provider metrics (cost, latency, success rate, circuit-breaker state — today's `providers/metrics.py::provider_stats()`). Production Engine owns system-level operational metrics (`/metrics` Prometheus endpoint, scheduler health, DB metrics) and **aggregates** Agent Firm's metrics into that endpoint by calling Agent Firm's metrics API — never by reading `agent_traces`/`provider_events` directly (that raw-SQL reach-through is exactly what AF-1's Data Access Layer eliminates). |
| **Health** | Production Engine owns the exposed surface; Agent Firm owns and reports its own component signal | `/health` stays Production Engine's endpoint and Production Engine's decision about what "healthy" means for the whole system. Agent Firm exposes one clear signal (e.g., "can I currently evaluate: yes / degraded / no, both providers down") that Production Engine's health check may incorporate — Production Engine does not compute Agent Firm's own health from Agent Firm's internals. |
| **Persistence (infrastructure)** | Production Engine | The physical SQLite file, the single `data.db.connect()` entry point, `busy_timeout`/WAL configuration, backup/restore — all infrastructure-level concerns stay exactly where they are today. This is unaffected by the schema-ownership decision below (see `AF1_SCHEMA_OWNERSHIP_DECISION.md`) — infrastructure ownership and schema/content ownership are different concerns. |
| **Database schema** | Split — see `AF1_SCHEMA_OWNERSHIP_DECISION.md` | Production Engine owns schema for its own operational tables (`scheduled_signals`, `paper_trades`, `watchlist_snapshot`, `_job_sentinel`, etc.). Agent Firm owns schema for `agent_decisions`/`agent_traces`/`provider_events` — full rationale in the dedicated decision document. |
| **Migrations** | Follows schema ownership | Whoever owns a table's schema owns that table's migration logic. Both still call through Production Engine's single `data.db.connect()` for the actual connection (Persistence row, above) — migration *logic* ownership and connection *infrastructure* ownership are orthogonal. |
| **Provider management** (Z.ai/Claude selection, circuit breaker, quota governor) | Agent Firm | Entirely internal to decision-making; Production Engine has no visibility into or control over which provider served a given evaluation, beyond the `providers_used` field already in `AgentDecision`. |
| **LLM routing** | Agent Firm | Same as Provider management — one concern, not two. |
| **Prompt orchestration** | Agent Firm | LangGraph graph structure, individual agent prompts, model selection per role. Entirely internal implementation, explicitly out of the stable interface per `AGENT_FIRM_INTERFACE_SPEC.md` §7. |
| **Evaluation** | Agent Firm | The whole point of the subsystem. |
| **Consensus** (bull/bear debate → risk manager → decision) | Agent Firm | Including the deterministic post-LLM guardrail override (`apply_guardrails`) — this is Agent Firm's own safety mechanism over its own output, not Production Engine's concern. |
| **Retry policy** | Agent Firm, exclusively | Agent Firm owns retry for its own provider calls. **Rule for Production Engine: never wrap `evaluate`/`evaluate_staged` in a caller-side retry loop.** Per the Interface Spec, a `degraded` decision means "not reviewed this cycle," not "worth retrying" — retrying at the call site would duplicate (and could conflict with) Agent Firm's own internal retry/failover logic. |
| **Caching** | Split by domain | Agent Firm owns its own evaluation-scoped caching (`reset_market_ctx()`'s per-scan-cycle cache). Production Engine owns its own unrelated caches (e.g., the macro-panic cache in `scheduler/scanner.py`, already confirmed safe in the Production Readiness Report). No shared cache exists or should exist between them. |

---

## Resolution Rule for Any Future Concern Not Listed Here

If a new concern arises that doesn't fit this table: **if it's about deciding what to do with a
signal, it's Agent Firm's; if it's about running the system that produces and acts on signals, it's
Production Engine's.** This is the Primary Principle restated as a test, not a new rule — apply it
before escalating to an owner decision.
