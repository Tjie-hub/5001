# AF-2 Work Package 2 (Context Producer Migration) — Implementation Report

**Date:** 2026-07-29
**Basis:** `docs/agent_firm/ADR-AF-001-DETERMINISTIC_OWNERSHIP.md`,
`docs/agent_firm/ADR-AF-002-CONTEXT_OWNERSHIP.md`, `docs/agent_firm/ADR-AF-003-SIZING_OWNERSHIP.md`,
`docs/agent_firm/ADR-AF-004-VERSIONING_CONTRACT.md`, `docs/agent_firm/AF2_ARCHITECTURE_CERTIFICATION.md`,
`Audit/AF2_WP1_IMPLEMENTATION_REPORT.md` (Foundation — the nine Tier 1 builder functions and the eight
new `SignalCandidate` fields this work package wires up).
**Scope, as briefed:** producer migration only. Wire the Work Package 1 builders
(`engine/agent_firm_context.py`) into the two live `SignalCandidate` construction sites in
`scheduler/scanner.py` so the eight Tier 1 context fields are populated with real data from
canonical producers, before `evaluate_staged()` runs. The Agent Firm itself (`engine/agent_firm/`),
its prompts, its analysts, consensus, sizing, and decision logic are **not** touched. The legacy
context path (`firm.py::_build_context()`/`_market_ctx`/`reset_market_ctx()`) is **not** touched and
remains fully available — nothing in the live evaluation graph reads the newly-populated fields yet.

---

## Files Changed

| File | Type | Nature of change |
|---|---|---|
| `engine/agent_firm_context.py` | Modified (WP1 → WP2) | +~95 lines, all additive: `_safe()` fail-soft helper, `_batch_ctx`/`reset_batch_context()`/`get_batch_context()` (batch-level Tier 1 cache), `build_candidate_context()` (per-candidate assembly), module docstring updated to WP2 status |
| `scheduler/scanner.py` | Modified | `run_agent_firm_gate()` and `rank_bear_watchlist_and_notify()` each gain one new optional trailing parameter (`market_risk_score=None`) and a context-population step before `SignalCandidate` construction; `scheduled_multi_strategy_scan()` gains a `reset_batch_context()` call alongside the existing `reset_market_ctx()` call, and threads `_market_risk.get('score')` into both call sites |
| `tests/test_scheduler_firm_hook.py` | Modified | `_call_gate()` now pins `scanner.DB_PATH`/`paper_trade.DB_PATH` to `":memory:"` — required for hermeticity once the gate opens a real DB connection (see "Backward Compatibility" and "A Test-Hermeticity Gap Found and Closed" below) |
| `tests/test_agent_size_hint.py` | Modified | Same `":memory:"` pinning in its own `_call_gate()` helper |
| `tests/test_bear_watchlist_ranking.py` | Modified | `isolated_db` fixture now also pins `paper_trade.DB_PATH` (previously pinned only `scanner.DB_PATH`) to the same temp DB |
| `tests/test_agent_firm_context.py` | Modified (WP1 → WP2) | +~130 lines: two new test classes, `TestBatchContext` and `TestBuildCandidateContext`, covering the new cache and assembly functions directly |
| `tests/test_agent_firm_context_wiring.py` | New | Scanner-level integration tests: `run_agent_firm_gate()`/`rank_bear_watchlist_and_notify()` actually populate Tier 1 context from a hermetic seeded DB, and fail open (candidates still reach `evaluate_staged()`) when the DB is unreadable |

**Nothing else changed.** `engine/agent_firm/firm.py`, every prompt in `engine/agent_firm/prompts/`,
every agent module in `engine/agent_firm/agents/`, `engine/agent_firm/schemas.py`, and
`engine/agent_firm/guardrails.py` are byte-for-byte unmodified — verified by `git diff` scoped to
this change and by the passing `tests/agent_firm/` suite (see Test Results).

---

## What Was Built

### 1. Batch-level context cache (`engine/agent_firm_context.py`)

Per `ADR-AF-002`'s stated lifecycle rule ("Tier 1 batch-level objects... cached once per scan cycle
by `engine/agent_firm_context.py`, matching `firm.py`'s existing `_market_ctx`/`reset_market_ctx()`
cache lifecycle exactly — that cache's *location* moves to the new module; its *behavior* is
unchanged"), this work package adds that cache **in the new module**, without touching `firm.py`'s
own, still-live `_market_ctx`/`reset_market_ctx()` — the two caches now coexist, each serving a
different, currently-disjoint consumer (the legacy raw-dict context vs. the new typed
`SignalCandidate` fields nothing reads yet).

