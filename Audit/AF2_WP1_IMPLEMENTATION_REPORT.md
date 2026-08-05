# AF-2 Work Package 1 (Foundation) — Implementation Report

**Date:** 2026-07-29
**Basis:** `docs/agent_firm/ADR-AF-001-DETERMINISTIC_OWNERSHIP.md`,
`docs/agent_firm/ADR-AF-002-CONTEXT_OWNERSHIP.md`, `docs/agent_firm/ADR-AF-003-SIZING_OWNERSHIP.md`,
`docs/agent_firm/ADR-AF-004-VERSIONING_CONTRACT.md`, `docs/agent_firm/AF2_ARCHITECTURE_CERTIFICATION.md`.
**Scope:** foundation infrastructure only — context object type definitions, Production-Engine-owned
context builders, unit tests. Nothing in the live evaluation path (`firm.py`, `scanner.py`, `jobs.py`,
any prompt) was touched. Nothing consumes this infrastructure yet.

---

## Files Changed

| File | Type | Lines |
|---|---|---|
| `engine/agent_firm/schemas.py` | Modified | +139 (all additive) |
| `tests/agent_firm/test_schemas.py` | Modified | +119 (all additive) |
| `engine/agent_firm_context.py` | New | 389 |
| `tests/test_agent_firm_context.py` | New | 276 |

**Nothing else changed.** Verified by `git status` — `scheduler/scanner.py`, `scheduler/jobs.py`,
`engine/agent_firm/firm.py`, every prompt in `engine/agent_firm/prompts/`, and every agent module in
`engine/agent_firm/agents/` are byte-for-byte unmodified.

---

## What Was Built

### 1. Context object type definitions (`engine/agent_firm/schemas.py`)

Ten new Pydantic classes, per `ADR-AF-002`'s decision that Agent Firm owns type definitions:
`TechnicalContext`, `FlowContext`, `RegimeContext`, `NewsContext`, `MarketContext`, `PortfolioContext`,
`RiskContext`, `ExecutionContext`, `SessionContext`, `ConsensusContext`. Every field defaults to a
sensible empty/neutral value (`None`, `0`, `[]`, `"UNKNOWN"`/`"NEUTRAL"` as appropriate) so every type
constructs with zero arguments — required for the "may exist unused" constraint, verified by a
parametrized test over all nine Tier 1/2 types.

`SignalCandidate` gains eight new optional fields (`technical`, `flow`, `regime_context`, `news`,
`market`, `portfolio`, `risk_limits`, `execution`), all defaulting to `None`. `AgentDecision` gains one
new optional field (`size_tier`), also defaulting to `None`. Per `ADR-AF-004`, `evaluate`/
`evaluate_staged`/`reset_market_ctx`'s signatures are untouched — this keeps the change MINOR under
`AGENT_FIRM_GOVERNANCE.md`'s existing versioning rule, not something requiring an amendment.

