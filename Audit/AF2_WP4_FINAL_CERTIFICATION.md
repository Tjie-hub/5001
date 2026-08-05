# ADR-AF-002 — Final Completion Certification (AF-2 WP4)

**Date:** 2026-07-29
**Authority:** This document, per this repository's own Decision-Making Hierarchy convention for
generated/point-in-time certification records — superseded by a later certification if further
work packages touch this surface, never silently edited.
**Scope certified:** `docs/agent_firm/ADR-AF-002-CONTEXT_OWNERSHIP.md`'s Tier 1 context-ownership
mandate, as delivered across WP1 (Foundation) → WP2 (Producer Migration) → WP3 (Consumption
Migration) → WP4 (this work package — audit, integration completion, hardening).

---

## 1. ADR Compliance

| ADR-AF-002 requirement | Status |
|---|---|
| Tier 1 objects (`TechnicalContext`, `FlowContext`, `RegimeContext`, `NewsContext`, `MarketContext`, `PortfolioContext`, `RiskContext`, `ExecutionContext`) constructed by Production Engine, before Agent Firm evaluation | **Met** — `engine/agent_firm_context.py`, unchanged since WP2 |
| Assembly lives outside `engine/agent_firm/`, visible in the file tree | **Met** — `engine/agent_firm_context.py` at `engine/` top level, unchanged |
| Every live construction site attaches Tier 1 context before calling `evaluate`/`evaluate_staged` | **Met as of this WP** — was true for 2 of 5 live sites before WP4 (scanner.py only); now true for all 5 |
| `_build_context()` deleted, not replaced in place | **Met** — done in WP3, re-confirmed still gone |
| `evaluate`/`evaluate_staged` receive already-assembled context attached to `SignalCandidate`, no internal context-building | **Met** — `firm.py`'s graph reads only `candidate.<field>`, confirmed unchanged this WP |
| Tier 2 (`ConsensusContext`) assembled by Agent Firm itself, post-analyst, pre-risk | **Not met** — no builder exists (`guardrails.py::build_consensus_summary()` was never implemented); inherited gap from WP1, not created or worsened by WP2/WP3/WP4, and explicitly out of this WP's mandate to build (see Technical Debt Report item 7) |
| Context objects ephemeral, never persisted | **Met** — no new persistence path introduced anywhere in WP1-4 |
| Batch-level Tier 1 objects cached once per scan cycle | **Met, extended this WP** — the three newly-wired call sites each now correctly treat their own invocation as its own cycle boundary (see Call Graph Report) |

**Verdict on ADR-AF-002 compliance: substantially complete.** The ADR's Tier 1 mandate — the part
that governs what production actually ships today — is now fully realized across every live call
site. The one unmet clause (Tier 2 `ConsensusContext`) was never in active use by any shipped
analyst node in any of WP1-3 either, and building it now would be new functionality, not completion
of existing wiring — explicitly excluded by this WP's "no architecture expansion" constraint.

---

## 2. Architecture Verification

- **Research/production boundary**: untouched. Zero files under `research/` read or modified this
  session. `tests/test_architecture_boundary.py`/`test_research_data_fence.py`: **13/13 passed**.
- **No database schema change**: confirmed by `git diff` — no `CREATE TABLE`/`ALTER TABLE` in any
  file this WP touched.
- **No new context type, builder, or agent**: confirmed — every fix reuses
  `engine.agent_firm_context.build_candidate_context()` verbatim; zero new Pydantic models; zero new
  files under `engine/agent_firm/agents/`.
- **Specialist consumption unchanged**: every analyst/researcher/risk node still reads exactly the
  `candidate.<field>` set WP3 established; verified by the full `tests/agent_firm/` suite passing
  unchanged (**75+37 = 112 of the 246 passed** in the combined run belong to that surface).
- **Call graph**: fully enumerated in `Audit/AF2_WP4_CALL_GRAPH_REPORT.md` — five live production
  construction sites, all now context-aware; two non-production developer scripts, deliberately left
  as-is (diagnostic tools, not part of the decision-making system).

---

## 3. Remaining Compatibility Debt