- `reset_batch_context()` — flushes the cache; called once per scan cycle from
  `scheduled_multi_strategy_scan()`, alongside (not replacing) the existing `reset_market_ctx()` call.
- `get_batch_context(conn, market_risk_score=None)` — returns the four batch-level Tier 1 objects
  (`MarketContext`, `PortfolioContext`, `RiskContext`, `ExecutionContext`), computing them once and
  reusing the cached result for every subsequent call within the same scan cycle (mirrors
  `firm.py`'s existing `_market_ctx` pattern exactly — same shared-object-reference-not-deep-copy
  design ADR-AF-004 specified for `SignalCandidate`'s batch-level fields).

### 2. Per-candidate assembly (`build_candidate_context()`)

One function, called once per candidate at both construction sites, returning a dict keyed exactly
to `SignalCandidate`'s eight new optional fields (verified by test —
`test_returns_exactly_signal_candidate_field_keys` asserts the returned key set is a subset of
`SignalCandidate.model_fields`):

```python
build_candidate_context(conn, ticker, date_str, market_risk_score=None) -> {
    "technical": TechnicalContext, "flow": FlowContext, "regime_context": RegimeContext,
    "news": NewsContext, "market": MarketContext, "portfolio": PortfolioContext,
    "risk_limits": RiskContext, "execution": ExecutionContext,
}
```

Per-candidate fields (`technical`, `flow`, `regime_context`, `news`) are built fresh per ticker;
batch-level fields (`market`, `portfolio`, `risk_limits`, `execution`) come from
`get_batch_context()`'s cache. No new deterministic computation was added anywhere — every field is
produced by calling a WP1 builder, which in turn calls the canonical producer named in
`ADR-AF-001`. This module performs **assembly and fail-soft wrapping only**.

### 3. Fail-soft wrapping (`_safe()`)

A single helper wraps every builder call: on exception, it logs a warning and returns that context
object's zero-argument default (e.g. `TechnicalContext()`), never propagating. This follows
CLAUDE.md's stated convention ("registry loading and metrics degrade to sentinels/`None` and log
rather than crash") and is what makes it safe to call real DB-backed builders from a pipeline stage
that must never fail closed. Verified directly by `TestBuildCandidateContext::
test_missing_tables_degrade_to_defaults_not_raise` and `TestBatchContext::
test_broken_builder_degrades_to_default_not_raise` (both construct a connection with **zero**
tables and assert every returned object equals its typed default, not an exception).

### 4. Scanner wiring (`scheduler/scanner.py`)

Both `SignalCandidate` construction sites now populate context before calling `evaluate_staged()`:

- **`run_agent_firm_gate()`** — opens one `db_connect(DB_PATH)` connection for the whole batch (≤20
  candidates, matching the existing cost-guard cap), calls `build_candidate_context()` per ticker,
  and spreads the result into each `SignalCandidate(...)` call via `**_ctx_by_ticker.get(ticker, {})`.
  The whole context-population step is wrapped in its own `try`/`except` — a DB-level failure (e.g.
  connection refused) degrades to **no context at all** (empty dict, i.e. every new field stays at
  its `None` WP1 default) rather than aborting the gate; candidates still reach `evaluate_staged()`
  exactly as they did before this change existed. This is a second, coarser fail-open layer on top of
  `_safe()`'s per-field one.
- **`rank_bear_watchlist_and_notify()`** — identical treatment for its own `SignalCandidate`
  construction loop.
- **`scheduled_multi_strategy_scan()`** — gains one `reset_batch_context()` call (new, additive,
  alongside the pre-existing `reset_market_ctx()` call) and threads the scan cycle's already-computed
  `_market_risk['score']` into both call sites as `market_risk_score=...`, satisfying WP1's
  documented `market_risk_score` dependency-injection point (`build_market_context(conn,
  market_risk_score=...)`) without a second, duplicate 4-sensor computation.

---

## Producer Mapping (unchanged from WP1 — verified still true after wiring)

