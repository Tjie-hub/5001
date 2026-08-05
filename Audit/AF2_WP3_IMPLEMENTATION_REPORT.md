# AF-2 Work Package 3 (Specialist Context Consumption Migration) — Implementation Report

**Date:** 2026-07-29
**Basis:** `docs/agent_firm/ADR-AF-001-DETERMINISTIC_OWNERSHIP.md`,
`docs/agent_firm/ADR-AF-002-CONTEXT_OWNERSHIP.md`, `docs/agent_firm/ADR-AF-003-SIZING_OWNERSHIP.md`,
`docs/agent_firm/ADR-AF-004-VERSIONING_CONTRACT.md`,
`Audit/AF2_WP1_IMPLEMENTATION_REPORT.md` (Foundation — the typed context objects and the eight
new `SignalCandidate` fields), `Audit/AF2_WP2_IMPLEMENTATION_REPORT.md` (Producer wiring — every
Tier 1 field is populated with real data at both live `SignalCandidate` construction sites, but
nothing consumed it yet).
**Scope, as briefed:** consumption migration only. Every Agent Firm specialist that has a Tier 1
context attach point (Technical, Flow, Regime, News, Risk) now reads that typed context directly
off `SignalCandidate` instead of deriving facts from raw data or a hand-rolled SQL context dict.
No architectural redesign, no `SignalCandidate`/`AgentDecision` schema change, no scanner/scheduler/
context-builder/paper-trading edit, no new agents.

---

## Files Changed

| File | Nature of change |
|---|---|
| `engine/agent_firm/agents/technical.py` | Dropped the `db_path` parameter and its `sqlite_query` OHLCV fetch; now reads `candidate.technical` (`TechnicalContext`), fails soft to `TechnicalContext()` if absent |
| `engine/agent_firm/agents/flow.py` | Dropped the raw `context: dict` parameter (`stockbit_flow`/`broker_flow`/`stockbit_flow_bars` rows); now reads `candidate.flow` (`FlowContext`) |
| `engine/agent_firm/agents/regime.py` | Dropped the raw `context: dict` parameter (`wf_scores`/`daily_screen` rows); now reads `candidate.regime_context` (`RegimeContext`) |
| `engine/agent_firm/agents/news.py` | Dropped the raw `context: dict` parameter (`news_mentions` rows); now reads `candidate.news` (`NewsContext`); the live Tavily web-search call is unchanged |
| `engine/agent_firm/agents/risk.py` | Signature unchanged (candidate already carried everything); now additionally reads `candidate.portfolio` (`PortfolioContext`) and `candidate.risk_limits` (`RiskContext`) into the prompt payload — closes a pre-existing delivery gap (see below) |
| `engine/agent_firm/prompts/technical_v1.md`, `flow_v1.md`, `regime_v1.md`, `news_v1.md`, `risk_v2.md` | Rewritten to describe the typed context object each agent now receives and to explicitly instruct "interpret, don't recompute" (see `Audit/AF2_WP3_PROMPT_SIMPLIFICATION_REPORT.md`) |
| `engine/agent_firm/firm.py` | `_build_context()` (7 raw SQL queries) deleted per `ADR-AF-002`'s "Required Implementation Changes"; `_run_analysts()`/`_run_stage1()` simplified to call each analyst with just `(candidate, client)`; `build_context` node removed from the LangGraph DAG; `_market_ctx`/`reset_market_ctx()` retained as an inert compatibility shim (see below) |
| `engine/agent_firm/smoke.py` | `_CANNED` module constant replaced with `_build_canned_candidate()`, which calls `engine.agent_firm_context.build_candidate_context()` so the daily smoke probe exercises real Tier 1 context instead of empty defaults |
| `tests/agent_firm/test_technical.py`, `test_flow.py`, `test_regime.py`, `test_news.py`, `test_risk.py` | Updated for the new call signatures; added context-payload, missing-context fail-soft, and (for `risk.py`) portfolio/risk-limits wiring tests |

**Not touched, as briefed:** `scheduler/scanner.py`, `scheduler/` generally, `engine/agent_firm_context.py`
(the Tier 1 context builders WP2 shipped), `engine/agent_firm/schemas.py` (`SignalCandidate`/
`AgentDecision`/`AgentResult` — zero fields added, zero renamed), any database schema, `paper_trade.py`,
the replay architecture, and every ADR document. `engine/agent_firm/agents/bull.py`, `bear.py`, and
`guardrails.py` are also unmodified — see "Bull/Bear/Guardrails: Confirmed Already Compliant" below.

