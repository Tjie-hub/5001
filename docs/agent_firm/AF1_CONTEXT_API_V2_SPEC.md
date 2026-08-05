# AF-1 — Context API V2 Specification

**Date:** 2026-07-29
**Status:** PROPOSED. Does not supersede `AF1_CONTEXT_API.md` yet — that happens once V2 is implemented,
per this document's own Definition of Done. Treat this as the design AF-2 should implement against
*instead of* V1, not an amendment layered on top of it.
**Basis:** `AF1_DETERMINISTIC_COMPUTATION_AUDIT.md`, `AF1_COMPUTATION_BOUNDARY_POLICY.md`,
`AF1_REQUIRED_CONTEXT_OBJECTS.md`, `AF1_REMEDIATION_PLAN.md` (WP1-WP5), and a fresh verification pass
against the current `engine/agent_firm/` code described in Part 1.
**What changed since V1:** `AF1_CONTEXT_API.md` (2026-07-28) was written to solve the *access* boundary
— "Agent Firm must never open a production database connection to gather its own evaluation context."
It explicitly stated its own scope limit: "this design does not invent new data sources, it types and
relocates existing ones." That was the correct scope for the problem it was solving. The
Deterministic Computation Audit found a second, different problem sitting underneath it: several of the
"existing ones" it relocates are raw rows a prompt then asks an LLM to compute over. V2 keeps V1's
access-boundary principle (Agent Firm never opens a DB connection mid-evaluation) and adds a second,
equally binding principle: **every value handed to a prompt must already be a deterministic fact, never
raw material for the LLM to derive one.**

---

## Part 1 — Disposition of Every V1 Context Object

**Verification note before the table:** V1 was never implemented. `engine/agent_firm/schemas.py` today
defines only `SignalCandidate`, `AgentResult`, `AgentDecision`, `AgentState` — no `MarketContext`,
`RecentHistory`, `PortfolioState`, `RiskLimits`, or `SessionState` class exists in code.
`firm.py::_build_context()` still returns a raw dict from 7 hand-written SQL queries, exactly as it did
when V1 was written. This matters for Part 5 (Migration Mapping): there is no running code to migrate,
only a document to supersede.

| V1 Object | Disposition | Why |
|---|---|---|
| `MarketContext` | **EXTEND** | Kept as the market-wide (not ticker-specific) container, but two problems found on re-verification: (1) `ihsg_recent: list[OhlcvBar]` is raw bars with the same T1/T2 problem `RecentHistory.ohlcv` had — no agent should have to infer IHSG's trend from raw bars any more than a ticker's own trend; (2) **`market_risk_score`, and the `ihsg` data underlying it, are computed every scan cycle by `firm.py`'s `_market_ctx` cache but never delivered to a single agent today** — confirmed by grep: no agent module reads `context["ihsg"]`. V1 named `market_risk_score` as a gap to close; this document additionally confirms `ihsg` itself never reaches anyone either. See `MarketContext.ihsg_trend` in Part 2/3. |
| `Opportunity` (= `SignalCandidate`) | **KEEP, renamed `OpportunityContext`** | V1 already stated this is "not a new type, a naming clarification." No field-level change needed beyond what `AF1_REQUIRED_CONTEXT_OBJECTS.md` already specified for `indicators` (now typed, via `TechnicalContext`, instead of the opaque, currently-always-empty dict at `scanner.py:1000,1092`). Renamed only for naming consistency across the V2 catalog (`*Context` suffix throughout) — not a structural change. |
| `RecentHistory` | **SPLIT** | This was the object carrying every raw-row field the Audit flagged (`ohlcv`, `stockbit_flow`, `broker_flow`, `stockbit_flow_bars`, `wf_scores`, `sector_data`, `news_mentions`). A single bundle mixing "needs heavy derivation" (OHLCV, flow, regime) with "genuinely fine as structured-raw" (news headlines) obscured the boundary this whole review exists to draw. Split into four independently-composable, independently-versionable objects: `TechnicalContext`, `FlowContext`, `RegimeContext`, `NewsContext` — each owned by exactly one analyst, each stating its own deterministic-source contract. |
| `PortfolioState` | **REPLACE → `PortfolioContext`, plus a code-wiring fix, not just a rename** | V1 specified `open_trades: list[OpenTrade]` as "same fields already queried today, just typed." Re-verification found this was never actually true in the sense that matters: `firm.py:141` computes `open_trades` into the `context` dict every scan cycle, but `agents/risk.py::run()`'s function signature (`candidate`, `analyst_results`, `client`) never accepts a `context` parameter, and `firm.py::_run_risk` never passes one. **The Risk Manager has zero visibility into open positions today, despite `risk_v2.md:7` telling the model it will receive "Current open paper trades."** This is not a V1 design flaw — V1's typed object would have had the same silent gap unless the wiring is fixed as part of building it, which is why this is called out explicitly here rather than assumed fixed by typing alone. |
| `RiskLimits` | **KEEP, renamed `RiskContext`** | V1 already correctly identified this as "genuinely new, closes a real gap" — `entries_blocked` is real, verified, and currently invisible to Agent Firm. No field change. Renamed only for `*Context` naming consistency. |
| `SessionState` | **KEEP, renamed `SessionContext`** | No computation-boundary issue exists here — `scan_time`/`wib_session` are metadata, not values requiring derivation. Renamed only for consistency. |

