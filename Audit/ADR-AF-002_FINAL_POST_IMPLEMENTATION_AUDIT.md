# ADR-AF-002 — Final Post-Implementation Audit

**Date:** 2026-07-29
**Nature:** Independent verification pass over WP1 (Foundation) → WP2 (Producer Migration) →
WP3 (Consumption Migration) → WP4 (Integration Completion & Hardening), all treated as frozen,
production-ready implementation per this session's mandate. This is not a continuation of
development — every finding below was re-derived from the current repository state (fresh greps,
fresh reads, fresh test runs), not recalled from prior-session memory, and the only two edits made
are documented in §6 as genuine defects, not enhancements.
**Basis:** `docs/agent_firm/ADR-AF-002-CONTEXT_OWNERSHIP.md`; `Audit/AF2_WP1_IMPLEMENTATION_REPORT.md`
through `Audit/AF2_WP4_FINAL_CERTIFICATION.md`.

---

## 1. End-to-End Architecture Audit

**Claim to verify:** every production execution path entering the Agent Firm follows
`SignalCandidate → build_candidate_context() → Tier-1 context attached → specialists consume
candidate fields only → committee decision`, with no bypass.

**Method:** repository-wide `SignalCandidate(`/`_SC(` grep (fresh, not reused from a prior session),
then direct line-by-line read of every production match to confirm `build_candidate_context()` is
called and its result is spread into the constructor call, not merely present nearby in the file.

**Result — five live production construction sites, all verified compliant:**

| # | Site | Context call verified | Spread into constructor verified |
|---|---|---|---|
| 1 | `scheduler/scanner.py::run_agent_firm_gate()` | ✅ line 991/1006 | ✅ `**_ctx_by_ticker.get(r["ticker"], {})` |
| 2 | `scheduler/scanner.py::rank_bear_watchlist_and_notify()` | ✅ line 1089/1118 | ✅ (same pattern) |
| 3 | `scheduler/jobs.py::run_premarket_firm_scan()` | ✅ line 871/879 | ✅ `**_ctx_by_ticker.get(r["ticker"], {})` |
| 4 | `scheduler/jobs.py::run_eod_trade_plan()` | ✅ line 1055/1063 | ✅ `**_ctx_by_ticker.get(c["ticker"], {})` |
| 5 | `monitor.py::_agent_confirms_exit()` | ✅ line 39/46 | ✅ `**_ctx` |

No sixth site exists. The grep additionally matched `engine/agent_firm_context.py` (a docstring
reference to the constructor pattern, not an actual construction — confirmed by direct read) and
two non-production developer scripts (`scripts/probe_actual_http_concurrency.py`,
`scripts/replay_firm_offline_run.py` — manual diagnostic harnesses, hardcoded personal paths,
not part of any scheduled or triggered execution path), plus test fixtures (which construct
candidates directly as test data, not part of the live call graph).

**Verdict: no remaining bypass.** This matches `Audit/AF2_WP4_CALL_GRAPH_REPORT.md`'s own recorded
state exactly, independently re-confirmed here rather than assumed.

---

## 2. Architectural Invariants

| Invariant | Verification method | Result |
|---|---|---|
| No specialist performs SQL/data retrieval | `grep -r "sqlite_query\|\.execute(\|db_connect\|sqlite3.connect" engine/agent_firm/agents/` | **Zero matches** — confirmed clean across all 7 agent files (technical, flow, regime, news, risk, bull, bear) |
| No specialist reconstructs Tier-1 facts | Re-read all 5 specialist prompts (technical_v1.md, flow_v1.md, regime_v1.md, news_v1.md, risk_v2.md) fresh | Every "calculate/derive/threshold" match found is guardrail language ("do not recompute/re-derive X"), not a derivation instruction. Confirmed clean |
| No duplicate context builders | `grep -rn "^def build_.*_context"` across the whole repo | All 9 Tier-1/Tier-2 builders live solely in `engine/agent_firm_context.py`. Four unrelated `build_*` functions found elsewhere (`build_news_block`, `build_market_health_report`, `build_regime_features`, `build_risk_summary_message`) are differently-named, differently-purposed (message formatting, research feature engineering) — no naming collision, no duplication |
| No legacy `_build_context()` implementation remains | `grep -rn "def _build_context"` | **Zero matches anywhere in the repository** — confirmed fully removed (WP3), re-confirmed here |
| No production path bypasses Context Producer | See §1 | 5/5 sites verified compliant |
| Research ↔ production boundary intact | Re-ran `test_architecture_boundary.py`, `test_research_data_fence.py`, `test_db_centralization.py`, `security/test_route_policy.py` fresh | **13/13 passed.** Zero `research/` files touched this session |