---

## What Changed, Per Specialist

### Technical Analyst

**Before:** received a raw `db_path` string and ran its own `sqlite_query` for the last 60 OHLCV
bars; the prompt asked the LLM to "produce a technical conviction call and identify key support /
resistance levels" directly from those bars — i.e. derive support/resistance and a directional read
from raw price data itself.

**After:** receives `candidate.technical` (`TechnicalContext`) — `sma20`, `sma50`,
`close_vs_sma50_pct`, `ma_slope_20`, `adx`, `atr`, `vol_ratio`, `support_levels`,
`resistance_levels`, `pattern_flags`, `mechanical_direction` (a `tech_direction()` passthrough,
per `ADR-AF-001`) — all already computed by `engine.agent_firm_context.build_technical_context()`
from `engine.indicators`/`engine.chart_indicators`/`engine.technicals`. `ohlcv_recent_10d` is kept
for color only. The prompt now explicitly instructs the model not to recompute any of these and to
use `support_levels`/`resistance_levels` directly for `key_levels` rather than deriving new ones.
No SQL query happens inside the agent anymore (`result.tools_called == []` — verified by test).

### Flow Specialist

**Before:** received raw `stockbit_flow`/`broker_flow`/`stockbit_flow_bars` rows; the prompt
explicitly instructed the LLM to compute `net_foreign_14d` itself ("sum of net_lot values from
broker_flow rows where investor_type='Asing'") — a lot-aggregation task, not interpretation.

**After:** receives `candidate.flow` (`FlowContext`) — `verdict`, `smart_money`, `composite_score`,
`foreign_score` (Stockbit's own columns, passthrough), `net_foreign_14d` (already summed by
`build_flow_context()`), `trend_7d` (already derived from bar-level deltas). The prompt's
lot-summation instruction is removed entirely; the model is told the field is already computed and
to pass it through unchanged in its output.

### Regime Analyst

**Before:** received raw `wf_scores`/`daily_screen` rows; the prompt encoded literal thresholds
for the LLM to apply itself (`"BULL: quant pipeline says BULL AND walk-forward consistency >= 55%"`,
`"VOLATILE: vpin_label is EXTREME... OR avg vol_ratio > 3.0"`) — an independent, second regime
classifier built out of prompt prose, exactly the anti-pattern `ADR-AF-001` documents and closes.

**After:** receives `candidate.regime_context` (`RegimeContext`) — `regime_call` (a
`detect_regime()` passthrough — the one canonical regime reading), `sector_tailwind`, `macro_risk`,
`best_strategy`, `ticker_consistency_pct`, all already computed by `build_regime_context()`. The
prompt no longer states any threshold; it instructs the model to default to `regime_context`'s own
values and only deviate — with an explicit stated reason — when `recent_screen_signals` clearly
contradicts them.

### News/Sentiment Analyst

**Before:** received a raw `news_mentions` list; already did not perform deterministic derivation
(no counting/threshold logic existed in the prompt) — its only gap was receiving an untyped dict
instead of the typed `NewsContext`.

**After:** receives `candidate.news` fields (`mentions_7d`, `mentions_count_7d`, `has_catalyst` — a
`has_catalyst()` passthrough, per `ADR-AF-001`) alongside the same live Tavily web search as before.
`has_catalyst` is now explicitly named in the prompt as a fact to weigh, not re-derive. The live web
search is deliberately **not** replaced by anything in `NewsContext` — per `ADR-AF-001`, it is
genuine real-time NLU input with no existing canonical producer, distinct from the deterministic
`has_catalyst` passthrough.

### Risk Manager

**Before:** received the candidate (already including all 8 Tier-1 fields via `model_dump()`,
silently, since WP2) and the analyst/bull/bear reports. The prompt claimed to receive "current open
paper trades" and instructed "Veto if ticker already has an open paper trade" — but no open-trades
data was ever threaded into `risk.run()`'s actual parameters. This was a real, pre-existing gap:
the veto condition was documented but structurally undeliverable.

**After:** additionally receives `portfolio_context` (`already_open_position` — a
`PortfolioContext.has_open_position()` membership lookup, not a calculation — and
`open_position_count`) and `risk_context` (`entries_blocked`, `drawdown_pct`), both already computed
by `paper_trade.py`'s existing `is_entries_blocked()`/`compute_drawdown()` via
`build_risk_context()`/`build_portfolio_context()`. The prompt's decision framework now references
both explicitly and states the Risk Manager must never calculate volatility, exposure, position
sizing, leverage, or drawdown itself — only weigh these already-computed facts qualitatively. This
closes the gap: `test_risk_prompt_payload_carries_portfolio_and_risk_context` verifies the veto-worthy
fact actually reaches the prompt now. The candidate payload sent to the LLM was also trimmed to
identity fields only (ticker/strategy/regime/flow_verdict/foreign_score/quant_score) — it no longer
implicitly leaks the other 6 Tier-1 context objects (`technical`, `flow`, `regime_context`, `news`,
`market`, `execution`) that Risk never asked for.

### Bull/Bear/Guardrails: Confirmed Already Compliant

`bull.py`/`bear.py` consume only `analyst_reports` (the four analysts' already-produced `AgentResult`s)
— no raw data, no independent technical/flow/regime analysis, matching the brief's "CIO"/"Consensus"
requirement ("consume specialist outputs only, no independent technical analysis") even though no
dedicated agent module by that name exists (see "Portfolio Manager / CIO / Consensus" below).
`guardrails.py::apply_guardrails()` keys only on already-produced analyst verdict strings
(`flow_verdict`, `verdict`, `regime_call`) — a lookup/comparison over categorical LLM outputs, not a
market-data derivation. Neither file needed a change; verified unmodified by `git diff` and by the
full `tests/agent_firm/test_bull.py`/`test_bear.py`/`test_guardrails.py` suites passing unchanged.

---

## Portfolio Manager / CIO / Consensus — Mapped to the Actual Codebase

The mission brief's org chart (Technical / Flow / Regime / News / Risk Manager / Portfolio Manager /
CIO / Consensus) does not have a 1:1 mapping onto the seven agents that actually exist in
`engine/agent_firm/agents/` (`technical`, `flow`, `regime`, `news`, `bull`, `bear`, `risk`) — there is
no `portfolio_manager.py`, `cio.py`, or `consensus.py`. Rather than invent new agents (an
architecture/feature addition explicitly out of scope), this work package maps the brief's intent
onto what exists:

- **Portfolio Manager** — no dedicated agent. `PortfolioContext` consumption is wired into
  `risk.py`, the only node that makes a capital-facing decision, per the gap closed above.
- **CIO** — no dedicated agent. `bull.py`/`bear.py` (the steelman researchers) are the closest
  structural analog — "consume specialist outputs only, no independent technical analysis" — and were
  already compliant (see above).
- **Consensus** — `ConsensusContext` (schemas.py) is a Tier 2 type with **no builder and no
  evaluation-graph attach point**, confirmed still true after this work package
  (`guardrails.py::build_consensus_summary()`, named in `ADR-AF-002` as its intended location, does
  not exist). `ADR-AF-002` explicitly scopes `ConsensusContext` assembly to Agent Firm itself
  (post-analyst, pre-risk) — building it now would be new Tier 2 wiring with no prior WP1/WP2
  foundation to migrate, which is a feature addition beyond this work package's "migrate consumption
  of already-produced Tier 1 context" mandate. **Documented as inherited, unresolved technical debt**,
  carried forward unchanged from `Audit/AF2_WP2_IMPLEMENTATION_REPORT.md`'s "Known Limitations" — not
  silently built, not silently dropped.

---

## `firm.py`: Retiring the Legacy Raw-Context Path

`ADR-AF-002`'s "Required Implementation Changes" states plainly: `_build_context()` is deleted, not
replaced in place — its 7 raw SQL queries move to `engine/agent_firm_context.py` in typed/derived
form (already done in WP1/WP2). This work package performs that deletion:

- `_build_context()` (the SQL-query function) and the `"build_context"` LangGraph node are removed.
  `_run_analysts()` now calls `technical.run(candidate, client)`, `flow.run(candidate, client)`,
  `regime.run(candidate, client)`, `news.run(candidate, client)` directly — no context dict or
  `db_path` is threaded through `AgentState` anymore. `_run_stage1()` (the 2-stage pre-scan's cheap
  technical+regime pass) is simplified the same way.
- `_market_ctx`/`reset_market_ctx()` — the legacy cache `_build_context()` fed — is **retained,
  unchanged, as an inert compatibility shim**. It cannot be deleted in this work package:
  `scheduler/scanner.py` still imports and calls `reset_market_ctx()` once per scan cycle (WP2
  deliberately kept this call alongside the new `reset_batch_context()` call, per its own report),
  and `scheduler/scanner.py` is explicitly out of WP3's scope ("Do NOT modify: scanner"). Removing
  the now-fully-dead cache requires a `scanner.py` edit, which this work package does not perform —
  flagged here as the one remaining piece of `ADR-AF-002`'s end state, deferred to a future,
  scanner-touching work package.
- `AgentState`'s `db_path`/`context` `TypedDict` keys are **left in place, unused** (populated with
  `""`/`{}` in `evaluate_async()`) rather than removed from `schemas.py` — `schemas.py` is out of
  this work package's scope by the mission brief's own "Do NOT modify... SignalCandidate schema"
  instruction, and `AgentState` lives in the same file.