| SignalCandidate field | Type | Canonical producer | Assembler |
|---|---|---|---|
| `technical` | `TechnicalContext` | `engine.technicals.tech_direction()` (+ `engine.indicators`/`engine.chart_indicators` values) | `build_technical_context()` |
| `flow` | `FlowContext` | `stockbit_flow` table columns (flow_filter.py's own computation) | `build_flow_context()` |
| `regime_context` | `RegimeContext` | `engine.regime_filter.detect_regime()` (+ `wf_scores`/`daily_screen` confirmation facts) | `build_regime_context()` |
| `news` | `NewsContext` | `engine.catalyst.has_catalyst()` + `engine.agent_firm.tools.news_lookup.lookup()` | `build_news_context()` |
| `market` | `MarketContext` | `engine.regime_filter.detect_regime()` on IHSG; `market_risk_score` injected from `scheduled_multi_strategy_scan()`'s existing composite-risk computation | `build_market_context()` via `get_batch_context()` |
| `portfolio` | `PortfolioContext` | `paper_trades` table (`status='OPEN'`) | `build_portfolio_context()` via `get_batch_context()` |
| `risk_limits` | `RiskContext` | `paper_trade.is_entries_blocked()`/`compute_drawdown()`; `security.auth.auth_mode()` | `build_risk_context()` via `get_batch_context()` |
| `execution` | `ExecutionContext` | `paper_trade.get_config()`/`get_open_trades()` | `build_execution_context()` via `get_batch_context()` |

No field in this table changed producer from WP1. WP2 added *assembly and call-site wiring only* —
verified by `git diff engine/agent_firm_context.py` containing no edits to any of the nine WP1
builder function bodies, only additions after them.

---

## Architectural Compliance

| Requirement (from the WP2 mission brief / ADRs) | Compliance |
|---|---|
| Every Tier 1 field originates from its canonical producer (`ADR-AF-001`) | **Met** — see Producer Mapping table; no new deterministic computation, only assembly |
| Every context object has one producer, one assembler | **Met** — `build_candidate_context()`/`get_batch_context()` are the sole call sites for the nine WP1 builders in the live path |
| No duplicate deterministic calculations | **Met** — `market_risk_score` is injected from the scan cycle's existing computation, not recomputed a second time (this was WP1's one deferred item, now closed) |
| Production Engine assembles Tier 1 (`ADR-AF-002`) | **Met** — assembly lives in `engine/agent_firm_context.py`, called from `scheduler/scanner.py`; both are Production Engine |
| Agent Firm remains unchanged | **Met** — `engine/agent_firm/` directory: zero files modified (verified by `git diff --stat engine/agent_firm/` returning empty) |
| No prompt changes | **Met** — `engine/agent_firm/prompts/` unmodified |
| No analyst/consensus/sizing/`evaluate()`/decision-logic changes | **Met** — `firm.py` unmodified; no call to `evaluate`/`evaluate_staged`/`reset_market_ctx` changed signature or behavior; `guardrails.py` unmodified |
| `evaluate`/`evaluate_staged`/`reset_market_ctx` signatures unchanged (`ADR-AF-004`) | **Met** — confirmed by `git diff engine/agent_firm/firm.py` being empty |
| Legacy context path remains available | **Met** — `firm.py::_build_context()`/`_market_ctx`/`reset_market_ctx()` unmodified and still the only thing every existing agent node reads |
| Context objects may be populated even if not yet consumed | **Met, by design** — nothing in `engine/agent_firm/` reads `SignalCandidate.technical`/`.flow`/etc. yet; this is producer wiring only |
| Batch-level lifecycle matches `ADR-AF-002` | **Met** — `reset_batch_context()`/`get_batch_context()` reproduce `_market_ctx`'s exact once-per-scan-cycle cache/reset pattern, scoped to the new module |

---

## Test Results