| Item | Blocking factor | Risk if left as-is | Recommended follow-up |
|---|---|---|---|
| `reset_market_ctx()` shim (`engine/agent_firm/firm.py`) | `scripts/probe_actual_http_concurrency.py`, `scripts/replay_firm_offline_run.py` still call it directly | **None** — the function is a pure no-op; every production call site pays a negligible, harmless cost | Dedicated small change: drop the call from all 7 sites, delete the function + its docstring reference, update the 2 scripts. Not performed here (touches `scripts/`, outside this WP's stated focus) |
| `ConsensusContext` unbuilt (Tier 2) | No builder, no analyst-node attach point exists yet | **None currently** — nothing expects this data; not a regression, a documented future-work item since WP1 | Would need its own dated ADR amendment / work package if ever prioritized — not a WP4 blocker |
| `AgentState.db_path`/`.context` unused `TypedDict` keys | `schemas.py` out of WP3/WP4 mandate | **None** — inert fields, zero runtime cost | Bundle with any future `schemas.py`-touching change |
| Two unrelated pre-existing unused imports (`scheduler/jobs.py`, `scheduler/scanner.py`) | Out of Agent-Firm-context mandate | **None** — cosmetic only | General hygiene pass, unrelated to ADR-AF-002 |

None of these four items block a GO recommendation — each is either genuinely inert or explicitly
out of scope by the ADR's own tiering (Tier 2 vs. Tier 1) or this session's stated mandate.

---

## 4. Removed Legacy Components

| Component | Removed | Reason |
|---|---|---|
| `engine/agent_firm/firm.py::_build_context()` | WP3 (re-confirmed gone this WP) | Superseded by Tier 1 producer wiring per `ADR-AF-002` |
| `"build_context"` LangGraph node | WP3 (re-confirmed gone this WP) | Its sole producer function was deleted |
| `engine/agent_firm/firm.py`'s unused `import time` | **This WP** | Genuinely dead, zero behavior change |
| `reset_market_ctx()` | **Not removed** | Blocked — see §3 |

---

## 5. Test Summary

| Suite | Result |
|---|---|
| Full Agent Firm + scheduler/scanner/monitor integration surface (11 files, incl. 2 new) | **246 passed, 0 failed** |
| Architecture boundary / research data fence / DB centralization / route policy | **13 passed, 0 failed** |
| Full repository suite (`pytest -q --ignore=tests/agent_firm/providers`) | **1564 passed, 44 failed, 9 errors** — **identical failure/error set to the WP3 baseline** (same files: `test_value_format.py`, `security/test_release_scripts.py`, `test_auto_token.py`, `security/test_secret_hygiene.py`, `test_config_validation.py`, `test_cron_contract.py`, `test_logging_config.py`, `test_news_filter.py`, `test_stockbit_fetcher_ensure_valid_token.py`, `test_experiment_tracking.py`, `regime/test_storage.py` — all pre-existing Windows-local-tooling artifacts, none touching `agent_firm`/`scanner`/`paper_trade`/`SignalCandidate`/`monitor`); **+4 passed**, exactly the 4 new regression tests this WP added |

**Zero new failures introduced by this work package**, confirmed by direct before/after comparison
against `Audit/AF2_WP3_IMPLEMENTATION_REPORT.md`'s own recorded baseline.

---

## 6. Risk Assessment

**This work package changes real production decision behavior**, not merely internal plumbing —
this is the honest risk to name plainly. Before WP4, the premarket shortlist (08:35), the EOD trade
plan (16:40), and the intraday exit-review gate all evaluated every candidate with the Technical/
Flow/Regime/News specialists receiving **no** grounding data (`None` → typed-default fallback),
meaning those three call sites' Agent Firm decisions were effectively driven by whatever the
LLM inferred from a bare ticker/strategy/score/regime tag — the four specialists were unable to
disagree, confirm, or contradict anything, since they had nothing concrete to reason about beyond
the quant pipeline's own already-computed regime/flow_verdict/score fields (not the same as the
Tier 1 context objects a "confirm or challenge" design assumes). After WP4, these same three call
sites give every specialist the same real, structured grounding the intraday scan gate has had
since WP2 — this is very likely to shift the *distribution* of approve/veto/confidence outcomes for
premarket, EOD, and exit-review decisions, in the direction the Agent Firm was actually designed to
produce (better-grounded, not necessarily more permissive or more restrictive in either direction).

This mirrors the precedent already accepted in `Audit/AF2_WP3_REGRESSION_REPORT.md` (the Risk
Manager's open-position-veto gap-closure) — a documented, foreseeable, intentional behavior
correction, not an anomaly, and not gated behind a shadow/enforce toggle because (a) `ADR-AF-002`
already specifies this wiring as fail-open/backward-compatible-safe by construction (context-build
failure degrades to the pre-WP4 empty-default shape, never blocks or crashes), and (b) WP2's
identical wiring pattern at `scanner.py`'s two sites shipped the same way, without incident, setting
the accepted precedent for this exact class of change in this codebase.

**Residual risk, scoped:**
- **Decision-distribution shift** (see above) — not a defect, the intended effect; operators should
  watch `agent_decisions.decision`/`.confidence` distributions for the `premarket`/`eod` strategies
  and the exit-review path in the days after deploy, per the same operator guidance
  `AF2_WP3_REGRESSION_REPORT.md` gave for its own behavior change.
- **One additional DB round-trip per candidate per job/tick** at the three newly-wired sites —
  `SELECT`-only, using the already-centralized `data.db.connect()`, same cost profile WP2 already
  accepted for `scanner.py`'s two sites; not measured under production load, flagged for
  observation, not treated as blocking (matches WP2's own stated posture on this exact cost).
- **`get_market_risk_for_circuit_breaker()` de-duplication in `run_premarket_firm_scan()`** — a
  behavior-preserving refactor (same value, computed once instead of twice) verified by the existing
  dedup-guard test continuing to pass unchanged; low risk.
- **No risk from the compatibility debt in §3** — each item is inert.

---

## 7. Recommendation

# GO WITH CONDITIONS

**Conditions:**
1. **Monitor** `agent_decisions` outcome distribution for `strategy IN ('premarket','eod')` and the
   exit-review path for 1-2 weeks post-deploy, watching specifically for the expected shift toward
   better-grounded (not necessarily more or less permissive) approve/veto/confidence outcomes — same
   operator discipline already established for WP3's Risk Manager change.
2. **File the proposed minimal follow-up** (Technical Debt Report §1) to remove `reset_market_ctx()`
   and its seven call sites, plus the two developer scripts, as its own small, separately-reviewed
   change — not a blocker to shipping this work package.
3. **`ConsensusContext` remains explicitly backlogged**, not silently dropped — any future work
   package that wants to build it starts from a known, documented, unbuilt state, not a rediscovery.

None of these conditions block shipping WP4 itself — all are follow-up hygiene or observation, not
prerequisites. The core deliverable (closing a real, live, three-call-site correctness gap in the
Agent Firm's Tier 1 context pipeline, using only already-approved, already-shipped machinery, with
zero new test regressions across a 1564-test full-suite run) is complete, tested, and safe to ship.
