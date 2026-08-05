# ADR-AF-003 (Sizing Ownership) — Implementation Report

**Date:** 2026-07-29
**Basis:** `docs/agent_firm/ADR-AF-003-SIZING_OWNERSHIP.md` (Status: DECIDED, permanent) — treated
as the authoritative, exact specification for this change, per this task's own instruction. No
architecture decision was revisited; this report documents implementation of an already-approved
design.

---

## Summary

`ADR-AF-003` documented a confirmed, currently-shipped defect: `scheduler/scanner.py` had two
independent, unconditional writers of `r["agent_size_hint"]` — `run_edge_veto_stage()`'s
deterministic `size_mult` (from `engine/edge_score.py::compute_edge()`, gated on
`EDGE_SCORE_MODE=enforce`) and `run_agent_firm_gate()`'s LLM-derived `size_hint`-or-blind-`1.0`
(gated only on the Agent Firm being active at all). The second always ran after and unconditionally
overwrote the first, silently discarding a computed, validated edge score whenever both were active
simultaneously.

This change eliminates the collision structurally, not by picking a winner: `engine/position_sizing.py::resolve_size_hint()`
is now the sole writer of `agent_size_hint` in the entire codebase, called exactly once per candidate
after both stages have contributed their inputs (`edge_score`, `agent_size_tier`).

---

## Files Modified

| File | Nature of change |
|---|---|
| `engine/position_sizing.py` | **New.** `resolve_size_hint()` — the sole authority for `agent_size_hint`, implementing ADR-AF-003's exact 4-branch precedence rule |
| `scheduler/scanner.py` | `run_edge_veto_stage()`: removed its direct `agent_size_hint` write (kept `edge_score`, unchanged). `run_agent_firm_gate()`: replaced its `_size_map`/blind-default write with a `_tier_map` that attaches `agent_size_tier` only (no numeric write). New function `resolve_agent_size_hints()`: the single call site, invoked once in `scheduled_multi_strategy_scan()` after both stages have run |
| `engine/agent_firm/firm.py` | `_run_risk()`: reads `size_tier` from the Risk agent's JSON output instead of `size_hint`; the guardrail-override path clears `size_tier` (was: zeroed `size_hint`); `AgentDecision.size_hint` is now always constructed as `None` (see "Deferred: Audit-Trail Completeness" below) |
| `engine/agent_firm/prompts/risk_v2.md` | Output schema changed from `"size_hint": 0.0-1.5` to `"size_tier": "reduce"\|"normal"\|"increase"`; decision framework's sizing guidance rewritten in tier language |
| `engine/agent_firm/schemas.py` | `AgentDecision.size_hint`/`.size_tier` docstrings updated to describe the new ownership (no field type or presence change — both remain `Optional`, same types) |
| `tests/agent_firm/test_risk.py`, `test_risk_v2.py`, `test_firm.py`, `test_firm_v2.py` | Mocked Risk-agent JSON payloads updated from `size_hint` to `size_tier`; the guardrail-override test's assertion updated from `size_hint == 0.0` to `size_tier is None` / `size_hint is None` |
| `tests/test_agent_size_hint.py` | The three "gate attaches sizing" tests renamed/rewritten to assert `agent_size_tier` (unit-level, what the gate itself does); three new tests added exercising gate + `resolve_agent_size_hints()` together, reproducing the same three scenarios end-to-end |
| `tests/test_position_sizing.py` | **New.** Exhaustive precedence-path + boundary-case unit tests for `resolve_size_hint()` |
| `tests/test_sizing_collision_regression.py` | **New.** The B2 regression test — reproduces the exact "both `EDGE_SCORE_MODE=enforce` and Agent Firm active" collision scenario end-to-end through the real `scheduler.scanner` functions, proving neither signal is discarded |
| `tests/test_sizing_single_writer_invariant.py` | **New.** Source-scan invariant test (same convention as `test_architecture_boundary.py`) proving exactly one `agent_size_hint` assignment exists anywhere in the production codebase |

**Not touched:** `engine/agent_firm/agents/risk.py` (pure JSON passthrough, no field-specific logic — required no change), `engine/agent_firm/guardrails.py` (its `apply_guardrails()` never touched sizing, only `decision`/`confidence` — required no change), any database schema, `research/`, `paper_trade.py`, any file outside the sizing-collision surface.

---

## How Each ADR-AF-003 Requirement Was Satisfied

