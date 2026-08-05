# AF-2 Readiness Certification

**Date:** 2026-07-29
**Basis:** every AF-1 document in `docs/agent_firm/` (the 2026-07-28 six: `AGENT_FIRM_ARCHITECTURE.md`,
`AGENT_FIRM_DEPENDENCY_AUDIT.md`, `AGENT_FIRM_GOVERNANCE.md`, `AGENT_FIRM_IMPLEMENTATION_ROADMAP.md`,
`AGENT_FIRM_INTERFACE_SPEC.md`, `AGENT_FIRM_MIGRATION_PLAN.md`; the 2026-07-28 AF-1 decision set:
`AF1_SCHEMA_OWNERSHIP_DECISION.md`, `AF1_CONTEXT_API.md`, `AF1_DATA_ACCESS_LAYER.md`,
`AF1_RESPONSIBILITY_MATRIX.md`, `AF1_FAILURE_CONTRACT.md`, `AF1_IMPLEMENTATION_SPEC.md`; and the
2026-07-29 computation-boundary set: `AF1_DETERMINISTIC_COMPUTATION_AUDIT.md`,
`AF1_COMPUTATION_BOUNDARY_POLICY.md`, `AF1_REQUIRED_CONTEXT_OBJECTS.md`, `AF1_REMEDIATION_PLAN.md`,
`AF1_IMPLEMENTATION_BACKLOG.md`, `AF1_CONTEXT_API_V2_SPEC.md`, `AF1_CONTEXT_OBJECT_CATALOG.md`,
`AF1_PROMPT_CONTEXT_MAPPING.md`) — plus a fresh code-verification pass specifically for this
certification, described inline where it changes a prior document's conclusion.
**Method:** this is not a re-summary of prior documents. Every claim below was checked against running
code as of this date. Three checks in this pass turned up material not discovered by any prior AF-1
document — these are surfaced as blockers, not silently absorbed into the existing design.

---

## Executive Verdict

**NOT YET CERTIFIED.** The core architecture — the computation-boundary principle
(`AF1_COMPUTATION_BOUNDARY_POLICY.md`) and the tiered context-object design
(`AF1_CONTEXT_API_V2_SPEC.md`) — is sound and is **not** contradicted by anything found in this pass.
No blocker below requires reworking that core design. But four concrete, bounded blockers exist, and per
this task's own instruction ("a critical contradiction" reopens the freeze), one of them (B1) is
material enough that it must be resolved, not deferred, before AF-2 begins writing code against the V2
Context API as currently specified. See **Minimum Remaining Blockers** below for the bounded fix for
each — none require a new design pass, all are resolvable as amendments to the existing V2 documents.

---

## Part 1 — Context Object Review

For every object in `AF1_CONTEXT_OBJECT_CATALOG.md`: producer, consumers, exact populating modules,
lifecycle, ownership, serialization, and whether it replaces an existing runtime object. The last column
is where this pass diverges most from the prior documents — see **Blocker B1** immediately after this
table for why.

