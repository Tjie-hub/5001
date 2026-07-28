# Agent Firm — Dependency Audit

**Date:** 2026-07-28
**Purpose:** Every dependency between the (now frozen, v1-released) Production Engine and Agent Firm
(`engine/agent_firm/`), classified so the eventual split knows exactly what has to move, what has to
stay, and what has to be re-architected in between. Every entry below is verified by direct grep/read
against the current repository — not inferred from naming or documentation.
**Classification key:** **Public API** (a call Production Engine makes that Agent Firm should keep
stable across its own versions) · **Internal implementation** (Agent Firm-owned code Production
Engine has no business reaching into, but currently does) · **Shared utility** (a Production-Engine-
owned helper Agent Firm currently imports directly) · **Tight coupling** (neither side can change
independently without breaking the other today) · **Technical debt** (works today, but is fragile or
undocumented as a boundary).

---

## 1. Production Engine → Agent Firm (forward dependencies)

| Call site | What it calls | Classification | Notes |
|---|---|---|---|
| `scheduler/jobs.py:780-781` (`run_premarket_firm_scan`) | `engine.agent_firm.firm.evaluate_staged()`, `engine.agent_firm.schemas.SignalCandidate` | **Public API** | Exactly the documented interface — see `AGENT_FIRM_INTERFACE_SPEC.md` |
| `scheduler/jobs.py:946-947` (`run_eod_trade_plan`) | same as above | **Public API** | Same call shape, different job |
| `scheduler/scanner.py:316,1345` | `engine.agent_firm.firm.reset_market_ctx()` | **Public API** | Documented lifecycle hook — must be called once per scan cycle |
| `scheduler/scanner.py:981-983, 1058-1060` | `firm.evaluate_staged()` / `evaluate()`, `config`, `SignalCandidate` | **Public API** | Main scanner integration point |
| `monitor.py:27-29` | `engine.agent_firm.config`, `engine.agent_firm.firm`, `SignalCandidate` | **Public API** (for the exit-veto check) | `monitor.py`'s `_agent_confirms_exit` — explicit fail-open on any exception, already verified sound in the Production Readiness Report |
| `routes/backtest.py:824,858` (`/api/agent/status`, `/api/agent/config`) | `engine.agent_firm.config.get_enabled()/get_enforce()/is_active()/MODEL_ID/set_mode()` | **Internal implementation reach-through** | Production Engine's web layer directly mutates and reads Agent Firm's live runtime config object — no API boundary, just a shared in-process module |
| `routes/backtest.py:877` (`/api/agent/audit`) | `engine.agent_firm.analytics.agent_agreement/cohort_summary/decision_log` | **Internal implementation reach-through** | Analytics functions built for Agent Firm's own reporting, called directly from Production Engine's Flask routes |
| `scheduler/scanner.py:1070`, `routes/backtest.py:835` | Raw SQL `SELECT ... FROM agent_decisions` | **Tight coupling** | Both sides read this table directly with hand-written SQL; no query function, no schema version, no API — a column rename in `agent_decisions` breaks both sides silently |
| `engine/trade_plan.py:389` (comment) | *(deliberately none)* | **Clean separation, by design** | `trade_plan.py`'s own comment: "Duck-typed (no agent_firm import)" — it consumes `AgentDecision`-shaped objects by attribute access, never imports the class. This is the one place in the codebase already built the *right* way for an eventual split. |
| `tests/test_premarket_firm_scan.py`, `tests/test_trade_plan.py`, `tests/test_scheduler_firm_hook.py`, `tests/test_agent_size_hint.py`, `tests/test_bear_watchlist_ranking.py`, `tests/test_monitor_exit_review.py`, `tests/test_nr7_live_pipeline_e2e.py` | Import `AgentDecision`/`SignalCandidate` directly to build fixtures; several monkeypatch `engine.agent_firm.firm`/`config` package attributes directly (`import engine.agent_firm as _pkg; monkeypatch.setattr(_pkg, "firm", ...)`) | **Tight coupling (test-layer)** | Production Engine's own test suite is coupled to Agent Firm's *internal* package attribute structure (not just its public functions) to make mocking work — a refactor of `engine/agent_firm/__init__.py`'s lazy-import pattern would break these tests even if `evaluate_staged()`'s signature never changed |

## 2. Agent Firm → Production Engine (reverse dependencies)