| ADR-AF-003 requirement | Satisfied by |
|---|---|
| "Production Engine owns executable sizing, in a single new module: `engine/position_sizing.py`" | Created, at the exact specified path |
| "`resolve_size_hint()` is the only code in the entire codebase permitted to write a final numeric value into `agent_size_hint`" | Verified by `tests/test_sizing_single_writer_invariant.py`'s source scan — exactly one assignment site, inside `resolve_agent_size_hints()`, which delegates to `resolve_size_hint()` |
| "`scanner.py:962` and `scanner.py:1013`'s current direct-write lines are both removed and replaced by exactly one call site" | Both removed; the one call site is `resolve_agent_size_hints(flow_confirmed)`, called once in `scheduled_multi_strategy_scan()` after `run_agent_firm_gate()` returns |
| "The Risk agent's LLM output changes from a numeric `size_hint` to a qualitative `size_tier`" | `risk_v2.md`'s output schema and decision framework updated; `firm.py::_run_risk()` reads `size_tier` |
| Exact `resolve_size_hint()` signature (`edge_score`, `size_tier`, `consensus`, `execution` → `float`) | Implemented verbatim, including accepting but not combining `consensus`/`execution` (see "Deviations" below) |
| Exact 4-branch precedence rule (both present → modulate; edge_score-only → passthrough; size_tier-only → fixed base; neither → 1.0 default) | Implemented verbatim in `resolve_size_hint()`; every branch covered by `tests/test_position_sizing.py` |
| "Bounded [0.0, 1.5] by construction" | `_clamp()` applied on every return path; verified by boundary tests exceeding both ends |
| "This function is called exactly once per candidate, after both `run_edge_veto_stage()` and `run_agent_firm_gate()` have run" | `resolve_agent_size_hints()`'s one call site sits strictly after both, before Step 7's `open_trade()` loop reads the result |
| "No silent overwrite is permitted... never a second write silently clobbering a first" | Verified directly by `tests/test_sizing_collision_regression.py`'s B2 regression suite, reproducing the exact documented collision scenario and asserting both signals are reflected in the output |
| Deterministic regardless of `EDGE_SCORE_MODE`/Agent Firm state | `resolve_size_hint()` is a pure function of its two inputs; every combination of "mode present/absent" is covered by the B2 regression tests and the precedence-path unit tests |
| "`AgentDecision.size_hint`... repurposed... carries the final resolved value... for audit-trail completeness" | **Partially — see "Deviation" below.** The type/field-presence contract is unchanged (still `Optional[float]`); `firm.py` now always constructs it as `None` rather than a stale raw LLM number, but does not retroactively populate it with `resolve_size_hint()`'s scanner-side output |

---

## Deviation: Deferred Audit-Trail Completeness (documented, not silently done)

ADR-AF-003's "Consequences" section states `AgentDecision.size_hint` should carry
"the final resolved value `resolve_size_hint()` produced for this candidate, for audit-trail
completeness in `agent_decisions`." This is **not fully implemented** by this change, and the
reason is structural, not an oversight:

`resolve_size_hint()` runs in `scheduler/scanner.py` (Production Engine), inside
`scheduled_multi_strategy_scan()`, strictly **after** `firm.evaluate_staged()` has already returned
— and `firm.py`'s own internal graph persists every `AgentDecision` to the `agent_decisions` table
(via its `persist` node) **before** `run_agent_firm_gate()` (the caller) ever receives the decision
objects back. By the time scanner.py computes the final sizing value, the corresponding
`agent_decisions` row is already written. Making the persisted row reflect the later-computed value
would require either (a) passing `edge_score` into the Agent Firm's own evaluation call — a new
`SignalCandidate`/`evaluate()` parameter or context field, which `ADR-AF-004` classifies as a MAJOR,
architecture-level change — or (b) a new mechanism for Production Engine to update an
already-persisted, Agent-Firm-owned table row after the fact, which is not described anywhere in
ADR-AF-003's own "Required Implementation Changes" section (the literal scope for this
implementation pass, as distinct from its "Decision"/"Consequences" prose).

**Given ADR-AF-003's own "Required Implementation Changes" section — the explicit checklist for
what this pass must do — lists only**: create `position_sizing.py`, delete the two scanner.py write
sites and add one call site, update `risk_v2.md`'s schema, and add the B2 regression test. **None of
these four items requires touching `firm.py::_persist()` or `evaluate()`'s signature.** Closing the
audit-trail loop is therefore treated as a distinctly-scoped follow-up (matching this repository's
own established pattern — e.g. `ConsensusContext`/`SessionContext` were left as documented,
unbuilt gaps rather than triggering an undiscussed architecture expansion during ADR-AF-002's
implementation). `AgentDecision.size_hint` is `None` at construction time in every case now (never a
stale raw LLM number); `size_tier` carries the Risk agent's actual qualitative recommendation.