| Object | Producer (module) | Consumers | Lifecycle | Ownership | Serialization | Replaces an existing runtime object? |
|---|---|---|---|---|---|---|
| `MarketContext` | New assembly code + `engine/regime_filter.py::detect_regime()` (existing, verified) | Regime agent, Risk agent | Per scan cycle (matches today's `_market_ctx` cache) | **Unresolved — see B3** | Ephemeral, JSON-dumped into prompts only (see G4) | `.ihsg_trend` should reuse `market_regime()`/`detect_regime()` from `engine/edge_enrich.py`/`engine/regime_filter.py` — **see B1**, not a fresh computation as originally specified |
| `OpportunityContext` (= `SignalCandidate`) | Quant scan pipeline (existing, unchanged) | All agents | Per candidate | Agent Firm (`schemas.py`, existing) | Pydantic model, already the pattern | No — genuinely unchanged from today |
| `TechnicalContext` | `engine/indicators.py`/`engine/chart_indicators.py` (as designed) **or** `engine/technicals.py::tech_direction()` (existing, discovered this pass) | Technical agent; reused for `MarketContext.ihsg_trend` | Per candidate, per evaluation | **Unresolved — see B3** | Ephemeral | **Yes — see B1**: `engine/technicals.py::tech_direction(closes, short=20, long=50)` already computes a directional read from the same `ohlcv` closes this object was designed to derive from scratch |
| `FlowContext` | `flow_filter.py` (existing, as designed) | Flow agent | Per candidate, daily | **Unresolved — see B3** | Ephemeral | Partially — `engine/edge_enrich.py::_latest_flow()` already reads the same `stockbit_flow.composite_score`/`.verdict` columns this object passthroughs; no conflict, but a second read path now exists where one would do |
| `RegimeContext` | New pure function (`regime_rules.py`, as designed) | Regime agent | Per candidate, per evaluation | **Unresolved — see B3** | Ephemeral | **Yes — see B1**: `engine/regime_filter.py::detect_regime()` is the existing, canonical, already-production regime classifier; `RegimeContext.regime_call`'s thresholds were derived from the LLM prompt's own prose (`consistency_pct >= 55%` etc.), not from this existing function — a second, independently-defined regime classifier is a direct instance of the duplication failure mode `AF1_COMPUTATION_BOUNDARY_POLICY.md`'s own Governing Test was written to prevent |
| `NewsContext` | `tools/news_lookup.py`/`tools/web_search.py` (existing, unchanged) | News agent | Per candidate, per evaluation | Agent Firm (already owns these tools) | Ephemeral, live web call | Partially — see G5: `engine/catalyst.py::has_catalyst()` is an existing deterministic catalyst-presence check with partial overlap with the News agent's own `catalyst` field |
| `PortfolioContext` | Existing `paper_trades` query, unchanged | `ConsensusContext` assembly | Per scan cycle | **Unresolved — see B3** | Ephemeral | No — genuinely new delivery of already-computed data (see the wiring-bug finding in `AF1_CONTEXT_API_V2_SPEC.md` Part 1) |
| `RiskContext` | `paper_trade.py::is_entries_blocked()` (existing) | `ConsensusContext` assembly | Per scan cycle | **Unresolved — see B3** | Ephemeral | No — closes a named, previously-unclosed gap (`AF1_FAILURE_CONTRACT.md` §6) |
| `ExecutionContext` | `paper_trade.py`'s capital/exposure bookkeeping (existing) | `resolve_size_hint()` (Tier 3) | Per scan cycle | **Unresolved — see B3** | Ephemeral | **Partially — see B2**: `engine/edge_score.py::compute_edge()` already produces a deterministic sizing multiplier (`size_mult`) from a related but distinct feature set (expectancy/consistency/flow/regime/technical votes); `ExecutionContext`+`resolve_size_hint()` was designed without awareness of this existing sizing computation |
| `SessionContext` | Derived from `scan_time`, trivial | Any agent | Per candidate | Agent Firm | Ephemeral | No |
| `ConsensusContext` | New pure function (`guardrails.py::build_consensus_summary()`, as designed) | Risk agent, `apply_guardrails` | Per candidate, post-analyst | Agent Firm (`guardrails.py`, existing pattern) | Ephemeral | No — genuinely new |

**No object in this table is unimplementable.** The "Unresolved" ownership cells and the "Yes/Partially"
duplication-risk cells are the actual content of Blockers B1 and B3 below — named here per-object so
AF-2 has a checklist, not just a narrative.

---

## Part 2 — Blocker B1: An Undiscovered Parallel Deterministic System

**This is the most significant finding of this certification pass, and was not surfaced by any prior
AF-1 or computation-boundary document.**

While tracing `scheduler/jobs.py`'s premarket job for an unrelated verification, this pass found
`scheduler/scanner.py::run_edge_veto_stage()` (lines 904-963), gated by the already-shipped,
already-governed `EDGE_SCORE_MODE` (`off`/`shadow`/`enforce` — documented in `CLAUDE.md`'s Environment
Variables table, which every AF-1 document had access to but none cross-referenced against Agent Firm's
own context design). This function runs **immediately before** `run_agent_firm_gate()` in the same scan
cycle (`scanner.py:1564,1569`) and calls a fully-formed, already-in-production deterministic pipeline:

| Existing module | Function | Computes |
|---|---|---|
| `engine/edge_enrich.py` | `market_regime(conn)` | IHSG regime (BULL/BEAR/SIDEWAYS), via `engine/regime_filter.py::detect_regime()` |
| `engine/technicals.py` | `tech_direction(closes, short=20, long=50)` | Technical direction from OHLCV closes |
| `engine/edge_enrich.py` | `_latest_flow()` / `_flow_direction()` | Flow direction from `stockbit_flow.composite_score`/`.verdict` |
| `engine/catalyst.py` | `has_catalyst(conn, ticker, date)` | Deterministic catalyst presence |
| `engine/wf_edge.py` | (via `_best_wf_edge()`) | `expectancy_pct`, `consistency_pct`, `win_rate`, `n_trades` from the `wf_edge` table |
| `engine/edge_score.py` | `compute_edge(...)` | **A deterministic position-sizing multiplier** (`edge_score` → `size_mult = round(edge, 2)`) |
| `engine/veto.py` | `apply_vetoes()` | Deterministic Tier A (directional safety) + Tier B (statistical edge floor) vetoes, open-position-count-aware capping |

**Why this matters for the V2 Context API as currently specified:**

1. `RegimeContext.regime_call` (`AF1_REQUIRED_CONTEXT_OBJECTS.md` §3, `AF1_CONTEXT_OBJECT_CATALOG.md`)
   was designed as a *new* pure function implementing thresholds copied from the LLM prompt's own prose
   (`consistency_pct >= 55%`, `vol_ratio > 3.0`, `avg_sharpe > 0.8`). These thresholds were never checked
   against `engine/regime_filter.py::detect_regime()` — the actual, canonical, already-production regime
   classifier. **If both ship as designed, Agent Firm's Regime agent and the pre-existing edge-veto gate
   can disagree about the market regime for the same ticker on the same day, with no reconciliation and
   no test catching it.** This is precisely the "two disagreeing definitions of the same fact" failure
   mode `AF1_COMPUTATION_BOUNDARY_POLICY.md`'s own Governing Test names as the reason duplication is
   never acceptable (Audit findings F1/F2 made exactly this argument about `flow_verdict` vs.
   `stockbit_flow.verdict` — the same argument applies here, just not caught in the original pass because
   this module wasn't found yet).
2. `TechnicalContext`'s design (`engine/indicators.py`/`engine/chart_indicators.py`, fresh SMA/ADX/S-R
   computation) has no relationship to `engine/technicals.py::tech_direction()`, the function the
   existing veto pipeline already uses for the same purpose on the same input (`closes`).
3. Most materially: **`ExecutionContext`/`resolve_size_hint()` (Tier 3, `AF1_REQUIRED_CONTEXT_OBJECTS.md`
   §5) was designed as an entirely new deterministic sizing computation, without any awareness that
   `engine/edge_score.py::compute_edge()` already exists and already produces a deterministic sizing
   multiplier from a related feature set.** This is not just a duplication risk — it collides with a
   confirmed, live bug. See Blocker B2.

**Required resolution (bounded, not a redesign):** `AF1_CONTEXT_OBJECT_CATALOG.md`'s `RegimeContext`,
`TechnicalContext`, and `ExecutionContext`/`resolve_size_hint()` rows must be amended to either (a)
directly wrap the existing `engine/technicals.py`/`engine/regime_filter.py`/`engine/edge_score.py`
functions as their producer, rather than inventing parallel computation, or (b) if the analyst-facing
context genuinely needs finer granularity than the coarser veto-gate feature set provides, the two
systems' potential disagreement must be an explicit, surfaced signal (e.g., "the pre-LLM edge gate read
this ticker as BULL; the Regime agent's own read is SIDEWAYS" as a flagged reconciliation input to the
Risk agent), never two silent, independent sources of truth. This is a single amendment to three rows
of one document, not a new document or a redesign — **but it must happen before AF-2 writes code**,
because it is exactly the class of finding the Computation Boundary Policy was written to prevent, found
here recurring inside that same policy's own implementation plan.