---

## Architectural Compliance

| Requirement (from the WP3 mission brief) | Compliance |
|---|---|
| Every specialist with a Tier 1 attach point consumes structured contexts | **Met** — Technical/Flow/Regime/News/Risk all read their typed context off `candidate`; see per-specialist sections above |
| No specialist derives deterministic indicators/aggregations/thresholds | **Met** — no `sqlite_query`, no lot-summation, no VPIN/vol_ratio/Sharpe thresholding remains in any prompt or agent body (verified by `git diff` and by the new `tools_called == []` / payload-content tests) |
| Prompts request interpretation, not computation | **Met** — every rewritten prompt states outright "these facts are already computed... do not recompute/re-derive/re-sum" (see `Audit/AF2_WP3_PROMPT_SIMPLIFICATION_REPORT.md`) |
| Agent Firm remains schema-compatible | **Met** — `SignalCandidate`/`AgentResult`/`AgentDecision` untouched; every specialist's JSON *output* schema (the fields `guardrails.py`/`analytics.py`/`firm.py` read: `verdict`, `flow_verdict`, `regime_call`, `sentiment`, `decision`, etc.) is byte-for-byte unchanged |
| Missing contexts degrade gracefully | **Met** — every specialist does `candidate.<field> or <ContextType>()`, verified directly by five new `*_missing_context_degrades_to_default_not_raise`-style tests, one per specialist |
| Existing evaluation pipeline remains unchanged | **Met** — `evaluate`/`evaluate_staged`'s public signatures, the daily-spend-cap short-circuit, the LangGraph node ordering after `run_analysts`, guardrail override logic, and persistence are all unmodified; `tests/agent_firm/test_firm.py`/`test_firm_v2.py` pass unchanged |
| No feature additions / no architecture redesign | **Met** — no new agents, no `ConsensusContext` builder, no schema/database change; the one behavior change (Risk Manager now actually sees open-position/drawdown facts) closes an already-documented, already-specified prompt instruction rather than adding new decision logic |