**Verdict: all six invariants hold**, independently re-verified.

---

## 3. Dead-Code Audit

| Item | Classification | Basis |
|---|---|---|
| `reset_market_ctx()` (`engine/agent_firm/firm.py`) | **Blocked** | Re-confirmed 7 call sites (5 production, all no-ops since `_build_context()`'s deletion; 2 developer scripts, `scripts/probe_actual_http_concurrency.py` and `scripts/replay_firm_offline_run.py`, calling it directly and unconditionally). Cannot be removed without also editing those two scripts, which sit outside this and every prior work package's stated focus. Unchanged since WP4's assessment. |
| `AgentState.db_path`/`.context` (`engine/agent_firm/schemas.py`) | **Intentional compatibility** | Confirmed still unused (`firm.py` never reads `state["db_path"]`/`state["context"]`); left in place because this and every prior session's mandate excludes schema changes |
| `SessionContext`/`build_session_context()` | **Intentional compatibility** | Builder exists and is unit-tested (`tests/test_agent_firm_context.py`), but has no `SignalCandidate` attach point — a deliberate, documented future-work placeholder (would need its own ADR amendment to add a `session` field), not orphaned dead code |
| `ConsensusContext` / `build_consensus_summary()` | **Intentional compatibility** | Type exists, builder was never implemented, no evaluation-graph attach point. Confirmed unchanged since WP1; building it now would be new Tier 2 functionality, explicitly out of every session's "no feature additions" constraint |
| `OpportunityContext` | **N/A — does not exist** | Zero matches anywhere in the codebase (not even a class definition); named only in ADR prose |
| `engine/agent_firm/firm.py`'s `import time` | Already removed (WP4) | Re-confirmed absent |
| `scheduler/jobs.py`'s unused `_load_ohlcv_bulk` import | **Blocked / out of mandate** | Pre-dates WP1-4, unrelated to Agent Firm context work, sits in a large shared production job file — re-confirmed present, correctly left untouched |
| `scheduler/scanner.py`'s unused `sqlite3`/`_sqlite3` imports | **Blocked / out of mandate** | Same reasoning; re-confirmed present |

**No new dead code found.** Nothing was removed this session (per the brief's "do not remove
anything unless absolutely safe" — the one removable item, `firm.py`'s `import time`, was already
removed in WP4).

---

## 4. Runtime Correctness Audit

- **Scheduler** (`scheduler/jobs.py`, `scheduler/scanner.py`): both files' five... wait, four
  candidate-construction sites between them (2 each — see §1) directly re-read and confirmed to
  build context before construction, with fail-open error handling around the context-build step in
  every case (a broken/unreadable DB degrades to no context, never blocks the job).
- **Monitor** (`monitor.py`): `_agent_confirms_exit()` re-read and confirmed; its own cache-flush
  (`reset_market_ctx()` + `reset_batch_context()`) runs immediately before context building, treating
  each invocation as its own cycle boundary (correct, since this function runs independently of the
  scheduler's own scan-cycle boundary, every ~30 minutes).
- **Scanner**: `run_agent_firm_gate()`/`rank_bear_watchlist_and_notify()` re-verified — both correct,
  unchanged since WP2/WP4.
- **`paper_trade.py`**: confirmed it does **not** invoke the Agent Firm at all (zero matches for
  `agent_firm`/`SignalCandidate`/`evaluate` in the file) — it is correctly a pure data/execution
  layer that `build_risk_context()`/`build_execution_context()` read from, not a candidate-
  construction site. No bypass risk here because there is no Agent Firm call to bypass.
- **Smoke tests**: `engine/agent_firm/smoke.py::_build_canned_candidate()` invoked directly against
  the real project DB this session — confirmed it successfully populates `technical`/`flow`/
  `portfolio` (all non-`None`) rather than silently degrading. `python -m engine.agent_firm.smoke`
  run with `AGENT_FIRM_ENABLED=false` confirmed to skip cleanly (`SKIP: agent firm not active`) with
  no exception.
- **Full Agent-Firm-adjacent test surface re-run fresh this session**: `tests/agent_firm/` +
  `test_agent_firm_context.py` + `test_agent_firm_context_wiring.py` +
  `test_scheduler_jobs_context_wiring.py` + `test_monitor_exit_review.py` +
  `test_scheduler_firm_hook.py` + `test_agent_size_hint.py` + `test_bear_watchlist_ranking.py` +
  `test_nr7_live_pipeline_e2e.py` + `test_premarket_firm_scan.py` + `test_eod_trade_plan_job.py` —
  **246 passed, 0 failed**, matching WP4's own recorded result exactly, independently re-run rather
  than assumed still true.

**Verdict: every Agent Firm invocation in the live system receives fully populated Tier-1 context**,
fail-open to typed defaults on any DB error, confirmed by direct code read and by test execution,
not by documentation review alone.

---

## 5. Documentation Consistency

**Finding — three stale docstrings, confirmed and corrected as genuine defects** (see §6 for the
exact diffs): `scheduler/scanner.py::run_agent_firm_gate()`'s and
`::rank_bear_watchlist_and_notify()`'s docstrings, and `engine/agent_firm_context.py`'s module
docstring, all still asserted the WP2-era claim "nothing in the evaluation graph reads these fields
yet... producer wiring only, no change to decision/ranking behavior." This became false the moment
WP3 wired specialist consumption, and was never updated — a genuine, misleading inconsistency
between code comments and actual current behavior, exactly the class of drift CLAUDE.md's own
Decision-Making Hierarchy principle #1 warns about ("documents self-report, tests verify"). Fixed —
see §6. This is a comment-only correction with zero functional impact, re-verified by a full
targeted test re-run (70 passed) and the full-suite run (§7).

**`ADR-AF-002` itself:** re-read in full. Its "Required Implementation Changes... (for AF-2, not
performed by this ADR)" section is accurate as written — it correctly scopes itself as a decision
record, not an implementation-status tracker, and does not claim any work is still pending. No edit
needed or made; ADRs in this repository are frozen-by-design and amended only via a dated
superseding entry, never silently.

**`CLAUDE.md`:** contains no false claim about the Agent Firm (its one "Agent firm" glossary line
remains accurate), but is entirely silent on the ADR-AF-00x Tier-1 context pipeline — a
completeness gap, not a defect (nothing asserted is wrong). `CLAUDE.md` is explicitly versioned and
marked `FROZEN`, amended only via its own documented, dated-amendment convention (as it already has
been once, 2026-07-28). Adding that amendment is a larger, more consequential documentation decision
than this audit's mandate covers — **recommended as a follow-up, not performed here.**

**`docs/agent_firm/*.md` governance/planning corpus (23 files):** re-confirmed to predate the
actual delivered WP1-4 re-scoping (Foundation/Producer-Migration/Consumption-Migration/Integration-
Completion), consistent with `Audit/AF2_WP2_IMPLEMENTATION_REPORT.md`'s own explicit deferral
("Full documentation reconciliation deferred... distinct from this specific wiring task"). This
session re-confirms that deferral is still the accurate, current state — not silently resolved,
not newly broken, genuinely out of proportion for a final audit to absorb (reconciling ~20+ planning
documents against four work packages' worth of actual delivery is its own work package, already
named — under its stale numbering — as "WP7" in `AF2_WORK_PACKAGE_SEQUENCE.md`).

---

## 6. Defects Found and Fixed This Session

Per this audit's mandate ("assume frozen unless a genuine defect is found"), exactly one class of
defect was found — stale documentation asserting a factually false claim about current system
behavior — and fixed, comment-only, zero functional risk:

| File | What changed |
|---|---|
| `scheduler/scanner.py::run_agent_firm_gate()` docstring | Removed the false "nothing in the evaluation graph reads these fields yet" claim; states the context population is now load-bearing for decision output (AF-2 WP3) |
| `scheduler/scanner.py::rank_bear_watchlist_and_notify()` docstring | Same correction, ranking-specific wording |
| `engine/agent_firm_context.py` module docstring | Replaced the stale WP1/WP2-only status paragraph with a current, accurate one-paragraph status naming all five live construction sites and the specialist-consumption fact, pointing to the full WP1-4 audit trail |

No other file was modified this session. No test file was modified. No production behavior changed
— every edit is a comment/docstring only, verified by an unchanged full-suite result (§7).

---

## 7. Test Summary

| Suite | Result |
|---|---|
| Full Agent-Firm-adjacent surface (11 files), re-run fresh | **246 passed, 0 failed** |
| Architecture boundary / research fence / DB centralization / route policy, re-run fresh | **13 passed, 0 failed** |
| Targeted re-run after the 3 docstring fixes | **70 passed, 0 failed** |
| Full repository suite (`pytest -q --ignore=tests/agent_firm/providers`), re-run fresh, post-fix | **1564 passed, 44 failed, 9 errors** — **byte-for-byte identical failure/error set to WP4's own recorded baseline** (same files: `test_value_format.py`, `security/test_release_scripts.py`, `test_auto_token.py`, `security/test_secret_hygiene.py`, `test_config_validation.py`, `test_cron_contract.py`, `test_logging_config.py`, `test_news_filter.py`, `test_stockbit_fetcher_ensure_valid_token.py`, `test_experiment_tracking.py`, `regime/test_storage.py` — all pre-existing Windows-local-tooling artifacts, none touching this session's two edited files) |