---

## Part 3 — Blocker B2: A Live, Confirmed Collision Between Two Sizing Signals

**Verified directly, not inferred:**

- `scanner.py:904-963` (`run_edge_veto_stage`, `EDGE_SCORE_MODE=enforce`): sets
  `r['agent_size_hint'] = keep[r['ticker']]['size_mult']` — the deterministic, edge-score-based
  multiplier.
- `scanner.py:1009-1013` (`run_agent_firm_gate`, `AGENT_FIRM_ENABLED=true`), which runs **immediately
  after** in the same pipeline (`scanner.py:1564` then `1569`):
  ```python
  _size_map = {d.ticker: d.size_hint or 1.0 for d in _decisions if d.decision == "approve"}
  for r in intersection_results:
      r["agent_size_hint"] = _size_map.get(r["ticker"], 1.0)
  ```
  This loop runs over **every** row in `intersection_results`, unconditionally, and **overwrites**
  whatever `run_edge_veto_stage` already wrote to the same `agent_size_hint` key — with the LLM's own
  `size_hint` if the firm approved that ticker, or a blind default of `1.0` if it didn't, regardless of
  what the deterministic edge score said moments earlier.

**This is a currently-shipped, live ordering dependency with no documented precedence rule and, as far
as this pass could verify, no test asserting which value should win when both `EDGE_SCORE_MODE=enforce`
and `AGENT_FIRM_ENABLED=true` are simultaneously active.** Nothing about this is new behavior this
certification introduces — it already exists in production. What's new is that `AF1_REMEDIATION_PLAN.md`
WP5 (`resolve_size_hint()`) would add a **third** deterministic sizing signal into this exact collision
without resolving it, compounding rather than fixing the ambiguity.