---

## Test Results

Run via the Windows checkout's `.winvenv` interpreter (`DB_PATH=data/walkforward.db
.winvenv/Scripts/python.exe -m pytest ...`).

| Suite | Result |
|---|---|
| `tests/agent_firm/test_technical.py`, `test_flow.py`, `test_regime.py`, `test_news.py`, `test_risk.py`, `test_risk_v2.py`, `test_bull.py`, `test_bear.py`, `test_guardrails.py`, `test_schemas.py` | **75 passed** |
| `tests/agent_firm/test_firm.py`, `test_firm_v2.py`, `test_migration.py`, `test_analytics.py`, `test_smoke.py` | **37 passed** |
| `tests/agent_firm/test_firm.py` + `tests/test_agent_firm_context_wiring.py` + `tests/test_agent_firm_context.py` + `tests/test_scheduler_firm_hook.py` + `tests/test_agent_size_hint.py` + `tests/test_bear_watchlist_ranking.py` + `tests/test_nr7_live_pipeline_e2e.py` | **67 passed** (see "Windows Test-Ordering Artifact" below — `test_firm.py` must run first in-session) |
| `tests/test_architecture_boundary.py`, `test_research_data_fence.py`, `test_db_centralization.py`, `security/test_route_policy.py` | **13 passed** — no boundary/write-fence/route-classification regression |
| Full suite, `pytest -q --ignore=tests/agent_firm/providers` | **1560 passed, 44 failed, 9 errors** (426s) — **+11 passed vs. WP2's reported 1549** (exactly the 11 new tests this work package added: 3 in `test_technical.py`, 2 each in `test_flow.py`/`test_regime.py`/`test_news.py`/`test_risk.py`); **identical 44-failed/9-error set to WP2's own reported baseline**, same files, same categories — see below |

### Windows Test-Ordering Artifact (pre-existing, not introduced by WP3)

`tests/test_agent_firm_context_wiring.py`, `test_scheduler_firm_hook.py`, and `test_agent_size_hint.py`
fail with `AttributeError: <module 'engine.agent_firm'> does not have the attribute 'firm'` **when run
in isolation** on this Windows checkout, because `engine/agent_firm/__init__.py` only imports `firm`
lazily and `patch.object(engine.agent_firm, "firm", ...)` requires the attribute to already exist.
This is the exact gap `Audit/AF2_WP2_IMPLEMENTATION_REPORT.md`'s "A Pre-Existing Windows Test-Env Gap
Found, Not Fixed" section already documented — confirmed identical before and after this work
package's changes, and confirmed to disappear once any `tests/agent_firm/` file runs first in the same
pytest session (priming the package attribute). Not a WP3 regression.

### Full-Suite Failures (identical to WP2's reported baseline, re-verified here)

Every failing file is one this work package does not touch, and every failure is the same
Windows-local-tooling category WP2 already catalogued: `test_value_format.py` (Node.js path-quoting on
Windows), `security/test_release_scripts.py`/`test_cron_contract.py` (POSIX-shell scripts invoked
directly), `test_auto_token.py` (Playwright/credential-refresh, unrelated module), `security/
test_secret_hygiene.py` (flags a third-party `langsmith` source line pulled in by installing
`langgraph` into `.winvenv` — the same pre-existing local-environment artifact WP2 documented, not a
repository issue), `test_config_validation.py`/`test_logging_config.py`/`test_news_filter.py`/
`test_stockbit_fetcher_ensure_valid_token.py`/`test_experiment_tracking.py`/`regime/test_storage.py`
(known Windows-checkout env/timezone/filesystem gaps, none touching `agent_firm`/`scanner`/
`paper_trade`/`SignalCandidate`).

---

## Known Limitations (deliberate WP3 scope boundaries, not defects)

1. **`ConsensusContext` remains unbuilt and unconsumed.** See "Portfolio Manager / CIO / Consensus"
   above — inherited from WP1/WP2, not resolved here, would need its own dated ADR/work package.
2. **`reset_market_ctx()`/`_market_ctx` in `firm.py` are dead code kept alive only for
   `scheduler/scanner.py`'s existing import.** `ADR-AF-002` calls for their removal; doing so requires
   editing `scanner.py`, out of this work package's scope.
3. **`AgentState`'s `db_path`/`context` keys are unused but not removed** from
   `engine/agent_firm/schemas.py`, per this work package's "do not touch `SignalCandidate` schema"
   instruction extending conservatively to the whole file.
4. **`ADR-AF-001`'s stated News-agent output rename (`catalyst` → `catalyst_sentiment`, to
   disambiguate from `NewsContext.has_catalyst`) was not performed.** It was never implemented in
   WP1/WP2 either (`news_v1.md`'s output schema still uses `catalyst`); renaming a specialist's JSON
   output field is a distinct decision from consumption migration and was not named in this work
   package's mission brief. Flagged here rather than silently carried forward without mention.
5. **`bull.py`/`bear.py` still send the full `candidate.model_dump()`**, which since WP2 silently
   includes all 8 Tier-1 context objects even though neither agent's prompt references them. Not
   named in the WP3 mission brief's Required Changes list (only Technical/Flow/Regime/News/Risk/
   Portfolio Manager/CIO/Consensus are named, and Bull/Bear were independently confirmed already
   behaviorally compliant — no raw-data derivation). Left untouched to keep this work package's diff
   scoped to its explicit mandate; flagged as a minor, pre-existing prompt-bloat inefficiency for a
   future prompt-simplification pass.