| Location | What it imports | Classification | Notes |
|---|---|---|---|
| `engine/agent_firm/analytics.py:8` | `data.db.connect` | **Shared utility, tight coupling** | Reads `agent_decisions`/`agent_traces` via the shared SQLite connection helper — same DB file, same process, no data API |
| `engine/agent_firm/tools/news_lookup.py:6`, `tools/sqlite_query.py:11` | `data.db.connect` | **Tight coupling** | These are LLM-callable tools — a live LLM agent has direct, unmediated SQL read access to the entire production database file through this path. Significant for any future process/service separation: this is not "call an API," it's "open the same file." |
| `engine/agent_firm/providers/events.py:61` | `data.db.connect` (lazy import) | **Shared utility, tight coupling** | Writes `provider_events` — same pattern as above, for the router's own telemetry |
| `engine/agent_firm/firm.py:445,460` | Raw SQL `INSERT OR REPLACE INTO agent_decisions` / `INSERT INTO agent_traces` | **Tight coupling** | The write side of the same tables `routes/backtest.py`/`scheduler/scanner.py` read directly (§1) — this is one shared, un-versioned schema owned by neither side exclusively |
| `engine/agent_firm/providers/alerts.py:16` | `utils.telegram.send_telegram` | **Shared utility** | Reuses the same, already-redaction-hardened Telegram sender Production Engine uses — this is actually a *good* dependency to keep, not one to break, once redaction is centrally available |
| `engine/agent_firm/config.py` | *(nothing from root `config.py`)* | **Clean separation, verified** | `engine/agent_firm/config.py` has its own independent `load_dotenv()` call and its own `os.getenv()` reads — confirmed zero imports from root `config.py`. Already fully independent on the configuration axis. |
| *(anywhere in `engine/agent_firm/`)* | `utils.logging_config` / `redact_secrets` | **Missing dependency — technical debt** | Zero direct usage found. `engine/agent_firm/providers/router.py` uses plain `logging.getLogger("agent_firm.providers.router")` — this only gets redaction and the JSON file handler because it's a *child logger of the root logger Production Engine's `app.py` configures at import time*. If Agent Firm ever runs as a separate process, this implicit inheritance disappears and Agent Firm's logs would be **unstructured and unredacted** unless it configures its own logging explicitly. |

## 3. Shared, Neither-Side-Owned Resources

| Resource | Owned by (today) | Written by | Read by | Risk |
|---|---|---|---|---|
| `agent_decisions` table | `data/db.py::init_agent_firm_tables()` (Production Engine's schema file) | `engine/agent_firm/firm.py` | `scheduler/scanner.py`, `routes/backtest.py`, `engine/agent_firm/analytics.py` | Schema lives in Production Engine's file; the only writer is Agent Firm; three different readers across both codebases with hand-written SQL and no shared query layer |
| `agent_traces` table | Same | `engine/agent_firm/firm.py` | `engine/agent_firm/analytics.py`, `engine/agent_firm/providers/metrics.py`, `engine/agent_firm/providers/router.py` | Same schema-ownership split, though all *readers* here happen to already be inside Agent Firm — the least-coupled of the three shared tables |
| `provider_events` table | Same | `engine/agent_firm/providers/events.py` | `engine/agent_firm/providers/metrics.py` | Same pattern; entirely internal to Agent Firm on the read side today |
| `scheduled_signals.agent_decision_id` | `data/db.py` (FK column added via migration) | Production Engine scheduler code | — | A foreign key from a Production Engine table into `agent_decisions` — the one place the *schema itself* (not just runtime code) encodes cross-subsystem coupling |
| SQLite file (`data/walkforward.db`) itself | Production Engine (`data/db.py::connect()`) | Both | Both | The most fundamental coupling: there is currently no concept of "Agent Firm's data" as distinct from "Production Engine's data" — it's one file, one connection helper, one process |
| Root logger configuration | Production Engine (`app.py` calls `utils.logging_config.setup_logging()`) | — | Agent Firm's loggers (implicitly, via propagation) | See §2 — Agent Firm has no logging setup of its own |
| `security/route_policy.py` classification of `/api/agent/*` routes | Production Engine | — | — | `/api/agent/status`/`/api/agent/audit` (VIEWER), `/api/agent/config` (ADMIN) — Agent Firm's control surface is classified and gated entirely by Production Engine's auth system, with no independent notion of "who can operate Agent Firm" |

## 4. What Is Already Clean (worth preserving as the model for everything else)

- **`engine/trade_plan.py`'s duck-typed consumption of `AgentDecision`** — no import, attribute access
  only. This is exactly the pattern the rest of the boundary should converge toward.
- **`engine/agent_firm/config.py`'s complete independence from root `config.py`** — already has its
  own env-loading, already portable.
- **External library dependencies are fully self-contained** — `langgraph`, `openai`, `pydantic`,
  `httpx`, `subprocess` (Claude CLI) are all Agent-Firm-only; no shared version constraints with
  Production Engine's own dependency set beyond what's already in one `requirements.txt`.

## 5. Summary Table

| Category | Count | Examples |
|---|---|---|
| Public API (stable, worth preserving as-is) | 5 call sites | `evaluate_staged()`, `evaluate()`, `reset_market_ctx()`, `_agent_confirms_exit`'s fail-open pattern |
| Internal implementation reach-through | 3 routes | `/api/agent/status`, `/api/agent/config`, `/api/agent/audit` |
| Shared utility (acceptable to keep) | 2 | `utils.telegram.send_telegram`, external libs |
| Tight coupling (must be resolved before independent release) | 6 | `agent_decisions`/`agent_traces`/`provider_events` raw-SQL access from both sides, direct DB-file access from LLM tools, test-layer package-attribute monkeypatching |
| Technical debt (works, but fragile) | 2 | implicit root-logger dependency, no data-versioning on the shared schema |

This audit is the evidence base for `AGENT_FIRM_ARCHITECTURE.md`'s blocker list and
`AGENT_FIRM_MIGRATION_PLAN.md`'s stay/move recommendations.