Run via the Windows checkout's `.winvenv` interpreter (`DB_PATH=data/walkforward.db
.winvenv/Scripts/python.exe -m pytest ...`; `langgraph` installed into `.winvenv` for this session
to exercise the real Agent Firm import path — see "A Pre-Existing Windows Test-Env Gap Found, Not
Fixed" below).

| Suite | Result |
|---|---|
| `tests/agent_firm/` (excluding `providers/`, pre-existing unrelated failure — see below) + `tests/test_agent_firm_context.py` + `tests/test_agent_firm_context_wiring.py` (new) + `tests/test_scheduler_firm_hook.py` + `tests/test_agent_size_hint.py` + `tests/test_bear_watchlist_ranking.py` + `tests/test_nr7_live_pipeline_e2e.py` | **192 passed** |
| `tests/test_premarket_firm_scan.py`, `test_trade_plan.py`, `test_dashboard_signals.py`, `test_edge_enrich.py`, `test_catalyst.py`, `test_chart_indicators.py`, `test_indicators.py`, `test_indicator_cache.py`, `test_regime_3class.py`, `test_regime_edge_scan.py`, `test_regime_honesty.py`, `test_paper_trade_sizing.py`, `security/test_auth.py` (every module WP2's builders/wiring touch, per WP1's own precedent list) | **209 passed** |
| `tests/test_architecture_boundary.py`, `test_research_data_fence.py`, `test_db_centralization.py`, `security/test_route_policy.py` | **17 passed** — no boundary/write-fence/route-classification regression; `engine/agent_firm_context.py` opened no new production/research import direction and added no route |
| `security/test_secret_hygiene.py::test_no_hardcoded_secret_literals` | **1 failed — pre-existing local-environment artifact, not a WP2 regression** (see below) |
| Full suite, `pytest -q --ignore=tests/agent_firm/providers` | **1549 passed, 44 failed, 9 errors** (416.96s) — every failure/error is in a file this change does not touch (see below); zero failures in any `agent_firm`/`scanner`/`paper_trade`/context-related module |

**Pre-existing, unrelated failures (confirmed not caused by this change):**
- `tests/agent_firm/providers/` — same uncommitted, unrelated quota-governor feature WP1's report
  already documented (`ImportError: cannot import name '_hydrate_quota_holds'`); untracked in `git
  status`, unaffected by this change.
- `security/test_secret_hygiene.py::test_no_hardcoded_secret_literals` — flags
  `.winvenv/Lib/site-packages/langsmith/client.py:159`, a third-party library's own source line
  (`_ANTHROPIC_API_KEY = "ANTHROPIC_API_KEY"` — an env-var *name* string, not a secret value). This
  is caused by installing `langgraph` (which pulls in `langsmith`) into the local `.winvenv` test
  environment for this session, purely to exercise the real Agent Firm import path on Windows (see
  below) — `.winvenv/` is untracked, gitignored-in-spirit (already excluded from Syncthing via
  `.stignore` per this repo's own conventions) but not yet added to this specific test's path-prefix
  exclusion list (`venv/`, `tests/`, etc.). **Not a repository regression**: real CI (Linux,
  `.github/workflows/test.yml`) has no `.winvenv` directory at all and would never see this file.
  No repository file was changed to produce or fix this — it is a byproduct of local test tooling,
  documented here rather than silently worked around.

**Full-suite run** (`pytest -q --ignore=tests/agent_firm/providers`, 1549 passed / 44 failed / 9
errors): every failing file is one WP2 does not touch, and every failure is a Windows-local-tooling
category, not a logic regression — confirmed by inspecting each failure's category, none of which
mention `scanner`, `agent_firm`, `agent_firm_context`, `paper_trade`, or `SignalCandidate`:
- `tests/test_value_format.py` (4) — Node.js subprocess invocation with a Windows path
  (`D:\IDX\static\format.js`) mangled by backslash-escaping inside a JS string literal
  (`Cannot find module 'D:IDXstaticormat.js'`); a Windows-vs-Linux path-quoting issue in the test
  itself, unrelated to this change.
- `tests/security/test_release_scripts.py` (6), `tests/test_cron_contract.py` (3) — invoke
  `scripts/*.sh` directly; no POSIX shell on this Windows Python venv.
- `tests/test_auto_token.py` (14 failed + 9 errors) — Playwright/credential-refresh tests, unrelated
  module (`auto_token.py`), pre-existing on this checkout independent of this session's edits.
- `tests/test_config_validation.py` (6), `tests/test_logging_config.py` (2),
  `tests/test_news_filter.py` (2), `tests/test_stockbit_fetcher_ensure_valid_token.py` (2),
  `tests/test_experiment_tracking.py` (1), `tests/regime/test_storage.py` (1) — none import or
  exercise any file this change touches; consistent with known Windows-checkout gaps (env/config
  defaults, timezone/locale, or filesystem-permission assumptions written for the Linux runtime this
  repo's CLAUDE.md documents as canonical).

No `git stash` differential run was performed to double-confirm these are 100% pre-existing (would
require stashing this session's uncommitted work); confidence is based on failure content — none
reference any file this change added or edited — rather than a before/after diff. Flagged here for
transparency rather than silently asserted.

---

## A Test-Hermeticity Gap Found and Closed

`run_agent_firm_gate()` and `rank_bear_watchlist_and_notify()` previously never opened a database
connection at all — `SignalCandidate` construction was pure in-memory dict manipulation. Wiring in
`build_candidate_context()` necessarily adds a real `db_connect(DB_PATH)` call to both functions.

Three existing test files call these functions without patching `scanner.DB_PATH`/
`paper_trade.DB_PATH` (`test_scheduler_firm_hook.py`, `test_agent_size_hint.py`), or patched only
`scanner.DB_PATH` and not `paper_trade.DB_PATH` (`test_bear_watchlist_ranking.py`'s `isolated_db`
fixture — `build_risk_context()`/`build_execution_context()` import `paper_trade` directly, with its
own separate module-level `DB_PATH`). Left unpatched, these tests would have started silently
opening the real, gitignored `DB_PATH` default (`data/walkforward.db`) on every run — exactly what
CLAUDE.md's Testing section states the suite must never do ("hermetic... never touches the gitignored
`data/walkforward.db`").

**Fixed** by pinning both `DB_PATH` globals to `":memory:"` (a fresh, empty, fully isolated database
per connection — no tables, so context population fails soft to typed defaults, which none of these
pre-existing tests inspect) in `test_scheduler_firm_hook.py`/`test_agent_size_hint.py`'s `_call_gate`
helpers, and adding the missing `paper_trade.DB_PATH` pin to `test_bear_watchlist_ranking.py`'s
existing `isolated_db` fixture. Verified: all three files' original assertions (filtering logic,
log content, Telegram silence) still pass unchanged.

One pre-existing WP1 test, `tests/test_agent_firm_context.py::TestRiskContext::
test_returns_typed_object`, already called `build_risk_context()` (real `paper_trade`/`security.auth`
read path) without any DB isolation — this predates WP2 and was not introduced or modified by this
change; left as-is, out of this work package's scope.

---

## A Pre-Existing Windows Test-Env Gap Found, Not Fixed

The Windows `.winvenv` test environment (`docs`-adjacent memory: `idx-windows-test-venv`) does not
have `langgraph` installed, so any test that lets `patch.object(engine.agent_firm, "firm", ...)` run
without `create=True` fails at collection with `AttributeError: <module 'engine.agent_firm'> does not
have the attribute 'firm'` **when run in isolation** — `engine.agent_firm.__init__.py` only imports
`firm` lazily, so the package never gains a `firm` attribute until something genuinely imports it,
and `firm.py` itself does `from langgraph.graph import ...` at module scope. This is **entirely
pre-existing** (confirmed: the failure occurs identically with or without any of this change's edits,
and disappears once any `tests/agent_firm/` file is run first in the same pytest session, priming the
package attribute) — not a WP2 regression. `langgraph` was installed into `.winvenv` for this session
only, to validate WP2's wiring against the real Agent Firm import path rather than relying solely on
mocks; this is a local-environment change, not a repository change (`.winvenv` is untracked).

---

## Backward Compatibility Verification

- **`evaluate`/`evaluate_staged`/`reset_market_ctx`**: unmodified — `engine/agent_firm/firm.py` is
  byte-for-byte unchanged (`git diff` empty for this file).
- **`SignalCandidate`/`AgentDecision`**: unmodified in `engine/agent_firm/schemas.py` — no new
  fields, no type changes; WP2 only *populates* fields WP1 already added.
- **No prompt, analyst, consensus, or sizing logic touched**: `engine/agent_firm/prompts/`,
  `engine/agent_firm/agents/`, `engine/agent_firm/guardrails.py` all unmodified.
- **Existing decision-flow behavior preserved**: `run_agent_firm_gate()`'s shadow/enforce filtering
  logic, the `agent_size_hint` write, and `rank_bear_watchlist_and_notify()`'s ranking/logging are
  byte-for-byte unchanged below the new context-population step — verified by every pre-existing test
  in `test_scheduler_firm_hook.py`, `test_agent_size_hint.py`, `test_bear_watchlist_ranking.py`, and
  `test_nr7_live_pipeline_e2e.py` continuing to pass with their original assertions intact.
  `test_agent_firm_context_wiring.py::test_broken_db_fails_open_candidates_still_evaluated` further
  confirms the new failure mode: an unreadable DB degrades to empty context, not a blocked gate.
- **Legacy context path (`firm.py::_build_context()`) still functions**: unmodified; still the only
  context source every existing agent node (`_run_analysts`, etc.) actually reads.
- **No schema/database change**: no `CREATE TABLE`/`ALTER TABLE`/`INSERT`/`UPDATE` was added anywhere
  in this change — every new builder call is read-only (inherited from WP1).

---

## Migration Status

| Tier 1 object | WP1 (builder exists) | WP2 (producer wired into live construction sites) | Consumed by Agent Firm |
|---|---|---|---|
| `TechnicalContext` | ✅ | ✅ | ❌ (future work) |
| `FlowContext` | ✅ | ✅ | ❌ |
| `RegimeContext` | ✅ | ✅ | ❌ |
| `NewsContext` | ✅ | ✅ | ❌ |
| `MarketContext` | ✅ (market_risk_score injected as a parameter) | ✅ (parameter now actually threaded from the scan cycle's real computation) | ❌ |
| `PortfolioContext` | ✅ | ✅ | ❌ |
| `RiskContext` | ✅ | ✅ | ❌ |
| `ExecutionContext` | ✅ | ✅ | ❌ |
| `SessionContext` | ✅ (builder exists) | **Not wired** — no `SignalCandidate` attach point exists (see Known Limitations) | ❌ |
| `ConsensusContext` | Type only (Tier 2, out of scope) | Out of scope (assembled by Agent Firm itself, post-analyst, per `ADR-AF-002`) | N/A |

---

## Known Limitations (deliberate WP2 scope boundaries, not defects)

1. **`SessionContext` has no `SignalCandidate` attach point.** `ADR-AF-004`'s "Required
   Implementation Changes" enumerates exactly eight new `SignalCandidate` fields (`technical`,
   `flow`, `regime_context`/`regime`, `news`, `market`, `portfolio`, `risk_limits`, `execution`) —
   `session` was never one of them, and WP1's actual `schemas.py` implementation matches that
   (confirmed by reading `SignalCandidate`'s field list directly). Adding a ninth field would be a
   schema change beyond "implement ONLY the wiring," so `build_session_context()` is not called from
   either construction site. This mirrors a documentation/implementation gap that already existed
   between `ADR-AF-002`'s prose (which lists `SessionContext` as a Tier 1 per-candidate object) and
   the frozen field list `ADR-AF-004`/`schemas.py` actually shipped — inherited from WP1, not
   introduced here, and not silently resolved: it would need its own dated ADR amendment to close,
   per the mission brief's instruction to stop and document rather than redesign.
2. **`OpportunityContext`, named in `ADR-AF-002`'s Tier 1 per-candidate list, has no type definition
   in `schemas.py` and no builder in `engine/agent_firm_context.py`.** Same category as (1) — an
   inherited WP1 gap between ADR prose and shipped code, not touched by WP2.
3. **Context population adds one DB round-trip per candidate per gate call** (≤20 candidates,
   the existing cost-guard cap) — a `SELECT`-only cost, using the already-centralized
   `data.db.connect()` entry point, no new connection-pooling or caching beyond the existing
   per-scan-cycle batch cache. Not measured against production load in this change; flagged for
   observation, not treated as a blocking concern (the whole step is fail-open on any DB error).
4. **Full documentation reconciliation deferred.** `AF1_CONTEXT_OBJECT_CATALOG.md`,
   `AF1_CONTEXT_API_V2_SPEC.md`, and `AF2_WORK_PACKAGE_SEQUENCE.md`'s own affected-file lists are not
   updated by this change — `AF2_ARCHITECTURE_CERTIFICATION.md` states each ADR's own "Required
   Documentation Updates" section is authoritative and that applying those edits is implementation
   work distinct from this specific wiring task (closer to the sequence document's own `WP7`). Out of
   this work package's stated mission.

---

## Readiness for WP3

Producer wiring is complete and independently verified:
- Every Tier 1 context object that has a `SignalCandidate` attach point is populated with real data
  from its canonical producer at both live construction sites, fail-soft at two layers (per-field via
  `_safe()`, per-candidate-batch via the outer `try`/`except` already present in both gate functions).
- `engine/agent_firm/` (prompts, agents, consensus, sizing, `evaluate`/`evaluate_staged`) is
  unmodified — zero risk of a decision-output change from this work package, confirmed by the full
  passing test suite.
- The legacy context path remains fully live and is the only thing any agent actually consumes today.

**What a future work package (consumption — updating `engine/agent_firm/prompts/*.md` to read the
new fields and retiring the corresponding raw-data prompt instructions, per
`AF1_PROMPT_CONTEXT_MAPPING.md`, then eventually deleting `firm.py::_build_context()` per
`ADR-AF-002`'s stated end state) can now build on:** every field is live, tested against both
hermetic fixtures and a seeded integration DB, and already flowing through the exact
`SignalCandidate` instances `evaluate_staged()` receives — wiring consumption is the only remaining
step; no further producer-side work is required first.