**One deviation from the ADR text, made necessary by a pre-existing name collision:** `ADR-AF-002`/
`ADR-AF-004` describe the new field as `SignalCandidate.regime: RegimeContext | None`, but
`SignalCandidate.regime: Optional[str]` already exists (the quant pipeline's own regime label, per
`AGENT_FIRM_INTERFACE_SPEC.md`'s data contract). The new field is named `regime_context` instead. This is
noted here as a documentation-vs-implementation discrepancy for the record, not silently resolved —
`AF1_CONTEXT_OBJECT_CATALOG.md` and the ADRs should be corrected to `regime_context` in a follow-up
documentation pass.

### 2. Context builders (`engine/agent_firm_context.py`)

Nine builder functions, one per Tier 1 object (`ConsensusContext` has no builder here — it is the
documented Tier 2 exception, assembled post-analyst, out of WP1's scope by design). Per `ADR-AF-001`,
every builder either wraps an existing canonical Production Engine function or performs a genuinely new,
small aggregation with no existing implementation to duplicate:

| Builder | Wraps (no re-derivation) | New, non-duplicated computation |
|---|---|---|
| `build_technical_context` | `engine.technicals.tech_direction()` (passthrough → `mechanical_direction`); `engine.indicators.calc_sma/calc_adx/calc_atr/calc_close_vs_ma/calc_ma_slope/calc_vol_ratio`; `engine.chart_indicators.support_resistance/detect_patterns` | — |
| `build_flow_context` | `stockbit_flow.verdict/.smart_money/.composite_score/.foreign_score` (passthrough, already computed by `flow_filter.py`) | `net_foreign_14d` (SUM over `broker_flow`), `trend_7d` (rolling-sign over `stockbit_flow_bars`) |
| `build_regime_context` | `engine.regime_filter.detect_regime()` (passthrough → `regime_call`) | `ticker_consistency_pct`/`sector_tailwind`/`macro_risk` from `wf_scores`/`daily_screen` — the per-ticker confirmation facts named in `ADR-AF-001`, not a second regime classifier |
| `build_news_context` | `engine.agent_firm.tools.news_lookup.lookup()` (called directly, not reimplemented — see Known Limitations); `engine.catalyst.has_catalyst()` (passthrough) | `mentions_count_7d` (trivial sum) |
| `build_market_context` | `engine.regime_filter.detect_regime()` on IHSG; **reuses `build_technical_context()` itself** for `ihsg_trend` (no separate computation) | `market_risk_score` is a **dependency-injection parameter**, not computed here — see Known Limitations |
| `build_portfolio_context` | Reads `paper_trades` (same fields `firm.py`'s existing `_market_ctx["open_trades"]` already queries) | `open_position_count`; `PortfolioContext.has_open_position()` method |
| `build_risk_context` | `paper_trade.is_entries_blocked()`, `paper_trade.compute_drawdown()`, `security.auth.auth_mode()` — all three read-only, verified during implementation (no writes, no Telegram calls) | — |
| `build_execution_context` | `paper_trade.get_config()`, `paper_trade.get_open_trades()` — read-only, does **not** touch `open_trade()`'s own inline capital computation | `aggregate_open_exposure_pct` (derived from the two reads above) |
| `build_session_context` | — | `wib_session` derivation from `scan_time` (minute-aware WIB market-hours boundary) |

**Module placement:** `engine/agent_firm_context.py`, at the top level of `engine/`, outside
`engine/agent_firm/` — per `ADR-AF-002`'s explicit instruction that the ownership boundary be visible in
the file tree, mirroring `engine/edge_enrich.py`'s existing shape relative to `engine/veto.py`.

---

## Architectural Compliance

| ADR requirement | Compliance |
|---|---|
| `ADR-AF-001`: canonical producers, no re-derivation | Verified — `mechanical_direction`, `regime_call`, `verdict`/`smart_money`, `has_catalyst` are all direct passthroughs of the named canonical functions, confirmed by reading each builder against the table above |
| `ADR-AF-002`: Tier 1 assembled by Production Engine, outside `engine/agent_firm/`; type definitions owned by Agent Firm; ephemeral, no persistence | All three verified — `engine/agent_firm_context.py`'s location, `schemas.py`'s type ownership, and the absence of any `INSERT`/write statement anywhere in the new module (verified by inspection — every function is read-only) |
| `ADR-AF-003`: sizing not touched | Verified — `size_tier` is an inert field only; no `resolve_size_hint()`, no change to `scanner.py:962`/`1013`, no sizing logic anywhere in this change |
| `ADR-AF-004`: `evaluate()` signature unchanged; new fields are additive/optional | Verified — `firm.py` is byte-for-byte unmodified; every new field defaults to `None` |
| Requirement 5/6 (no duplicate business logic / deterministic calculations) | Verified per-builder in the table above — the one deliberate exception (`market_risk_score` as an injection point rather than a fresh 4-sensor wiring) is a **avoidance** of duplication, not an instance of it |

---

## Test Results

| Suite | Result |
|---|---|
| `tests/test_agent_firm_context.py` (new) | **25 passed** |
| `tests/agent_firm/test_schemas.py` (extended) | **25 passed** (10 pre-existing + 15 new) |
| `tests/agent_firm/` (full, excluding one pre-existing broken-collection file — see below) | **264 passed, 9 failed** |
| `tests/test_premarket_firm_scan.py`, `test_trade_plan.py`, `test_agent_size_hint.py`, `test_dashboard_signals.py`, `test_edge_enrich.py`, `test_catalyst.py` (every Production Engine test file that constructs `SignalCandidate` or touches modules this change reuses) | **107 passed** |
| `test_chart_indicators.py`, `test_indicators.py`, `test_indicator_cache.py`, `test_regime_3class.py`, `test_regime_edge_scan.py`, `test_regime_honesty.py`, `test_paper_trade_sizing.py`, `security/test_auth.py` (every module WP1's builders import) | **108 passed** |

**Pre-existing failures, verified not caused by this change:** 9 tests in `tests/agent_firm/providers/`
(`test_governor.py`, `test_quota_scenarios.py`, `test_quota_state_persistence.py`) fail both with and
without this change — confirmed directly by `git stash`-ing this change's edits and re-running the same
tests against the unmodified baseline, which reproduced the identical 9 failures. These tests belong to
an entirely separate, currently-**uncommitted** quota-governor feature (`engine/agent_firm/providers/
governor.py` and its test files are untracked in this repository, confirmed by `git status`) — unrelated
to WP1's scope. One additional file, `tests/agent_firm/providers/test_quota_hydration_edge_cases.py`,
fails to even collect (`ImportError: cannot import name '_hydrate_quota_holds'`) — same uncommitted
feature, same pre-existing condition, verified unaffected by this change.

**Two real bugs were found and fixed during test-writing** (both in this change's own new code, caught
before this report was written, not shipped with the defect):
1. `build_session_context()`'s WIB session boundary originally compared only the hour component,
   misclassifying 15:00-15:29 (still within IDX's 09:00-15:30 market hours per `CLAUDE.md`) as
   `post-close`. Fixed to a minute-aware comparison.
2. `build_technical_context()`'s `pattern_flags` originally returned `engine.chart_indicators.
   detect_patterns()`'s full per-bar history across the whole input window (up to 24 entries for a 60-bar
   fetch) rather than recent, actionable pattern context. Trimmed to the last 5 bars.

---

## Backward Compatibility Verification

- **`evaluate`/`evaluate_staged`/`reset_market_ctx`**: unmodified — `firm.py` was not touched.
- **`SignalCandidate`/`AgentDecision` existing fields**: unmodified in type or default; every existing
  test that constructs either class with only the original fields continues to pass unchanged (confirmed
  by the pre-existing tests in `test_schemas.py` still passing, plus the two new
  `*_backward_compatible` tests added specifically to assert every new field defaults to `None`).
- **No production call site changed**: `scheduler/scanner.py` (both `SignalCandidate(...)` construction
  sites, `indicators={}` included) and `scheduler/jobs.py` are unmodified — they continue to construct
  `SignalCandidate` exactly as before, simply not populating the eight new optional fields, which is the
  intended WP1 state.
- **No schema/database change**: every new builder is read-only; no `CREATE TABLE`, `INSERT`, `UPDATE`,
  or `ALTER TABLE` appears anywhere in this change.

---

## Known Limitations (deliberate WP1 scope boundaries, not defects)

1. **`market_risk_score` is a dependency-injection parameter, not computed by
   `build_market_context()` itself.** The canonical function, `engine.risk_score.compute_market_risk_score()`,
   requires four upstream sensor summaries (`flow_filter.get_market_accdist_summary`,
   `engine.vpin.get_market_vpin_summary`, `engine.breadth.get_market_breadth`,
   `engine.technicals.detect_ihsg_technicals`) already fully wired once per scan cycle inside
   `scheduler/scanner.py` (lines ~1229-1244) for an unrelated purpose. Rather than write a second,
   parallel wiring of those four sensors in this new module (a duplication risk `ADR-AF-001` exists to
   prevent), `build_market_context(conn, market_risk_score=...)` accepts the already-computed value as a
   parameter. Wiring the actual call is deferred to `AF2_WORK_PACKAGE_SEQUENCE.md`'s WP8, which was
   already scoped for exactly this. Verified via a dedicated test
   (`test_market_risk_score_is_injected_not_recomputed`) that the parameter passes through correctly.
2. **`ExecutionContext.max_position_pct_config` duplicates a literal, not a named constant.**
   `paper_trade.py:410` hardcodes `0.30` inline (`max_lots = int((capital * 0.30) / cost_per_lot)`) —
   there is no named constant to import. `build_execution_context()` mirrors the same literal with a
   comment explaining the duplication rather than refactoring `paper_trade.py` to introduce one, since
   that refactor is explicitly out of WP1's scope (and was separately flagged in
   `AF2_WORK_PACKAGE_SEQUENCE.md`'s WP9 discussion as carrying its own regression risk, warranting its
   own reviewed change).
3. **`ConsensusContext` has a type definition but no builder.** Correct per `ADR-AF-002`'s Tier 2
   distinction — it depends on analyst `AgentResult`s that don't exist until Agent Firm's own evaluation
   graph runs, which WP1 does not touch.
4. **The `SignalCandidate.regime_context` naming deviation** (see "What Was Built" §1) should be
   corrected in the ADR/Catalog documents in a follow-up documentation-only change.
5. **`news_lookup.lookup()`'s db-path recovery via `PRAGMA database_list`** works correctly against any
   real, file-backed SQLite connection (verified in tests via a temp-file DB) but would silently return
   an empty result against a pure `:memory:` connection, since each `:memory:` connection is its own
   isolated database and the recovered path can't reopen the same one. This is a non-issue for production
   (every real connection is file-backed via `data.db.connect(DB_PATH)`) and is exercised correctly in
   tests using a temp file, not `:memory:`, for this specific builder — noted here for anyone extending
   this module later.

---

## Readiness for WP2

Foundation infrastructure is in place and independently verified:
- Every context object type is defined, validated, and JSON-serializable.
- Every Tier 1 builder is implemented, unit-tested against hermetic fixtures, and smoke-tested against
  the real production database (`data/walkforward.db`) with sensible output for a live ticker (`AADI`).
- No live behavior changed; no existing test regressed.

**What WP2 (per `AF2_WORK_PACKAGE_SEQUENCE.md`'s recommended order: WP2/WP8/WP1/WP3 next, in any order)
can now build on:** the builder functions exist and are ready to be called from wherever context
assembly is actually wired into the evaluation path — that wiring itself, along with updating
`engine/agent_firm/prompts/*.md` to consume the new fields and retiring the corresponding raw-data
prompt instructions (per `AF1_PROMPT_CONTEXT_MAPPING.md`), remains future work, not performed here.
