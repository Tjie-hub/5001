# Agent Firm — Post-ADR Integration Validation Report

**Date:** 2026-07-29
**Scope:** ADR-AF-002 (Context Ownership), ADR-AF-003 (Sizing Ownership), ADR-AF-004 (Versioning
Contract) — all previously implemented and independently certified in prior sessions. This report
is a fresh, end-to-end integration validation across all three together, not a re-litigation of any
single ADR's own implementation report.

---

## Executive Summary

The complete production chain — `scanner signal → Tier 1 context → Agent Firm committee → sizing
resolution → paper_trade.open_trade()` — was validated end-to-end this session, for the first time
as one connected chain rather than as three separately-certified segments. **One genuine,
previously-undiscovered integration defect was found and fixed**: `AgentDecision.size_tier` (the
Risk agent's qualitative sizing recommendation, introduced by ADR-AF-003) was never wired into
`agent_decisions`' database schema or `firm.py::_persist()`'s INSERT statement — it existed only on
the in-memory Pydantic object and was silently dropped every time a decision was persisted. This is
fixed (an idempotent schema migration + one INSERT-statement update, matching this repository's own
established migration pattern) and covered by a new regression test proving the value now round-trips
through the real database.

Beyond that one fix, every contract from all three ADRs was independently re-verified against real
execution (not re-derived from prior reports): no legacy code path bypasses the single-writer
sizing model, fail-soft behavior holds at every tested failure point, and the pipeline is
deterministic across repeated runs with identical inputs.

**Recommendation: GO WITH CONDITIONS** (detail in §9).

---

## Validation Scope

- **In scope:** the full chain from scanner-level signal construction through Tier 1 context
  attachment, Agent Firm committee evaluation, `resolve_size_hint()`'s sizing resolution, and
  `paper_trade.open_trade()`'s actual position sizing — plus the audit-trail persistence
  (`agent_decisions`/`agent_traces`) that chain produces.
- **Out of scope, unchanged:** any research code, any architecture decision (all three ADRs are
  treated as settled), any refactoring of code not directly implicated in a discovered defect.
- **Method:** consistent with the precedent already established and accepted in this repository's
  own prior Production Validation session (`Audit/AF2_PRODUCTION_VALIDATION_REPORT.md`), real
  production code paths (`run_edge_veto_stage()`, `run_agent_firm_gate()`,
  `resolve_agent_size_hints()`, `paper_trade.open_trade()`, `firm.py`'s real LangGraph evaluation
  graph) were exercised against real seeded SQLite data, with a scripted/mocked LLM layer standing in
  for real Z.ai/Claude calls — avoiding real API spend and avoiding consumption of this session's own
  shared Claude-provider quota, the same tradeoff explicitly chosen in the prior session.

---

## End-to-End Execution Path (as validated)

```
signal (scanner intersection_results row)
  │
  ▼
run_edge_veto_stage()          — EDGE_SCORE_MODE gate; attaches edge_score (real code, mocked
  │                               engine.veto.apply_vetoes/engine.edge_enrich internals)
  ▼
run_agent_firm_gate()          — build_candidate_context() attaches real Tier 1 context (ADR-AF-002);
  │                               firm.evaluate_staged() runs the real 7-agent committee (scripted
  │                               LLM layer); attaches agent_size_tier only (ADR-AF-003 — no numeric
  │                               write here)
  ▼
resolve_agent_size_hints()     — the sole writer of agent_size_hint (ADR-AF-003), combining
  │                               edge_score + agent_size_tier per the ADR's exact precedence rule
  ▼
paper_trade.open_trade(lots_multiplier=agent_size_hint)
  │
  ▼
agent_decisions / agent_traces — persisted audit trail (now including size_tier — see §5)
```

Every arrow above was exercised with real function calls this session (`tests/test_scanner_to_open_trade_integration.py`),
not simulated at the boundary — the only mocked components are the three deepest edge-veto
internals (`engine.veto.apply_vetoes`, `engine.edge_enrich.market_regime`/`enrich_candidate` —
mocked to return a controlled, known edge score, exactly as ADR-AF-003's own B2 regression test
already established as sufficient) and the LLM provider layer itself.

---

## Contract Verification

### ADR-AF-002 (Context Ownership)

Re-verified, not re-derived: all five live `SignalCandidate` construction sites still attach Tier 1
context via `build_candidate_context()` before evaluation (confirmed unchanged by this session's
own `run_agent_firm_gate()` re-read); no specialist performs its own SQL/data retrieval (unchanged,
re-confirmed by grep); the legacy `_build_context()` remains fully absent. No new finding this
session beyond what `Audit/ADR-AF-002_FINAL_POST_IMPLEMENTATION_AUDIT.md` already certified.

### ADR-AF-003 (Sizing Ownership)

- **Single-writer invariant:** re-ran `tests/test_sizing_single_writer_invariant.py` fresh — still
  exactly one `agent_size_hint` assignment site in the entire production codebase
  (`resolve_agent_size_hints()`), unchanged since the ADR-AF-003 implementation session.
- **Precedence rule under real execution:** `tests/test_scanner_to_open_trade_integration.py`'s
  `test_full_chain_approve_with_increase_tier_sizes_trade_up` proves `edge_score=0.6` +
  `size_tier="increase"` produces `0.69` (`0.6 × 1.15`) through the real `resolve_size_hint()` call,
  and that this measurably changes `open_trade()`'s resulting lot size versus the unmodulated
  edge_score alone — the precedence rule holds under real execution, not only in the unit tests
  that exercise `resolve_size_hint()` directly.
- **Audit-trail persistence — defect found and fixed (see §5).**

### ADR-AF-004 (Versioning Contract)

Re-ran `tests/agent_firm/test_versioning_contract.py` fresh — `evaluate`/`evaluate_staged`/
`evaluate_async`/`evaluate_staged_async`/`reset_market_ctx` signatures are still byte-for-byte
unchanged. No new finding.

---

## Integration Findings

### Finding 1 (defect, fixed) — `size_tier` never reached the audit trail

**What was found:** `data/db.py::init_agent_firm_tables()`'s `agent_decisions` table DDL had no
`size_tier` column, and `engine/agent_firm/firm.py::_persist()`'s `INSERT` statement never included
it — despite `size_tier` existing on the `AgentDecision` Pydantic model since ADR-AF-003. Every
Risk-agent sizing recommendation was silently discarded at the point of persistence; only
`decision`/`confidence`/`rationale` (and the now-always-`None` `size_hint`) reached the database.

**Why this blocked successful integration validation:** Objective 5 of this validation
("Validate audit logging and persistence") cannot be truthfully certified as passing while a field
the architecture explicitly introduced for exactly this purpose is silently dropped.

**Fix:** an idempotent `ALTER TABLE agent_decisions ADD COLUMN size_tier TEXT` (matching this
repository's own established `PRAGMA table_info()` + `ALTER TABLE ADD COLUMN` migration pattern,
identical in shape to the pre-existing `providers_used` column migration a few lines above it), plus
adding `size_tier` to `_persist()`'s column list and value tuple. This is a minimal, mechanical
completion of already-decided wiring — no new column semantics, no schema redesign, no change to
any ownership rule.

**Verification:** `tests/agent_firm/test_firm.py::test_evaluate_async_persists_size_tier_to_agent_decisions`
(new) constructs a real decision through the real `firm.py` graph and confirms `size_tier` is
readable back from a live SQLite query against the `agent_decisions` table — not just present on
the in-memory object.

### Finding 2 (verified clean, no defect) — no legacy bypass of the ownership model

A fresh, session-wide grep for every `agent_size_hint`/`size_hint`/`size_tier` reference across the
repository found no new or reintroduced direct-write site outside `resolve_agent_size_hints()`.
`engine/trade_plan.py`, `scheduler/jobs.py`'s premarket message builder, and `engine/agent_firm/smoke.py`
all still gracefully handle `size_hint is None` (unchanged since the ADR-AF-003 session) — no crash,
no defect.

### Finding 3 (verified clean, no defect) — fail-soft behavior holds at every tested boundary

- `run_edge_veto_stage()` raising internally still fails open (inputs unchanged, no `edge_score`
  attached) and `resolve_agent_size_hints()` still produces the correct default (`1.0`) for the
  affected rows — verified through real function calls, not assumed from the function's docstring.
- Agent Firm disabled entirely (`config.is_active() == False`) still lets a real, computed
  `edge_score` drive sizing on its own (the "only edge_score present" branch), verified through the
  real `run_agent_firm_gate()` early-return path, not only via `resolve_size_hint()` called directly.
- A vetoed candidate (shadow mode, still reaching `flow_confirmed`) correctly falls through to the
  edge-score-only branch rather than any blind default — the exact historical collision ADR-AF-003
  fixed, now proven through `open_trade()` itself, not only at the row-dict level.

### Finding 4 (verified clean, no defect) — deterministic behavior

`test_full_chain_deterministic_across_repeated_runs` runs the identical scenario twice (fresh,
independently-seeded DB each time, matching how two real scan cycles would never share state) and
confirms byte-identical `agent_size_hint` and `open_trade()` lot output. `resolve_size_hint()` is a
pure function with no hidden state (confirmed by direct code read — no caching, no global mutation),
so this is expected, but is now an executable, permanent guarantee rather than an assumption.

---

## Test Results

Run via the Windows checkout's `.winvenv` interpreter (`DB_PATH=data/walkforward.db
AGENT_FIRM_ENABLED=true TAVILY_API_KEY= .winvenv/Scripts/python.exe -m pytest ...`).

| Suite | Result |
|---|---|
| `tests/agent_firm/` (excl. `providers/`) + all context-wiring/scanner/monitor/jobs + all 3 sizing test files + `tests/test_scanner_to_open_trade_integration.py` (new) + `test_migration.py` + `test_trade_plan.py` | **351 passed, 0 failed** |
| `tests/test_architecture_boundary.py`, `test_research_data_fence.py`, `test_db_centralization.py`, `security/test_route_policy.py`, `test_dashboard_signals.py` | **21 passed, 0 failed** |
| Full repository suite (`pytest -q --ignore=tests/agent_firm/providers`) | **1628 passed, 43 failed, 9 errors** |

---

## Regression Analysis

**Baseline (previous certified run, end of the ADR-AF-004 session):** 1620 passed / 44 failed / 9
errors.

**This session:** 1628 passed / 43 failed / 9 errors — a **net +8 passed, one fewer failure**.

Both deltas are fully accounted for:

- **+8 passed** = 7 new tests added this session
  (`test_evaluate_async_persists_size_tier_to_agent_decisions` +
  `tests/test_scanner_to_open_trade_integration.py`'s 6 tests) **+ 1** from the one-failure delta
  below (a previously-failing test now passing counts once in each direction).
- **44 → 43 failed:** `tests/regime/test_storage.py::test_append_only_rerun_makes_a_new_profile_id`
  passed in this session's full-suite run. Re-run in isolation immediately after
  (`pytest tests/regime/test_storage.py::test_append_only_rerun_makes_a_new_profile_id`), it
  **failed again** — confirming this is the same known-flaky, order/timing-sensitive test already
  documented across multiple prior certification passes in this repository (its own failure mode is
  a hash-based `profile_id` comparison unrelated to Agent Firm, sizing, or anything this session
  touched) — not a fix, and not a regression either direction. Zero files under `research/` or
  `tests/regime/` were touched this session.

**No new failure category appeared anywhere in the full-suite run.** Every one of the 43 failures
and 9 errors is in the same set of pre-existing Windows-local-tooling files already documented across
every prior session in this sequence (`test_value_format.py`, `security/test_release_scripts.py`,
`test_auto_token.py`, `security/test_secret_hygiene.py`, `test_config_validation.py`,
`test_cron_contract.py`, `test_logging_config.py`, `test_news_filter.py`,
`test_stockbit_fetcher_ensure_valid_token.py`, `test_experiment_tracking.py`).

**Zero regressions.**

---

## Remaining Risks

- **`AgentDecision.size_hint`'s own audit-trail completeness remains deferred** (unchanged from the
  ADR-AF-003 implementation report) — it is always persisted as `None`, by design, pending a future,
  separately-scoped change to either add a new `evaluate()` parameter (MAJOR, per ADR-AF-004) or a
  post-hoc `UPDATE` mechanism. `size_tier` (the qualitative recommendation) is now fully persisted;
  the numeric final-resolved-value is not. This is a known, documented gap, not a new risk.
- **`reset_market_ctx()` compatibility shim** — unchanged, still blocked by the same two developer
  scripts, still inert and harmless.
- **`docs/agent_firm/*.md` planning-corpus staleness** — unchanged, still explicitly deferred across
  every session in this sequence.
- **The simulated-LLM validation methodology** (this session and the prior Production Validation
  session both) does not exercise real Z.ai/Claude provider behavior — real-provider output quality
  remains validated only by `engine/agent_firm/smoke.py`'s manual Tier-4 probe, unchanged by this
  report.

None of these four items are newly introduced by this session, and none block the recommendation
below.

---

## Production-Readiness Assessment

| Dimension | Assessment |
|---|---|
| Correctness | The full chain, exercised end-to-end with real code paths, produces correct, precedence-rule-compliant sizing and correctly persists the decision that drove it (after this session's fix) |
| Robustness | Fail-soft verified at three independent boundary conditions (edge-veto exception, Agent Firm disabled, vetoed-but-shadow-mode candidate), not just asserted from docstrings |
| Auditability | **Materially improved this session** — the Risk agent's actual sizing recommendation is now part of the permanent record, closing a real gap that would have made "the system behaved correctly" unverifiable after the fact for every decision made before this fix |
| Determinism | Verified, not merely assumed, via a real repeated-run test |
| Ownership model integrity | Re-confirmed: exactly one writer of `agent_size_hint`, codebase-wide, enforced by an automated source scan |

---

## Recommendation

# GO WITH CONDITIONS

**Rationale for GO:** every objective in this validation's scope was met; the one genuine defect
found was fixed with a minimal, low-risk, additive change and is now regression-tested; zero
regressions across a 1628-test full-suite run; every ADR-AF-002/003/004 contract holds under real
(not merely unit-level) execution.

**Conditions (none newly invented — all four are already-tracked, pre-existing items, restated here
for completeness, not new blockers this validation discovered):**

1. If `agent_decisions.size_hint`'s full audit-trail completeness (the final resolved numeric value,
   not just the qualitative tier) is ever required, it needs its own separately-scoped change — do
   not attempt to bridge it with an undiscussed architecture change.
2. Continue tracking the `reset_market_ctx()` shim removal and `docs/agent_firm/*.md` corpus
   reconciliation as the already-documented, low-priority maintenance items they are.
3. Monitor `agent_decisions.size_tier`'s new data going forward (it will be `NULL` for every decision
   persisted *before* this fix shipped, and populated from this fix forward) — this is expected, not
   an anomaly, but worth noting for anyone querying historical data across the fix boundary.
4. As with every prior certification in this sequence: real-provider (Z.ai/Claude) output quality is
   validated only by the existing manual smoke probe, not by this or the prior simulated validation
   pass — continue relying on that mechanism for that specific concern.