**Two new objects, no V1 counterpart:**

- **`ConsensusContext`** — assembled *after* the four analyst agents run, not before. V1's six objects
  were all pre-evaluation inputs; this is the first context object in the design that depends on LLM
  output from an earlier phase. Named explicitly as its own tier in Part 2, not force-fit into the
  pre-evaluation bundle.
- **`ExecutionContext`** — account-level capital/exposure state (`aggregate_open_exposure_pct`,
  `capital`, `risk_pct_config`). A second, previously-undiscovered gap closed here: today, when the Risk
  agent picks a `size_hint`, it has zero visibility into current portfolio heat — sizing "reasoning" is
  blind to aggregate exposure, relying entirely on `paper_trade.py`'s downstream cap as a blunt backstop
  rather than an informed input. `ExecutionContext` is what `AF1_REQUIRED_CONTEXT_OBJECTS.md`'s
  `resolve_size_hint()` was missing an input for.

---

## Part 2 — The Complete V2 Object Set

Three tiers, by *when* each object is assembled relative to the LLM calls in the evaluation graph.
Full field-level detail for every object is in `AF1_CONTEXT_OBJECT_CATALOG.md`; this section gives each
object's purpose and tier.

### Tier 1 — Pre-Evaluation Context (assembled once, before any agent runs)

| Object | Scope | Purpose |
|---|---|---|
| `MarketContext` | Market-wide, cached per scan cycle | IHSG-level trend + market risk score — macro grounding available to any agent that needs it |
| `OpportunityContext` | Per candidate | The signal being evaluated (renamed `SignalCandidate`) |
| `TechnicalContext` | Per candidate | Precomputed indicator facts — replaces raw OHLCV for the Technical Analyst, and doubles as the producer for `MarketContext.ihsg_trend` |
| `FlowContext` | Per candidate | Precomputed flow verdict/smart-money/aggregate facts — replaces raw 14d flow rows for the Flow Specialist |
| `RegimeContext` | Per candidate | Precomputed regime classification — replaces raw `wf_scores`/`daily_screen` rows for the Regime Analyst |
| `NewsContext` | Per candidate | Structured news rows + web search results — largely unchanged from V1, since the News agent's job is genuine NLU over text, not arithmetic (Audit N1: no violation found here) |
| `PortfolioContext` | Account-wide, cached per scan cycle, ticker-scoped lookup | Open positions — now actually wired to every agent that needs it, closing the gap found in Part 1 |
| `RiskContext` | Account-wide, cached per scan cycle | The drawdown circuit breaker's live state (renamed `RiskLimits`) |
| `ExecutionContext` | Account-wide, cached per scan cycle | Capital/exposure state for sizing decisions — new, closes the second gap found in Part 1 |
| `SessionContext` | Per candidate | Timing metadata (renamed `SessionState`) |

### Tier 2 — Inter-Agent Context (assembled by the orchestrator, between phases)

| Object | Scope | Purpose |
|---|---|---|
| `ConsensusContext` | Per candidate, per evaluation | Deterministic counts/gates computed from the four analysts' *already-produced* verdicts plus `PortfolioContext`/`RiskContext` — feeds the Risk agent and `apply_guardrails` |

### Tier 3 — Post-Decision Resolution (not context handed to an LLM; the deterministic mirror-image)

Not part of the Context API's input surface, but documented here for completeness since it consumes
Tier 1/2 objects and closes the loop the Computation Boundary Policy opened:

| Function | Inputs | Purpose |
|---|---|---|
| `resolve_size_hint()` | LLM's `size_tier` + `ConsensusContext` + `ExecutionContext` + `quant_score` | Turns a qualitative LLM signal into the bounded, capital-affecting `size_hint` number — see `AF1_REQUIRED_CONTEXT_OBJECTS.md` §5, refined here to also take `ExecutionContext` so sizing is exposure-aware, not blind to portfolio heat |

---

## Part 5 — Migration Mapping

```
V1 (AF1_CONTEXT_API.md)              V2 (this document)
─────────────────────────            ──────────────────────────────────────────
MarketContext                   →    MarketContext (extended: +ihsg_trend, market_risk_score actually wired)
Opportunity                     →    OpportunityContext (renamed; .indicators now typed as TechnicalContext)
RecentHistory                   →    SPLIT into:
  .ohlcv                        →      TechnicalContext
  .stockbit_flow, .broker_flow  →      FlowContext
  .stockbit_flow_bars           →      FlowContext.flow_bars_recent
  .strategy_edge                →      RegimeContext
  .recent_screen_signals        →      RegimeContext
  .news_mentions                →      NewsContext
PortfolioState                  →    PortfolioContext (extended + actually wired into risk.run()'s signature)
RiskLimits                      →    RiskContext (renamed only)
SessionState                    →    SessionContext (renamed only)
(none)                          →    ConsensusContext (new — Tier 2)
(none)                          →    ExecutionContext (new — Tier 1)
```

### Compatibility Strategy

**There is no code to migrate.** V1 was a design document only — verified in Part 1, no
`MarketContext`/`RecentHistory`/`PortfolioState`/`RiskLimits`/`SessionState` class exists anywhere in
`engine/agent_firm/` today, and `_build_context()` still runs its original 7 raw queries unchanged.
This means the usual compatibility concerns (dual-write periods, deprecation cycles, versioned field
migration) do not apply between V1 and V2 — there is no live caller depending on V1's shape to break.

**What this means for `AGENT_FIRM_GOVERNANCE.md`'s versioning policy:** the V1→V2 change is invisible to
that policy entirely. Governance versions `evaluate`/`evaluate_staged`/`SignalCandidate`/`AgentDecision`
— the *external* interface. Every V1/V2 Context API object is *internal* to Agent Firm's own evaluation
pipeline (assembled by `_build_context()` or its replacement, consumed only by agents inside
`engine/agent_firm/`), explicitly out of the versioned contract per `AGENT_FIRM_INTERFACE_SPEC.md` §7
("Prompt orchestration... entirely internal implementation"). Superseding V1 with V2 requires no MAJOR,
MINOR, or PATCH designation and no owner sign-off beyond this document's own review — the one exception
being `SignalCandidate.indicators` gaining defined content, which is a MINOR-at-most change per
`AF1_COMPUTATION_BOUNDARY_POLICY.md`'s existing Compatibility Note, unchanged by this document.

**When V1 is formally superseded:** per this document's Definition of Done, `AF1_CONTEXT_API.md` should
be marked superseded (not deleted — this repository's own convention per `CLAUDE.md`'s "nothing is
deleted on supersession") once AF-2 actually implements the Context API against V2 instead of V1. Until
that implementation lands, both documents coexist: V1 remains the historical record of the
access-boundary design; V2 is what AF-2 builds.

---

## Definition of Done — Verification

- **Agent Firm receives structured facts:** every Tier 1/Tier 2 object in Part 2 carries pre-derived
  values; the only remaining raw-shaped data (`NewsContext`'s headlines, `TechnicalContext`/`FlowContext`'s
  small recent-window fields) is raw *text* or a small window kept deliberately for qualitative color,
  never raw material a prompt is asked to compute an indicator, sum, or threshold from.
- **Production Engine remains the sole producer of deterministic calculations:** every object's producer
  in `AF1_CONTEXT_OBJECT_CATALOG.md` is a Production Engine module or an existing, already-tested
  function (`engine/indicators.py`, `engine/chart_indicators.py`, `flow_filter.py`, `paper_trade.py`) or
  a new pure function living beside `guardrails.py`'s existing deterministic-post-LLM pattern — never an
  LLM call.
- **No prompt requires arithmetic, indicator calculation, statistical computation, or threshold
  evaluation:** verified per-prompt in `AF1_PROMPT_CONTEXT_MAPPING.md`.
- **V1 can be superseded cleanly:** verified above — zero implemented code depends on V1's shape.
