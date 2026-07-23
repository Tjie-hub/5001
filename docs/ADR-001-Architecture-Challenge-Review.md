# ADR-001 Architecture Challenge & Optimization Review

**Date:** 2026-07-22
**Reviewed artifact:** `docs/ADR-001-Production-Engine-v2.md` (PROPOSED)
**Review stance:** Adversarial. The reviewer is not the author. Every decision in ADR-001 was treated as potentially wrong. Findings below that *survive* attack are endorsed explicitly; everything else is challenged with a concrete alternative.
**Context weighted throughout:** single operator, one machine, SQLite, ~900-ticker IDX universe, paper-trade execution today, Telegram as the delivery surface, a demonstrated failure history of *unwired machinery* (audit H-1/H-2) and *ad-hoc state surgery*.

---

## 1. Executive Review

ADR-001's diagnosis is correct and its skeleton survives adversarial review: two-plane canonical objects, one entry authority, integrity-as-gate, scouts-that-only-nominate, and DAG-of-stages scheduling are the right answers to the audit's structural findings, and no alternative examined here beats them *as a shape*.

However, the ADR has a consistent failure mode of its own: **it is most confident exactly where it is least specified.** The four load-bearing mechanisms — the snapshot hash, the declarative trigger/invalidation DSL, the TRIGGERED state, and the "one Decision Engine" — are each either under-specified (hash), over-engineered (DSL), redundant (TRIGGERED as a persisted state), or conflating two concepts that will be forced apart within a year of research evolution (engine = authority vs engine = policy). The ADR also misses three domain realities that the *audit itself* surfaced: ticker-level suspension as a temporary condition, ticker-level position/cooldown invariants that cut across a thesis-keyed registry, and the corpus-correction problem (what happens to "immutable" snapshots when history is repaired — which Phase 1's own C-1 reconciliation will do on day one).

None of this requires redesign. It requires **eight binding amendments** before schemas are written. With them, the architecture is production-credible and research-credible for a five-year horizon.

**Verdict: GO WITH CONDITIONS (§15). Architecture score: 7.0/10 as written; estimated 8.5/10 with amendments.**

---

## 2. Architecture Score

| Dimension | Score | Note |
|---|---|---|
| Problem diagnosis fidelity (audit → structure) | 9 | Traceability table is genuinely complete |
| Canonical object choice | 7 | Two planes right; third object (Decision Log) wrongly demoted; snapshot mechanics vague |
| Domain model correctness | 6 | Thesis-keyed identity right, but ticker-level invariants missing; suspension missing |
| Lifecycle / state machine | 7 | Sound; TRIGGERED and COOLDOWN both challengeable |
| Data integrity design | 7 | Certification model strong; publication/correction story absent |
| Scheduler | 8 | Right model at right thinness; resume semantics need one rule tightened |
| Simplicity discipline | 5 | DSL, snapshot hash, premarket duplication all violate the ADR's own R4 |
| Research readiness | 7 | Event log is the right asset; decision-policy seam missing |
| Migration plan | 8 | Strangler with success criteria and deletion as deliverable — rare and correct |
| Testability | 7 | Stages-as-functions good; DSL would have been a testing tarpit |
| **Overall** | **7.0** | Right skeleton, four soft joints |

---

## 3. Strengths (attacked and survived)

- **S1 — Two-plane canonical model.** Attacked via "why not one object?" and "why not signal-centric with better hygiene?" Survives: data trust and decision state have different lifecycles, different writers, and different consumers; merging them re-creates the audit's W4. Signal-centric-with-hygiene fails because ephemeral objects cannot carry the age/provenance/accountability the audit demanded.
- **S2 — One entry authority (P5).** Attacked in §6 below (the "one engine" claim partially falls) — but the *chokepoint* itself survives every alternative: multiple entry paths are precisely what produced audit W3/M-10.
- **S3 — Integrity as a gate, not an alert.** Attacked via "isn't this just monitoring with extra steps?" Survives: the audit proved alert-based integrity races its consumers (17:00 coverage alert after 16:30/16:40 jobs consumed the bad data). The verdict table (CERTIFIED/DEGRADED/FAILED × entries/exits/reports) with fail-closed entries and fail-open exits is the single best design element in the ADR.
- **S4 — Scouts demoted to nominators.** Survives cleanly. The strongest simplicity move in the document: it converts N pipelines × M gates into N nominators + 1 gate set.
- **S5 — Runs-as-DAGs with manifests, sentinel-on-success, stages-only-in-DAGs.** Survives. "Unregistered work is unrepresentable" is the correct structural kill for H-1/H-2.
- **S6 — Migration with deletion as a tracked deliverable and phase gates.** Survives. Phase 3's shadow-decision comparison harness is the right way to make fail-closed politically survivable (R2).
- **S7 — Preserving the exit kernel and validated logic as libraries.** Survives; re-validation budget is spent only where the audit demands.

---

## 4. Weaknesses

### W1 — The declarative `trigger_spec` / `invalidation_spec` DSL is an unbuilt language (over-engineering, severe)
ADR-001 stores promotion/invalidation conditions "as data (e.g., `close > level L on VR > x`), evaluated by the one evaluator." That is a rules language: it needs a grammar, an evaluator, versioning, migration of stored specs when semantics change, and a test surface for *every expressible rule* — for a system with roughly six thesis types, all of which already have validated, tested checker functions. A DSL is also *worse* for auditability than code: code is reviewed, diffed, and covered by the existing 1,193-test suite; stored expressions are data that silently drifts from the evaluator that interprets them.
**Alternative (recommended):** `trigger_spec = {evaluator_id, params, evaluator_version}` where `evaluator_id` names a registered, versioned *function* (the existing checkers, wrapped). Declarative *parameters*, code *logic*. All of the ADR's auditability claims are preserved (the target records which evaluator+version+params judged it); none of the language cost is paid.

### W2 — The snapshot hash is under-specified and, as literally described, impractical (severe)
"Hash over the corpus slice consumed" — which slice? Feature computation needs up to 2 years of history per ticker (MA200, 52-week highs). If the hash covers consumed history, then *any* historical repair — including Phase 1's own C-1 volume reconciliation, late yfinance corrections, or the corporate-action back-adjustment — changes the effective content of every subsequent snapshot, and the ADR gives no rule for what that means. If the hash covers only the day's rows, it doesn't certify what features actually depended on. The ADR needs snapshots to be immutable *and* needs the corpus to be repairable, and never reconciles the two.
**Alternative (recommended, replaces the hash):** see §8/A1 — a **published snapshot artifact** plus a monotonic **`corpus_version`**. Certification *publishes* a compact per-date artifact (active universe × {final bar, computed features, integrity flags} — a few MB) and stamps it with `(trade_date, corpus_version, feature_version, calendar_version, ca_version, universe_version)`. The artifact file is what gets hashed — trivially. Historical repairs bump `corpus_version` and may trigger explicit, *recorded* re-publication of affected dates. Immutability becomes true by construction (artifacts are files/rows never updated, only superseded with lineage), replay becomes cheap, and research reads artifacts instead of contending for the hot DB's WAL (a real, audited pain point).

### W3 — Ticker-level invariants are missing from a thesis-keyed registry (severe)
ADR-001 keys targets by (ticker, thesis_type, direction) and defers confluence to OQ-1 — but never addresses the **ticker-level facts that no thesis owns**: at most one open position per ticker (cash equity book); opposing-direction theses cannot both act; the post-stop-loss cooldown is empirically a *ticker* property today (a momentum SL loss should chill a reversal entry on the same name); suspension freezes every thesis on the ticker at once. Without a ticker-level constraint surface, these invariants get re-implemented ad hoc inside the Decision Engine — the exact "four copies of the gates" failure mode v2 exists to kill, one level up.
**Fix:** introduce a thin **Ticker Book View** (a queryable projection, not a new stateful object): open position?, cooldown_until (ticker-level ledger), suspension/halt flag, live targets by direction. Admission consults it (conflict policy), the Decision Engine enforces it (one position per ticker; direction conflict resolution — the validated directional source wins, mirroring today's proven rule), and COOLDOWN moves out of the target lifecycle (see §4/W5).

### W4 — "One Decision Engine" conflates authority with policy (will not survive five years)
The chokepoint (one component may open positions, one record type, one risk veto) is correct forever. But the ADR implies one decision *logic*. Within the stated research roadmap (edge discovery, experiment framework, RL, adaptive allocation), different strategy families will demand different decision policies — the counter-trend book already has different sizing/level rules *today*. If policy is monolithic, every research advance becomes a surgery on the single most safety-critical component.
**Fix:** split explicitly: **Decision Authority** (frame: invariant enforcement, ticker book checks, risk veto invocation, decision recording — changes rarely, tested exhaustively) hosting **Decision Policies** (per strategy family, versioned, pluggable — change often, sandboxed by the frame). A policy proposes {enter/pass, size intent}; the authority disposes. Five-year research evolution then touches policies, never the frame.

### W5 — Lifecycle: two states don't pay for themselves
- **TRIGGERED as a persisted state:** in the v2 default (entries decided EOD/premarket only), trigger detection and decision happen *inside the same run, minutes apart*. A persisted state whose healthy lifetime is one transaction, plus the stuck-state detector built to babysit it, is machinery serving its own failure mode. **Alternative:** record `TriggerEvent` on the target (append-only, fully auditable), let the Decision Engine consume trigger events within the run; a trigger event with no corresponding decision record in the same run *is* the stuck-state alarm — no state needed. Re-introduce the persisted state only if intraday-triggered/EOD-decided flows (OQ-2 reversal) ever materialize.
- **COOLDOWN as a target state:** cooldown is a ticker property (W3). As a target state it both under-covers (doesn't chill sibling theses) and over-covers (archiving the target would erase the cooldown). **Alternative:** ticker-level cooldown ledger in the Book View; after position close the target goes directly to `WATCHING` (thesis intact) or `ARCHIVED(completed)` (thesis consumed), and the *ledger* blocks re-entry.
- **Missing: suspension.** IDX suspensions are common, temporary, and audit-relevant (M-12 explicitly distinguishes suspended from delisted). A `WATCHING` target on a suspended ticker must neither expire by TTL nor be evaluated; a `POSITIONED` target on a suspended ticker is a first-class risk condition that deserves visibility. **Alternative to a new state:** an orthogonal `frozen` flag (set by the universe-sync stage from suspension events) that pauses TTL clocks and evaluation for any state — avoids state-machine combinatorics (SUSPENDED×WATCHING, SUSPENDED×POSITIONED…) while making the condition queryable and reported.

Resulting simplified machine: `CANDIDATE → WATCHING ⇄ READY → POSITIONED → (WATCHING | ARCHIVED)`, + `ARCHIVED(reason)` from any live state, + orthogonal `frozen`, + ticker cooldown ledger, + TriggerEvent/DecisionRecord pairing. **Six states → four**, with strictly more domain coverage.

### W6 — The premarket run duplicates the EOD decision on the same data
The premarket run "re-evaluates the registry against the last certified EOD snapshot." Same snapshot, same registry ⇒ by the ADR's own determinism principle (P6), it must produce the *same* ranking the 16:40 EOD run already produced — so the 08:35 firm re-evaluation is either a no-op or a violation of P6. This reproduces an audit theme (duplicated outputs from duplicated pipelines) inside v2 itself.
**Fix:** premarket becomes a **delta digest**: overnight news/macro/global inputs, universe changes, and any *changed* target states — plus a re-run of the Risk Layer only (market state may have changed via overnight futures/macro). No second full decision pass, no second LLM spend.

### W7 — No corpus-correction / backfill protocol (the immutability story has a hole)
Phase 1 begins with the largest historical mutation in the system's life (C-1 volume reconciliation, corporate-action adjustment). The ADR treats snapshots as immutable but never defines what a *repair* does to already-issued certificates, already-computed features, already-made decisions, or research exports. Without a protocol, the first backfill silently breaks replay — the exact property the machinery was bought for.
**Fix:** the versioned-publication model of W2/A1, plus a rule: *decisions are never retro-invalidated* (they record the artifact version they saw — that is the point of provenance); repairs create superseding artifact versions with lineage; a nightly stage reports "dates whose artifacts were superseded" so research knows what shifted.

### W8 — Missing operator-override surface
Single-operator platforms die by ad-hoc SQL surgery the event log never sees. The ADR gives the operator no first-class verbs: force-archive a target, freeze a ticker, pause entries globally, override a veto with a reason. Every one of those *will* happen; if they aren't commands emitting events, the event log's claim to be the truth is fiction within a month.
**Fix:** a small set of operator commands (CLI/Telegram) that go through the same APIs and emit `OperatorEvent`s — the manual path *is* the audited path.

---

## 5. Hidden Risks

| # | Risk | Why it's hidden |
|---|---|---|
| HR1 | **Feature/evaluator version churn invalidates comparability** — bumping `feature_version` makes yesterday's priority scores incommensurable with today's; nothing in the ADR notices | Versions appear only in manifests, which nothing analyzes; add a "version-change changelog" line to the registry digest |
| HR2 | **The Certifier becomes a de-facto trading gate tuned by trading outcomes** — pressure to loosen DEGRADED thresholds when they block wanted trades | The R8 contract test guards imports, not incentives; require certifier threshold changes to be config-versioned and to appear in the run report |
| HR3 | **SQLite single-writer contention** between the event-emitting registry, position monitor, and research reads during the EOD run window | Audit already saw lock bugs; the published-artifact model (A1) removes research reads from the hot path; keep decision-plane writes in one process |
| HR4 | **Shadow-phase anchoring** — Phase 2's success criterion ("registry explains 100% of legacy watchlist contents") risks enshrining legacy *bugs* as v2 requirements | Restate criterion: explain 100% of differences, not reproduce 100% of contents |
| HR5 | **The comparison harness is itself a build** with no owner or scope in the plan; if it slips, Phase 3's gate quietly becomes vibes | Scope it in Phase 1 (it needs snapshots anyway) |
| HR6 | **Telegram as a single delivery point** — every output funnels through one bot token; the run report about Telegram being down goes over Telegram | Cheap mitigation: run reports also land as files; heartbeat watchdog alarms via a second channel |
| HR7 | **Clock authority is unowned** — `date.today()`/WIB conversions scattered today; replay and holiday logic silently depend on host clock/timezone | One Clock module, injected; manifests record the clock decision inputs |
| HR8 | **Event-log growth** — decades-scale append-only tables in one SQLite file | Trivial now; name a compaction/archival policy so it's a decision, not an accident |

---

## 6. Missing Concepts

1. **Decision Log as the third canonical object** (promoting ADR-001's `Decision` entity). The review question is right and the ADR under-called it: the complete record of *everything considered* — enters, passes, and vetoes, each with `{artifact_version, target_id + event_seq, evaluator versions, policy version, risk verdict, portfolio state, firm artifact}` — is the platform's most valuable research asset, because it is the only selection-bias-free dataset the system produces. Positions record what happened; the Decision Log records what was *choosable*. Fields per the review prompt: all endorsed; add `policy_id/version` (W4) and `book_state_snapshot`.
2. **Ticker Book View** (W3) — ticker-level invariants, cooldown ledger, frozen flag.
3. **Decision Policy seam** (W4).
4. **Corpus versioning & publication protocol** (W2/W7).
5. **Operator command surface** (W8).
6. **Clock authority** (HR7).
7. **Parameter/config store as a versioned object** — the ADR stamps `config_version` into manifests but never says where config lives or how it changes; today it is scattered across `paper_config`, `.env`, and constants. One versioned parameter set, changed only by recorded operations, referenced by version everywhere.
8. **Conflict policy at admission** — scouts *will* conflict (reversal-long and distribution-short on the same ticker, same day; it happens in today's data). Policy: both admissible as targets; the Book View forbids simultaneous action; directional precedence follows the validated-source rule the current system already proved (REVERSAL wins as the broker-confirmed directional source).

Explicitly evaluated and **rejected** as canonical objects: `Portfolio` and `Position` (real entities, but owned by the existing, audited-strong position/exit machinery — elevating them buys nothing now; revisit with live execution); `Thesis` and `Evidence` (attributes of Target — promoting them is normalization theater at this scale); `Signal` (correctly demoted to event; re-elevating it would resurrect the audited failure mode); `Market State` (a *feature block* with a version, not an object — making it canonical invites a parallel data plane).

---

## 7. Components to Remove

| Component (as designed) | Disposition |
|---|---|
| Trigger/invalidation **DSL** | Remove. Replace with registered versioned evaluator functions + declarative params (W1) |
| **Snapshot hash** over "corpus slice consumed" | Remove. Replace with published artifact + corpus_version lineage (W2) |
| **TRIGGERED** persisted state + stuck-state detector | Remove. Replace with TriggerEvent/DecisionRecord pairing check (W5) |
| **COOLDOWN** target state | Remove. Replace with ticker-level cooldown ledger in Book View (W5) |
| **Premarket full re-evaluation** (second decision pass + LLM spend) | Remove. Replace with delta digest + risk-only refresh (W6) |
| `CANDIDATE` as a *persisted* state (challenge considered) | **Keep** — admission rejections must be recorded events with reasons (audit demands visible filtering); but allow same-transaction CANDIDATE→WATCHING so it never lingers |

## 8. Components to Add

- **A1 — Snapshot Publication:** certification ends by *publishing* the per-date artifact (bars + features + flags for the active universe) stamped with the version vector; artifacts are immutable, supersession is recorded, research reads artifacts only. (Subsumes: snapshot immutability question — **yes**, and this is how; provenance/schema-hash/feature-fingerprint/universe-fingerprint/CA-version/volume-normalization-version from the review prompt — **all yes**, they are exactly the artifact's version vector.)
- **A2 — Decision Log** (canonical, §6.1).
- **A3 — Ticker Book View** (§6.2).
- **A4 — Decision Authority/Policy split** (§6.3).
- **A5 — Operator command surface** (§6.5).
- **A6 — Clock module** (§6.6).
- **A7 — Versioned parameter store** (§6.7).
- **A8 — Nightly invariant checker:** status == fold(events) per target; artifact lineage consistency; Book View consistency. Cheap, and it converts the hybrid state model's one real risk (drift) into a detected condition (§9 below).

## 9. Simplicity Improvements (the Simplicity Test, applied)

- **Can the Certifier and Feature Engine merge?** Operationally yes — one "publication" stage runs checks then computes features then publishes (A1). Keep them as separate *modules* (different change cadences, R8 contract), single *stage*. Merge accepted.
- **Can Admission and Daily Evaluation merge?** Yes — they are one "registry maintenance" stage with two phases (evaluate, then admit) against the same artifact. The ADR already sequences them; make them one stage, two functions.
- **Can Ranking merge into the Decision Authority?** No — ranking is alpha-ordering (research-owned, changes often), decisions are constraint enforcement (safety-owned, changes never). The seam is the point.
- **Can the Risk Layer merge into the Decision Authority?** Tempting (it's consulted exactly once, by one caller) — but keep separate: risk *reporting* is a standalone output stage (fixes audit H-1 class), and the module boundary is what makes "the LLM can never out-vote risk" checkable.
- **Scheduler:** stays as thin as the ADR promises — in-process sequential stage lists + manifest rows. **Reject** event-driven orchestration (review Q8): a daily-cadence, single-machine system gains nothing from a bus except a new failure mode; partial-data-arrival is handled by resumable runs. Manifests as first-class objects — **yes** (they already are; keep them queryable rows, not files).
- **State model (review Q9):** **Hybrid confirmed** — status column maintained transactionally with the append-only event insert. Full event sourcing: rejected (replay machinery without a consumer — the artifacts serve replay). CQRS: rejected outright at this scale. The hybrid's drift risk is closed by A8, not by more architecture.
- **Scout properties (review Q5):** stateless — yes (all state belongs to the registry); deterministic — yes, per P6 (any scout needing network data reads ingested/certified data, never fetches); composable — no, explicitly: composition is confluence, which is the *ranking engine's* job; keep scouts flat, reject scout hierarchies as an abstraction with no payer. Conflicts — yes they conflict; resolution per §6.8.

## 10. Alternative Architectures (considered whole)

| Alternative | Verdict |
|---|---|
| **Fix-in-place** (apply audit fixes to current architecture, no v2) | Rejected: leaves pipeline plurality and ephemeral watchlists — the defect *generators* — intact. The audit is evidence this converges to whack-a-mole. |
| **Full event-sourced / CQRS platform** | Rejected: maximal machinery for a one-writer SQLite system; the hybrid + artifacts capture 90% of the value at 20% of the cost. |
| **File-first quant pipeline** (parquet artifacts + batch jobs, no registry DB) | Partially adopted: A1 *is* this pattern for the data plane. Rejected for the decision plane — targets are mutable, concurrent-read state with invariants; files model that badly. |
| **Event-driven orchestration** (data-arrival triggers) | Rejected for now (§9); the DAG model with resume covers late data; revisit only if intraday decision authority (OQ-2) is ever enabled. |
| **Redesign around Portfolio as the canonical object** (allocation-first) | Rejected *today*: with max_open=5 paper positions there is no allocation problem to architect for; the A4 policy seam and §11 note keep the door open without building the room. |

## 11. Long-Term Scalability Review (the Five-Year Test)

At 1,000 experiments / 500 hypotheses / 100 production strategies / multiple research programs:

- **Holds:** the registry (rows scale trivially); the Decision Log (append-only; *the* longitudinal dataset); artifact publication (research reads scale independently of production); the Authority/Policy split (strategies arrive as policies + scouts + parameters, the frame untouched); frozen-artifact research contract (already proven by the existing registry inversion).
- **Bends:** ranking with 100 strategies stops being a single edge-score — it becomes cross-strategy capital allocation. That is a *portfolio construction layer* between Ranking and Decision Authority. Do not build it now; the seam (policies propose sizes, authority disposes) is where it slots in.
- **Breaks (predictably, acceptably):** single SQLite file — at multi-program scale, split along the boundary this review already draws: corpus DB + published artifacts (data plane) / decision DB (decision plane). Because *all* cross-plane traffic already flows through artifacts (A1), this split is a deployment change, not an architecture change. This answers OQ-5 more decisively than the ADR did: **design the seam now, split later.**
- **Research invalidation check (review Q10):** microstructure/inefficiency/edge-discovery programs consume artifacts + Decision Log — served. Experiment framework: needs only what A1/A2 provide plus the parameter store (A7). RL/adaptive allocation: writes *policies* and *parameter sets*, reads Decision Log for training data — the one thing it must never do is bypass the Authority, and the architecture makes that structural. **No plausible research direction identified that invalidates the frame.**

## 12. Production Readiness Assessment

**Score: 7/10 as written → 9/10 with conditions.** Strong: fail-closed asymmetry, chokepoint entry, resumable DAGs, watchdog-on-outcomes, migration gates. Gaps closed by conditions: operator overrides (C6), correction protocol (C3), Telegram single-channel (HR6), clock authority (C7). Residual accepted risk: Stockbit as a data monopoly (R6) — visible and blocking under v2, but not solved by architecture; treat as a sourcing decision alongside OQ-4.

## 13. Research Readiness Assessment

**Score: 6/10 as written → 9/10 with conditions.** As written, research gets event logs and snapshot exports of unspecified mechanics. With A1 (artifacts), A2 (Decision Log incl. passes/vetoes — the counterfactual set), A7 (versioned parameters), and HR1's version-change visibility, the platform produces, as a *byproduct of operating*, exactly the datasets that edge attribution, experiment frameworks, and eventual RL need. The single most important research property — selection-bias-free decision records — comes from A2 and exists nowhere in the current system.

## 14. Final Recommendations

1. Adopt ADR-001's skeleton unchanged: two planes, integrity gate, scouts→registry→ranking→decision, DAG runs, migration phasing.
2. Apply amendments A1–A8; remove the four components in §7.
3. Elevate the **Decision Log** to the third canonical object; state it in the ADR's §4 with the same prominence as Snapshot and Target.
4. Rewrite ADR §5 with the simplified state machine (4 states + frozen flag + ticker ledger + event pairing).
5. Resolve OQ-1 *now* with this review's §6.8 (separate targets per thesis; conflicts owned by the Book View; precedence = validated directional source). It gates Phase 2 and the answer is available.
6. Re-scope the premarket run to delta digest before anyone builds the second decision pass.
7. Add the comparison harness to Phase 1's deliverables (HR5) and restate Phase 2's success criterion (HR4).
8. Record HR2's governance rule: certifier thresholds are versioned config, visible in run reports.

## 15. Verdict: **GO WITH CONDITIONS**

Not "Go": four of the ADR's load-bearing mechanisms need the amendments above, and two of them (snapshot mechanics, DSL) would be expensive to unwind after schemas exist. Not "Redesign": the diagnosis, the two-plane model, the chokepoint, the integrity gate, and the migration plan all survived adversarial review intact, and every alternative architecture examined loses to the amended design on this platform's actual constraints (single operator, SQLite, audited failure history).

**Binding conditions (all pre-Phase-2; C1–C3 pre-Phase-1-completion):**

| # | Condition | Blocks |
|---|---|---|
| C1 | Replace snapshot hash with versioned artifact publication (A1) | Phase 1 certifier design |
| C2 | Replace trigger/invalidation DSL with registered versioned evaluators + params (W1) | Phase 2 schema |
| C3 | Define the corpus-correction/supersession protocol (W7) — required *before* the C-1 volume reconciliation runs | Phase 1 |
| C4 | Simplified lifecycle: drop persisted TRIGGERED and COOLDOWN; add frozen flag + ticker cooldown ledger + Book View (W3/W5) | Phase 2 schema |
| C5 | Decision Log as canonical object; Decision Authority/Policy split (A2/A4) | Phase 3 design |
| C6 | Operator command surface emitting events (W8) | Phase 2 |
| C7 | Clock module + versioned parameter store (A6/A7) | Phase 1–2 |
| C8 | Premarket run re-scoped to delta digest (W6) | Phase 3 run DAGs |

With these conditions, proceed to implementation planning.

---

*Adversarial review conducted against the ADR text and the audit evidence only; no code inspected beyond what the audit already established, no code modified. Companion documents: `docs/ADR-001-Production-Engine-v2.md`, `Audit/PRODUCTION_ENGINE_AUDIT_2026-07-22.md`.*