**Required resolution:** a single, explicit precedence decision — e.g., "when both modes are enforce,
the edge-veto's `size_mult` is the sizing floor/ceiling and Agent Firm's `resolve_size_hint()` output is
clamped to it" or "Agent Firm's decision, when it runs, always supersedes the edge gate's, since it runs
strictly later in the pipeline and has already reviewed the edge gate's own survivors as input" — either
is defensible, but **a decision must exist and be tested**, not remain implicit last-write-wins. This
must happen before WP5 (`AF1_REMEDIATION_PLAN.md`) is implemented, not discovered as a production
incident after.

---

## Part 4 — Blocker B3: Context-Object Ownership and Assembly Location Is Self-Contradictory Across the Document Set

`AF1_CONTEXT_API.md`'s own text: "Production Engine assembles these six objects... and passes them into
`evaluate`/`evaluate_staged`... instead of Agent Firm reaching into `data.db.connect()` itself
mid-evaluation" — this places assembly on the **Production Engine (caller) side**.

`AF1_REMEDIATION_PLAN.md` and `AF1_IMPLEMENTATION_BACKLOG.md` (written in this review's earlier phase)
list `engine/agent_firm/firm.py::_build_context()` as the affected file for WP1 (`TechnicalContext`), WP2
(`FlowContext`), WP3 (`RegimeContext`) — i.e., **assembly stays inside Agent Firm's own module.**

These are inconsistent, and the inconsistency has teeth: if assembly stays inside
`engine/agent_firm/firm.py`, then implementing WP1 requires Agent Firm to import
`engine/indicators.py`/`engine/chart_indicators.py` (or, per B1, `engine/technicals.py`) directly — new
Agent-Firm-to-Production-Engine forward dependencies that `AGENT_FIRM_DEPENDENCY_AUDIT.md` never
catalogued, and that work directly against `AGENT_FIRM_GOVERNANCE.md`'s stated eventual goal of
independent releasability (a future repository split cannot cleanly separate a module that reaches
into `engine/`'s pandas-heavy internals for its own context assembly).

**Required resolution:** one explicit sentence, added to `AF1_CONTEXT_API_V2_SPEC.md`, stating which side
assembles Tier 1 objects. The two live options, both bounded and implementable:
- **(a)** Assembly happens in Production Engine (`scheduler/scanner.py`/`jobs.py`, or a new
  Production-Engine-owned helper module those call) *before* calling `evaluate`/`evaluate_staged` —
  consistent with V1's own original text, and with `AF1_DATA_ACCESS_LAYER.md`'s existing "Production
  Engine imports this repository's read-only query functions" pattern generalized to compute functions.
  Agent Firm receives only typed, already-assembled objects — genuinely zero new forward dependencies.
- **(b)** Assembly stays in `engine/agent_firm/`, and the new forward dependencies on
  `engine/indicators.py` etc. are explicitly accepted and added to `AGENT_FIRM_DEPENDENCY_AUDIT.md`'s
  table as "Shared utility, acceptable to keep" (the same classification already given to
  `utils.telegram.send_telegram`) — a defensible choice, but only if made explicitly, not by omission.

Either is acceptable; **silence is not**, since it currently produces contradictory affected-file lists
across the document set that AF-2 cannot implement against without first picking one.

---

## Part 5 — Blocker B4: `evaluate()`'s Signature-Change Versioning Rule Contradicts Its Own Practical Necessity

`AGENT_FIRM_GOVERNANCE.md`: "**MAJOR** — any change to `evaluate`/`evaluate_staged`/`reset_market_ctx`'s
signature..." — stated as an unconditional rule, unlike the adjacent rule for `SignalCandidate`/
`AgentDecision` field changes, which explicitly carves out additive/optional changes as non-MAJOR
("removal or type change of an existing field" is MAJOR; a new optional field is MINOR).

`AF1_CONTEXT_API.md`'s own "Open Item for AF-2": "Whether these six objects are passed as one bundled
`EvaluationContext` parameter or as five separate named parameters to `evaluate`/`evaluate_staged` is an
implementation-level API-shape decision, not an architectural one — left to AF-2."

**The contradiction:** account-wide Tier 1 objects (`MarketContext`, `PortfolioContext`, `RiskContext`,
`ExecutionContext`) do not fit naturally as per-candidate `SignalCandidate` fields — they are batch-level
state, which is exactly why `_market_ctx` is cached once per scan cycle today, not attached to each
candidate. If they must reach `evaluate()` some other way, that is a signature change, and
`AGENT_FIRM_GOVERNANCE.md`'s literal text makes that MAJOR regardless of whether the new parameter is
optional — undermining AF1_CONTEXT_API.md's framing that this is a non-architectural implementation
detail AF-2 can decide freely.

**Required resolution:** one of two explicit choices, made now, not deferred to "an implementation
detail":
- **(a)** Extend `SignalCandidate` with an optional `market: MarketContext | None`,
  `portfolio: PortfolioContext | None`, etc. — batch-level objects get redundantly attached to every
  candidate in a batch (cheap, since they're constructed once and referenced, not deep-copied), keeping
  `evaluate()`'s signature literally unchanged and the whole migration MINOR per Governance's own
  existing carve-out for additive `SignalCandidate` fields.
- **(b)** Add an optional, defaulted parameter to `evaluate`/`evaluate_staged`
  (`evaluate(candidates, market_context: MarketContext | None = None)`) and explicitly amend
  `AGENT_FIRM_GOVERNANCE.md` to carve out additive-optional-parameter signature changes as MINOR, the
  same way it already does for the data classes — closing the inconsistency identified above rather than
  leaving it standing.

Recommend **(a)** — it requires no amendment to `AGENT_FIRM_GOVERNANCE.md` at all and reuses the pattern
already proven safe for `indicators`. Either is implementable without ambiguity once chosen.

---

## Part 6 — Deterministic Computation: Owner Confirmation

Every finding from `AF1_DETERMINISTIC_COMPUTATION_AUDIT.md`, cross-checked against Part 1's object table
above:

| Finding | Owner confirmed? |
|---|---|
| T1, T2 (Technical) | **Confirmed, pending B1 resolution** — owner is `engine/indicators.py`/`chart_indicators.py` *or* `engine/technicals.py`, whichever B1 resolves to; not ownerless, just not yet singular |
| F1, F2, F3 (Flow) | Confirmed — `flow_filter.py` (existing), one new `SUM()`, one new rolling-sign function |
| R1, R2, R3 (Regime) | **Confirmed, pending B1 resolution** — owner is the new `regime_rules.py` *or* `engine/regime_filter.py::detect_regime()`, whichever B1 resolves to |
| K1, K2 (Consensus/dedup) | Confirmed — `guardrails.py::build_consensus_summary()` |
| K3 (Sizing) | **Confirmed, pending B2 resolution** — owner is `resolve_size_hint()` *and* possibly `engine/edge_score.py::compute_edge()`, precedence undecided |
| K4 (Confidence banding) | Confirmed — `ConsensusContext.aligned_bullish` |
| S1, S2 (Schema gaps) | Confirmed — `schemas.py` amendments, WP6 |

**Five of seven finding groups have an unambiguous single owner today. Two (Technical/Regime) and one
partially (Sizing) are pending the B1/B2 resolutions above** — this is the precise, bounded scope of
"not yet certified," not a wholesale reopening of the computation-boundary design.

## Part 7 — LLM Computation: Reasoning-Only Purpose Confirmation

| Agent output | Reasoning-only? | Confirmation |
|---|---|---|
| Technical `verdict`/`conviction` | Yes | Synthesis over `TechnicalContext` facts — no arithmetic once B1 is resolved |
| Flow `reasoning` | Yes | Narration/cross-referencing daily vs. intraday signal, per `AF1_PROMPT_CONTEXT_MAPPING.md`'s open question |
| Regime narrative | Yes | Macro/sector color beyond the three deterministic factors |
| News `sentiment`/`catalyst`/`key_headline` | Yes | Genuine NLU over unstructured text — confirmed clean in the original audit; **G5 below narrows this slightly, not reverses it** |
| Bull/Bear `*_case`/`key_strength`/`key_risk` | Yes | Argumentation over already-produced analyst outputs |
| Risk `decision` (residual, post-guardrail) | Yes | Only genuinely close calls survive to the LLM once K1/K2 become hard guardrails |
| Risk `confidence` | Yes | Calibration, not gated by a restated threshold, per the Computation Boundary Policy's explicit exception |
| Risk `size_tier` | Yes | Qualitative signal only, resolved to a number by `resolve_size_hint()`, never the number itself |

**Every LLM output has a stated, reasoning-only purpose.** No LLM output in the current design computes
a number, sum, threshold comparison, or lookup table result directly — this holds regardless of how B1/B2
resolve, since those blockers are about *which deterministic function* owns a fact, not about whether the
LLM is asked to compute it.

---

## Part 8 — Non-Blocking Gaps (close during AF-2, do not block the freeze)

| # | Gap | Detail |
|---|---|---|
| G1 | `AF1_IMPLEMENTATION_SPEC.md` Part 3 step 6 still references V1's six-object design | Needs a dated amendment once V2 is adopted — documentation staleness, not a design flaw |
| G2 | `AF1_IMPLEMENTATION_BACKLOG.md` has no work package for `MarketContext.ihsg_trend`, `market_risk_score`, or `ExecutionContext` | These were introduced in the later V2 redesign, after the backlog was written — see `AF2_WORK_PACKAGE_SEQUENCE.md`'s WP8/WP9 |
| G3 | Context-object *type definition* ownership (which side's `schemas.py`) was never pinned down the way `AF1_SCHEMA_OWNERSHIP_DECISION.md` pinned down `agent_decisions` ownership | Resolved in practice by B3's answer — if (a), types can live either side; if (b), types live in `engine/agent_firm/schemas.py` alongside `SignalCandidate` |
| G4 | Serialization requirements were never addressed for any Tier 1/2/3 object | Recommend: ephemeral by default (Pydantic models, JSON-dumped into prompts, never persisted); whether audit-reproducibility later requires snapshotting them into `agent_traces` is an explicitly deferred AF-3+ question, not a silent default either way |
| G5 | News agent's "fully clean" classification narrows slightly | `engine/catalyst.py::has_catalyst()` is an existing deterministic boolean catalyst check with partial overlap with the News agent's own 3-way `catalyst` field — not a duplication (different granularity), but AF-2 should verify they don't silently disagree before assuming independence |
| G6 | Test-file breakage from WP4's signature change is real and quantified | `tests/agent_firm/test_firm.py`, `test_firm_v2.py`, `test_risk.py`, `test_risk_v2.py` all construct calls to `risk.run()` or its fixtures directly — see `AF2_TEST_STRATEGY.md` |
| G7 | No concrete shadow-mode flag mechanism was named for WP4/WP5 | `engine/agent_firm/config.py::FIRM_ENABLED`/`get_enforce()`/`set_mode()` is the existing pattern to extend — see `AF2_TEST_STRATEGY.md` and `AF2_RISK_REGISTER.md` |
| G8 | `hypothesis` (property-based testing) is not a current dependency (verified: absent from `requirements.txt`) | WP5's "property-style test" acceptance criterion should be restated as exhaustive boundary-case testing unless adding the dependency is separately approved |
| G9 | `scripts/replay_firm_offline_run.py` already exists and is the right tool for shadow-mode validation | Already runs the real production path against the real DB with a distinct, cleanable `scan_time` marker — reuse, don't reinvent; see `AF2_TEST_STRATEGY.md` |

---

## Certification Statement

The computation-boundary architecture (`AF1_COMPUTATION_BOUNDARY_POLICY.md`) is **certified sound in
principle** — every deterministic-computation category has a Production Engine owner in principle, every
LLM output has a reasoning-only purpose, and no finding in this pass contradicts that core design.

**Implementation readiness is NOT certified** until Blockers B1-B4 are each resolved by a short, explicit
amendment (none require a redesign):
1. B1 — reconcile `RegimeContext`/`TechnicalContext`/`ExecutionContext` with `engine/edge_enrich.py`'s
   existing pipeline (amend 3 rows in `AF1_CONTEXT_OBJECT_CATALOG.md`).
2. B2 — decide and document the precedence between `EDGE_SCORE_MODE`'s `size_mult` and Agent Firm's
   `resolve_size_hint()` output (one paragraph, one test).
3. B3 — decide and document which side assembles Tier 1 context objects (one sentence in
   `AF1_CONTEXT_API_V2_SPEC.md`).
4. B4 — decide and document how batch-level objects reach `evaluate()` without an unresolved MAJOR-version
   question (one sentence, recommend option (a) in Part 5 above).

Once B1-B4 are resolved, this document's Part 6/Part 7 tables go from "5 of 7 confirmed, 2 pending" to
fully confirmed, and AF-2 may proceed against `AF1_CONTEXT_API_V2_SPEC.md` without ambiguity. The nine
G-items in Part 8 should be tracked but do not block that certification.