**Consequence for existing consumers, verified, not assumed:** `engine/trade_plan.py::rank_approved()`/`fallback_rank()`
and `scheduler/jobs.py`'s premarket message builder both already handle `d.size_hint is None`
gracefully (confirmed by direct code read — `rank_approved()`'s own line, `c["size_hint"] = float(d.size_hint)
if d.size_hint is not None else None`, and the premarket builder's `f" ×{d.size_hint:.2f}" if d.size_hint else ""`)
— this was already the exact fail-soft pattern used for degraded/bypassed decisions before this
change. The EOD/premarket Telegram reports will now display no size-hint figure for every decision
rather than the LLM's raw number; this is a direct, ADR-authorized consequence of "no longer carries
the LLM's raw recommendation," not a defect. No crash, no exception, in either consumer.

**Recommended follow-up** (not performed by this change, flagged rather than silently left for
someone to rediscover): if the `agent_decisions.size_hint` audit trail needs to reflect the final
resolved value, the minimal correct approach is a targeted `UPDATE agent_decisions SET size_hint = ?
WHERE id = ?` issued from `resolve_agent_size_hints()`'s call site, keyed by whatever decision-id
`run_agent_firm_gate()` can be made to expose — a small, separate, reviewable change, not bundled
into this one.

---

## Test Results

Run via the Windows checkout's `.winvenv` interpreter (`DB_PATH=data/walkforward.db
AGENT_FIRM_ENABLED=true TAVILY_API_KEY= .winvenv/Scripts/python.exe -m pytest ...`).

| Suite | Result |
|---|---|
| `tests/agent_firm/` (excl. `providers/`) + all context-wiring + scanner/monitor/jobs + `test_agent_size_hint.py` + all 3 new sizing test files + `test_trade_plan.py` | **333 passed, 0 failed** |
| `tests/test_architecture_boundary.py`, `test_research_data_fence.py`, `test_db_centralization.py`, `security/test_route_policy.py`, `test_dashboard_signals.py` | **21 passed, 0 failed** |
| Full repository suite (`pytest -q --ignore=tests/agent_firm/providers`) | **1609 passed, 44 failed, 9 errors** — **identical 44-failed/9-error set** to every prior ADR-AF-002-sequence baseline (same files: `test_value_format.py`, `security/test_release_scripts.py`, `test_auto_token.py`, `security/test_secret_hygiene.py`, `test_config_validation.py`, `test_cron_contract.py`, `test_logging_config.py`, `test_news_filter.py`, `test_stockbit_fetcher_ensure_valid_token.py`, `test_experiment_tracking.py`, `regime/test_storage.py` — all pre-existing Windows-local-tooling artifacts, none touching sizing/scanner/firm code); **+45 passed** vs. the prior baseline of 1564, exactly the 45 new tests this change added (33 + 5 + 4 + 3) |

**Zero regressions.**

---

## Confirmation: The Duplicate-Writer Defect Is Eliminated

- **Structurally**: `tests/test_sizing_single_writer_invariant.py` proves, by source scan (not by
  example), that exactly one `agent_size_hint` assignment exists in the entire production codebase.
- **Behaviorally**: `tests/test_sizing_collision_regression.py` reproduces the exact documented
  collision (`EDGE_SCORE_MODE=enforce` + Agent Firm both active for the same candidate) through the
  real `scheduler.scanner` functions and proves the final value is a function of *both* inputs —
  `reduce`/`normal`/`increase` tiers produce measurably different results from the same `edge_score`,
  and a vetoed/no-tier candidate correctly falls through to the edge-score-only branch instead of the
  old blind `1.0` default that used to discard it.
- **Preserved semantics**: the pre-existing default (`1.0`, neither signal present) and the
  fixed tier-to-value mapping (`reduce`→0.5, `normal`→1.0, `increase`→1.2 — the exact numbers
  `risk_v2.md` used to hardcode) are unchanged, confirmed by `test_gate_then_resolve_approved_signal_gets_tier_based_size_hint`
  reproducing the pre-ADR-AF-003 numeric outcome for the no-edge-score case.