**Zero regressions.** The full-suite number is unchanged to the test from WP4's own certification,
confirming the documentation fixes made this session carry no functional weight whatsoever.

---

## 8. Overall Verdict

**ADR-AF-002 is fully implemented and independently verified.** Every production execution path
entering the Agent Firm — five live construction sites across `scheduler/scanner.py`,
`scheduler/jobs.py`, and `monitor.py` — follows the mandated
`SignalCandidate → build_candidate_context() → Tier-1 context attached → specialists consume
candidate fields only → committee decision` flow with no bypass, no duplicate builder, no
SQL/data-retrieval inside any specialist, and no legacy `_build_context()` remnant anywhere in the
repository. The research/production boundary remains intact. The only residual items are (a) an
inert, harmless compatibility shim (`reset_market_ctx()`) blocked from removal by two non-production
developer scripts, and (b) `ConsensusContext`/`SessionContext`/`OpportunityContext`, deliberately
unbuilt Tier 2 / no-attach-point placeholders that were never in scope for WP1-4's Tier 1 mandate —
neither is a defect, both are already-documented, explicitly-deferred boundaries, re-confirmed
unchanged.

**This audit's own contribution:** found and corrected three stale docstrings that had drifted from
"accurate WP2-era snapshot" to "actively misleading about current WP3/WP4 behavior" — a genuine,
if low-severity, defect, fixed with zero functional risk and a re-verified unchanged full-suite
result.

**Recommendation: GO WITH CONDITIONS — unchanged from `Audit/AF2_WP4_FINAL_CERTIFICATION.md`,
re-affirmed rather than newly imposed.** This audit introduces no new condition: it found nothing
that downgrades WP4's own verdict, and the one defect found (stale docstrings) is fixed with zero
functional risk. The conditions remain exactly what WP4 already named — monitor the premarket/EOD/
exit-review decision-distribution shift post-deploy; file the `reset_market_ctx()` cleanup (drop the
call from all 7 sites, delete the function, update the 2 developer scripts) as its own small,
separately-reviewed follow-up; keep `ConsensusContext` explicitly backlogged rather than silently
forgotten. None of these block shipping — the core ADR-AF-002 Tier 1 pipeline is complete, tested,
and independently verified.
