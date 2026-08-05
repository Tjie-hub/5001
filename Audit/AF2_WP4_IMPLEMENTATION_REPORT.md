# AF-2 Work Package 4 (ADR-AF-002 Completion & Hardening) — Implementation Report

**Date:** 2026-07-29
**Basis:** `docs/agent_firm/ADR-AF-002-CONTEXT_OWNERSHIP.md`, `Audit/AF2_WP1_IMPLEMENTATION_REPORT.md`
(Foundation), `Audit/AF2_WP2_IMPLEMENTATION_REPORT.md` (Producer Migration — scanner.py wiring),
`Audit/AF2_WP3_IMPLEMENTATION_REPORT.md` (Specialist Consumption Migration).
**Scope, as briefed:** audit remaining ADR-AF-002 technical debt; complete remaining
scheduler/Agent-Firm integration; remove obsolete compatibility code only where every caller has
migrated; validate; certify. No research code, no schema/DB migration, no architecture expansion
beyond ADR-AF-002, backward compatibility preserved for any caller not migrated in this change.

**A note on "WP4" numbering:** `docs/agent_firm/AF2_WORK_PACKAGE_SEQUENCE.md` defines its own
"WP4" as `ConsensusContext` + guardrail vetoes — a different, earlier planning pass that predates
the actual delivered re-scoping into WP1 (Foundation) / WP2 (Producer Migration) / WP3 (Consumption
Migration). That document is stale against what was actually built (per this repo's own Decision-
Making Hierarchy: a document's status claim yields to the actual repository state). This session's
WP4 is the natural continuation of the WP1→WP2→WP3 sequence actually delivered, per this session's
own mission brief — not a re-run of `AF2_WORK_PACKAGE_SEQUENCE.md`'s WP4. Flagged here rather than
silently reconciled.

---

## Summary of Findings and Actions

The Task 1 audit (`Audit/AF2_WP4_TECHNICAL_DEBT_REPORT.md`) found one item requiring code changes
beyond documentation: **two live, scheduled production call sites that construct `SignalCandidate`
and call the Agent Firm without ever attaching Tier 1 context**, plus **one live intraday call
site** with the same gap — none of these were covered by WP2's producer-wiring pass, which only
reached `scheduler/scanner.py`'s two construction sites. This is the single most significant
finding of this work package and is the majority of the code change below.

| Call site | Job / trigger | Status before WP4 | Status after WP4 |
|---|---|---|---|
| `scheduler/scanner.py::run_agent_firm_gate()` | Intraday multi-strategy scan | Tier 1 context wired (WP2) | Unchanged — already correct |
| `scheduler/scanner.py::rank_bear_watchlist_and_notify()` | Intraday bear-watchlist ranking | Tier 1 context wired (WP2) | Unchanged — already correct |
| `scheduler/jobs.py::run_premarket_firm_scan()` | 08:35 WIB daily job | **No context — every field None** | Wired this WP |
| `scheduler/jobs.py::run_eod_trade_plan()` | 16:40 WIB daily job | **No context — every field None** | Wired this WP |
| `monitor.py::_agent_confirms_exit()` | Intraday exit-review, every ~30 min | **No context — every field None** | Wired this WP |

Practically, this means: since WP3 shipped, every candidate evaluated by the premarket shortlist,
the EOD trade plan, and the exit-review gate has reached the Technical/Flow/Regime/News specialists
with `technical`/`flow`/`regime_context`/`news` all at their `None`→typed-default fallback — every
one of those four analysts has been returning its "insufficient data"/`NEUTRAL`/`UNKNOWN` degraded
response for every candidate from these three call sites, and the Risk Manager has never seen
`portfolio`/`risk_limits` for them either. Only the intraday multi-strategy scan gate and the bear-
watchlist ranking (`scanner.py`'s two sites) were receiving real Tier 1 context. This is a
functional correctness gap in production, not merely unfinished plumbing — see `Audit/
AF2_WP4_CALL_GRAPH_REPORT.md` for the full before/after call graph.

---

## Files Changed

| File | Nature of change |
|---|---|
| `scheduler/jobs.py` | `run_premarket_firm_scan()` and `run_eod_trade_plan()` each gain a context-population step — identical pattern to `scanner.py`'s WP2 wiring — before `SignalCandidate` construction; each also now flushes `reset_market_ctx()`/`reset_batch_context()` at its own start (see "Cache Lifecycle" below); `run_premarket_firm_scan()`'s duplicate `get_market_risk_for_circuit_breaker()` call (previously computed twice — once implicitly needed for context, once for the Telegram summary) is consolidated into one call, reused for both |
| `monitor.py` | `_agent_confirms_exit()` gains the same context-population step before its single-candidate `SignalCandidate` construction, with its own cache-flush (see below) |
| `engine/agent_firm/firm.py` | Removed one genuinely dead import (`import time`, unused since before WP1-3 — found by the Task 1 unused-import sweep, safe zero-behavior-change deletion) |
| `tests/test_scheduler_jobs_context_wiring.py` | New — integration tests verifying `run_premarket_firm_scan()`/`run_eod_trade_plan()` populate Tier 1 context (happy path + fail-open on a broken/empty context DB), mirroring `tests/test_agent_firm_context_wiring.py`'s structure |
| `tests/test_monitor_exit_review.py` | New context-population test; `DB_PATH` pinned to `":memory:"` in the existing `_call_confirms()` helper and the `check_all_open_trades()` end-to-end test (hermeticity fix, see below); one module-level pre-import added (see "A Windows Test-Ordering Fragility Found and Fixed" below) |

**Not touched:** `scheduler/scanner.py` (already correctly wired by WP2 — confirmed by direct read,
no gap found), `engine/agent_firm_context.py` (the Tier 1 builders themselves — reused as-is, zero
changes), `engine/agent_firm/schemas.py`, any prompt, any analyst/consensus/risk logic, any database
schema, `research/`.

---

## Cache Lifecycle for the Three Newly-Wired Call Sites

`scanner.py`'s `scheduled_multi_strategy_scan()` flushes both `reset_market_ctx()` (legacy, inert)
and `reset_batch_context()` (the real Tier 1 batch-level cache — `MarketContext`/`PortfolioContext`/
`RiskContext`/`ExecutionContext`) exactly once per its own scan cycle, before any candidate context
is built. `scheduler/jobs.py`'s two jobs and `monitor.py`'s exit-review check do **not** run inside
that scan cycle — they are independently scheduled/triggered. Without their own reset, the batch-
level cache (a process-global, per ADR-AF-002's stated lifecycle) would silently carry over
whatever the last invocation of *any* of these five call sites computed, potentially hours stale,
into a job that has no relationship to that prior invocation. Each of the three newly-wired call
sites therefore now flushes both caches immediately before building its own context, treating its
own invocation as its own "scan cycle" for Tier 1 batch-level purposes — this is the same rule
ADR-AF-002 already states, applied at the correct granularity for jobs that don't share the
intraday scan's cycle boundary.

---

## A Test-Hermeticity Gap Found and Closed (mirrors WP2's own precedent)

`_agent_confirms_exit()` previously never opened a database connection — a pure in-memory
`SignalCandidate` construction plus a call to the (mockable) `firm.evaluate()`. Wiring in
`build_candidate_context()` necessarily adds a real `db_connect(DB_PATH)` call.
`tests/test_monitor_exit_review.py`'s existing tests only ever mocked `engine.agent_firm.firm`/
`engine.agent_firm.config` — none patched `monitor.DB_PATH`, so left unpatched they would have
started silently opening the real, gitignored `data/walkforward.db` on every run, exactly what
CLAUDE.md's Testing section states the suite must never do. **Fixed** by pinning `monitor.DB_PATH`
to `":memory:"` in the existing `_call_confirms()` helper and in
`test_check_all_open_trades_r4_agent_veto_skips_close` — identical fix shape to WP2's own
`scanner.DB_PATH`/`paper_trade.DB_PATH` pinning.

## A Windows Test-Ordering Fragility Found and Fixed

Wiring `build_candidate_context()` into `_agent_confirms_exit()` also means `monitor.py` now
lazily imports `engine.agent_firm_context` (which imports `pandas`) for the first time, at call
time, inside a test function body. On this Windows `.winvenv` environment, a **first-ever**
`pandas`/`numpy` import performed **after** `tests/agent_firm/test_firm.py`'s `importlib.reload()`
calls (used there to re-exercise `config`/`firm` under different env vars) have already run in the
same pytest process fails with `ImportError: cannot load module more than once per process` — a
numpy C-extension guard against being unloaded and reloaded, not a logic defect. Confirmed by direct
reproduction (see session trace): the identical `build_candidate_context()` call succeeds without
issue in `tests/test_scheduler_jobs_context_wiring.py`, which imports `engine.agent_firm_context` at
**module level** — collected before any test's `importlib.reload()` runs at runtime — while
`test_monitor_exit_review.py` only referenced it lazily inside `_agent_confirms_exit`, so its first
import happened at runtime, after `test_firm.py`'s reloads. **Fixed** by adding one module-level
`import engine.agent_firm_context` to `test_monitor_exit_review.py`, mirroring the file's own
existing `import engine.agent_firm.schemas` pre-import (added previously for an analogous lazy-
attribute reason) and matching the pattern the new jobs-context test file already used. This is a
test-only fix — no production code path is affected, since production processes never call
`importlib.reload()` on these modules at runtime.

---

## Architectural Compliance

| Requirement (from the WP4 mission brief) | Compliance |
|---|---|
| No research code modifications | **Met** — zero files under `research/` touched; verified by `git diff --stat` scope |
| No database/schema migrations | **Met** — no `CREATE TABLE`/`ALTER TABLE`/schema change anywhere in this change |
| No architectural expansion beyond ADR-AF-002 | **Met** — the fix reuses `engine.agent_firm_context.build_candidate_context()` verbatim (already-approved WP1/WP2 code), applying the exact pattern `scanner.py` already used; no new context object, no new builder, no new agent |
| Preserve backward compatibility unless every caller is migrated | **Met** — `reset_market_ctx()` retained (2 non-production dev scripts still call it directly — see Technical Debt Report); every touched function's own external call signature/contract is unchanged |
| Focus on scheduler/scanner and Agent Firm integration | **Met** — `scheduler/jobs.py` (2 sites) + `monitor.py` (1 site, immediately adjacent to the same integration surface); `scheduler/scanner.py` itself required no change (confirmed already correct) |
| No new features / no redesign | **Met** — the change closes a wiring gap using existing, already-shipped machinery; no new Agent Firm behavior, decision logic, or context type was introduced |

---

## Test Results

Run via the Windows checkout's `.winvenv` interpreter (`DB_PATH=data/walkforward.db
.winvenv/Scripts/python.exe -m pytest ...`).

| Suite | Result |
|---|---|
| `tests/agent_firm/` (excl. `providers/`) + `tests/test_agent_firm_context.py` + `tests/test_agent_firm_context_wiring.py` + `tests/test_scheduler_jobs_context_wiring.py` (new) + `tests/test_monitor_exit_review.py` + `tests/test_scheduler_firm_hook.py` + `tests/test_agent_size_hint.py` + `tests/test_bear_watchlist_ranking.py` + `tests/test_nr7_live_pipeline_e2e.py` + `tests/test_premarket_firm_scan.py` + `tests/test_eod_trade_plan_job.py` | **246 passed** |
| `tests/test_architecture_boundary.py`, `test_research_data_fence.py`, `test_db_centralization.py`, `security/test_route_policy.py` | **13 passed** — no boundary/fence/route regression |
| Full suite, `pytest -q --ignore=tests/agent_firm/providers` | **1564 passed, 44 failed, 9 errors** (575s) — **identical 44-failed/9-error set to the WP3 baseline** (same files, same categories — see `Audit/AF2_WP4_FINAL_CERTIFICATION.md` for the full comparison); **+4 passed vs. WP3's 1560**, exactly the 4 new tests this work package added |

No new failure, no new error, anywhere in the full suite.

---

## Known Limitations (deliberate WP4 scope boundaries, not defects)

1. **`reset_market_ctx()` is not removed.** Blocked by two non-production developer scripts
   (`scripts/probe_actual_http_concurrency.py`, `scripts/replay_firm_offline_run.py`) that still
   call it directly. See `Audit/AF2_WP4_TECHNICAL_DEBT_REPORT.md` for the full analysis and the
   proposed minimal follow-up.
2. **`ConsensusContext` remains unbuilt**, carried forward unchanged from WP2/WP3's own Known
   Limitations — no builder, no attach point, out of this work package's mandate (would be a new
   Tier 2 feature, not a completion of already-shipped Tier 1 wiring).
3. **Unrelated pre-existing dead code found but not touched**: `scheduler/jobs.py`'s unused
   `_load_ohlcv_bulk` import and `scheduler/scanner.py`'s unused `sqlite3`/`_sqlite3` imports (both
   pre-date WP1-3, unrelated to Agent Firm context work, and touching them would be an out-of-mandate
   change in shared production files). Flagged in the Technical Debt Report, not fixed here.
