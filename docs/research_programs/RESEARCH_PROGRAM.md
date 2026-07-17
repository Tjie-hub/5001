# Research Program — Operating Layer

> **The live operating instance of the Research OS.** The frozen standards state *what must be true* of a Program; this document states *what this institution is actually running*. It decides only what the standards leave to the CRO — active programs, intake flow, prioritization, cadence, and operating thresholds — and **cites** every rule rather than restating it.

**Version:** 1.0 · **Status:** Operating (standing) · **Layer:** Program operating layer — an *instance* of the L0 standards, not a standard
**Owner:** Research Director / CRO · **Last Updated:** 2026-07-17 · **Branch of record:** `ops/hardening-2026-07-10` · **Supersedes:** — (initial version)
**Governed by:** [[RESEARCH_PROGRAM_STANDARD]] (what a Program must be) · [[RESEARCH_PROGRAM_PLAYBOOK]] (how one is run) · [[RESEARCH_PROTOCOL]] (the day-one entry point)
**Renewable companion:** [[OBJECTIVES_2026H2]] — the annual objectives + prioritized backlog. **Only that file turns over.** This one is standing and is designed to run for years without redesign.
**Baseline inheritance (binding):** authored against an L1 that is **certified-ready, NOT FROZEN** ([[DECISION_LOG]] D-018/D-019). If review alters the E/C scale, R15, or §5.2, the operating thresholds below are void pending re-derivation, not grandfathered.

---

## 0. What this document is — and is not

This is a **thin operating instance** (owner decision, 2026-07-17). It introduces **no normative content**. Every rule cited here lives in a frozen standard and is the single source of truth (SSOT); where this document and a standard appear to conflict, **the standard wins** and the conflict is a defect to be reported, not resolved here.

| This document owns | This document must never contain |
|---|---|
| Which Programs are active, and their declared families | A re-statement of PG-1…PG-17, TC1–TC8, the E/C/X scale, or the six §5.2 elements |
| The intake queue and the monthly execution rhythm | A second definition of a gate, a tier, or a lifecycle state |
| The prioritization rubric for admissible candidates | A profitability, Sharpe, or capital objective (PG-1, PG-12) |
| The operating thresholds declared *per hypothesis at registration* | A universal statistical threshold (those are per-hypothesis, ex ante — R5) |

---

## 1. Mission

> Discover **statistically defensible IDX market inefficiencies**, mechanism-first, and carry each to **the highest evidence tier this institution can honestly reach**.

Per the four operating priorities set at charter (binding tie-breakers, in order):

1. **Evidence over documentation.**
2. **Experiments over architecture.**
3. **Reproducibility over speed.**
4. **Statistical validity over backtest performance.**

The mission is an allocation of the one scarce resource — **the credibility of a claim** ([[RESEARCH_PROGRAM_STANDARD]] §1.1, P4). It is not an allocation of capital, and capital never flows backward into it ([[01_SCIENTIFIC_FOUNDATION]] §0.1: *research produces knowledge; capital consumes it; the reverse dependency is prohibited*).

### 1.1 Program Non-Goals

State these first, because every one of them is a failure mode that reads as success:

- This program is **not a production deployment roadmap**. Deployment is downstream of, and gated by, evidence it does not produce.
- This program is **not a trading-strategy catalogue**. A registered hypothesis is a risked claim about a mechanism, not a strategy to be shipped.
- This program is **not an optimization exercise**. Search without a barrier yields significant results whether or not any effect exists ([[RESEARCH_PROGRAM_STANDARD]] §7.1, R2).
- This program is **not evaluated by profitability, Sharpe ratio, CAGR, or win rate**. Per PG-12 / R7.1, *profit is not evidence* — "both fortune and error produce them." Judging the program by return metrics inverts the causal order it exists to protect.
- Program success is measured by **scientific rigor, reproducibility, accumulated evidence, and research lineage** — see §8.

---

## 2. Active Programs

The institutional register is [[RESEARCH_OS_MASTER_ROADMAP]] §3 (canonical, unaltered — D-006). This section records the CRO's **operating selection** and the **G-6 family decision** (owner ruling, 2026-07-17).

### 2.1 The G-6 decision — merge into honest wide families

Running the family-drawing procedure ([[RESEARCH_PROGRAM_PLAYBOOK]] §1.2) against the register's Current Programs surfaces mandatory PG-7 merges on the confound structure of [[MARKET_INEFFICIENCY_TAXONOMY]] §4. **The owner ruled to merge** (Option A — "the correct cost, not an objection," [[RESEARCH_PROGRAM_PLAYBOOK]] §4.3):

- **I5 ↔ I7** (inventory vs adverse selection) — *confounds*: both predict displacement-with-flow. Severity is zero for discriminating them (R3) ⇒ **one family**.
- **I6 ↔ I12** (illiquidity vs capacity shielding) — *near-inseparable* (LIM2) ⇒ **one family**.
- **I8 → I2** (reconstitution flow → closing auction) — *upstream*: I8's mechanism produces I2's observations ⇒ evidence not independent ⇒ **one family**.

> **This closed the G-6 window.** Per R7.5 / PG-6 a family may never later be narrowed or split. The merge was available once; it has now been exercised. The only future remedy for a mis-drawn boundary is **termination and a new family from zero, forfeiting every survivor** ([[RESEARCH_PROGRAM_PLAYBOOK]] §1.2, PB-2).

### 2.2 The active program table

| Program | Merged from | Declared family (append-only, monotonic — PG-3) | Capability class (D-002) | Status |
|---|---|---|---|---|
| **P-M · Microstructure Flow** | P1 + P2 | **I5, I6, I7, I12** — order-flow imbalance + liquidity/toxicity as one denominator | **PROXY** (L3 LOB not held) | **Ready for Hypothesis Registration** |
| **P-A · Auction Dislocation** | P3 | **I2, I3, I8** — reconstitution/close mechanism as one denominator | **PROXY** | **Ready for Hypothesis Registration** |
| **P4 · Informed-Flow** | — | held, undeclared | 🟡 blocked on **LIM4** — history maturity (~3.5 mo) | **Not initiated** — timebox watch only (see [[OBJECTIVES_2026H2]] O5) |
| **P5 · L3 Microstructure** | — | — | 🔵 **TC2 pre-met** — L3 LOB unobtainable | **Retained, not initiated** (D-006) |
| **P6 · Latency / HFT** | — | — | ⚫ out of scope | **Retained, not initiated** (D-006) |

> **"Ready for Hypothesis Registration," not "Initiated."** The program is prepared and its family is drawn, but per the frozen lifecycle **formal initiation occurs at the first hypothesis registration** (G1 / T4, [[HYPOTHESIS_LIFECYCLE]] §4.1). Until then no family slot is consumed and the denominator is zero.
>
> **The family for P-M and P-A is declared as of this document.** The first T4 in each program joins that family permanently (OS-10); nothing registered under it ever leaves — not on failure, not on withdrawal, not on supersession (PG-3).

### 2.3 P0 — the delivered precedent

Program **P0 (v3 Edge Pipeline, NR7)** is the one worked instance, executed before the standards existed and now frozen ([[RESEARCH_MASTER_PLAN]]). Its 42-cell family collapse — *significant against zero, C-low under its own denominator* — is this operating layer's standing evidence that the family boundary is load-bearing ([[EVIDENCE_MODEL]] EV-4). Its family declaration is retroactively binding; no successor may narrow it.

---

## 3. Research Pipeline

The pipeline is **not redefined here.** It is the ten-stage flow of [[MARKET_INEFFICIENCY_RESEARCH_PIPELINE]] (canonical), whose executable realization for S7–S8 is `research/gatekeeper` ([[RESEARCH_OS_RECONCILIATION]] §4):

```
Literature → Mechanism → Hypothesis Registration → Data → Feature
   → Experiment → Statistical Validation → Robustness → Peer Review → Promotion
```

The ordering **is** the mechanism-first argument made procedural: the mechanism (S2) is authored **blind to the result** (S6), per [[01_SCIENTIFIC_FOUNDATION]] §7.3. This operating layer adds nothing to the stage definitions; it only routes candidates through them via §5–§7 below.

---

## 4. Standard Experiment Lifecycle

The lifecycle is the state machine of [[HYPOTHESIS_LIFECYCLE]] (canonical). It is cited, not restated. The two facts that govern daily operation:

- **G1 is a one-way door** (HL-2). Before it — states `DRAFT` / `REFINING` — refinement is unlimited and free. After it — `REGISTERED` onward — the claim is frozen; any edit is R7.4 (threshold migration) or R15 (rescue) and **deletes the evidence retroactively**.
- **One transition, one receipt** (HL-1). No transition without a durable evidence receipt — already realized by `research/knowledge`'s receipt-bound `set_status` and R-10.

Terminal states that are **not failures** and must never be filed as `FAILED`: `WITHDRAWN` (nothing risked), `RETIRED` (constraint removed, DG2), `DECAYED` (was true, now false, F9/DG3). Conflating them corrupts the §8 diagnostic ([[HYPOTHESIS_LIFECYCLE]] §3.1).

---

## 5. Hypothesis Intake Process

Intake is procedure, owned by [[RESEARCH_PROTOCOL]] §5.2 and [[RESEARCH_PROGRAM_PLAYBOOK]] §2.1. This section records only the **operating queue** through which candidates reach G1.

### 5.1 The flow

```
Observation / literature / rule-change
        │  (Discovery era — unlimited, unrecorded, no claim: OS-9)
        ▼
   DRAFT ──▶ REFINING   (free era — refine without limit; no receipt required)
        │
        ▼  admissibility gate (§6.1) — the default answer is NO
   ┌────────────────────────────────────────────────────────┐
   │  Bring all SIX of §5.2 or G1 REFUSES (not defers):     │
   │   mechanism (M-class + constraint + participant) ·      │
   │   directional prediction · null · scope ·               │
   │   ex-ante criterion incl. effect size · multiplicity    │
   │   family — plus: mechanism blind_to OOS, power/MDE       │
   │   showing the test CAN fail (R2), refutation condition   │
   │   in one sentence (R14), data resolves Available/        │
   │   Obtainable (D-002), CRO approval                       │
   └────────────────────────────────────────────────────────┘
        │
        ▼  T4 / G1
   REGISTERED — joins the program family PERMANENTLY (PG-3, OS-10)
```

### 5.2 Operating rules for intake

- **Refusal is the cheapest and most common outcome.** Most proposed hypotheses should be refused at G1 ([[RESEARCH_PROGRAM_PLAYBOOK]] §2.1). Refusal costs nothing; registration costs a family slot forever.
- **Ask the two free-kill questions first** ([[RESEARCH_PROGRAM_PLAYBOOK]] §1.1): *Why has nobody already taken this?* (name a §6.3 barrier, or R17 presumes no effect) and *Why us?* (§6.4 — deviation is least likely where capital is abundant).
- **Every near-miss is recorded.** Catching yourself about to violate one of the six rules is data about the institution; write it to the Failure Library or Decision Log at the moment it happens (PR-2).

---

## 6. Experiment Prioritization Framework

Two stages, in strict order. **Stage 1 is a gate; Stage 2 is a ranking.**

### 6.1 Stage 1 — admissibility (binary, non-negotiable)

A candidate is **inadmissible** — auto-rejected regardless of any other merit — if it fails any of:

| Gate | Refuse because |
|---|---|
| No persistence **barrier** named | R17 — default presumption is the effect does not exist |
| Mechanism authored **after** looking at the result | §7.3 / U3 — a counterfeit |
| The test **could not fail** (no power / MDE) | R2 — a test that cannot fail produces no evidence |
| Predicted effect **< friction** | F4 — free kill under the cost model |
| Any of the six §5.2 elements missing | G1 refuses (R14) |

### 6.2 Stage 2 — weighted ranking of the survivors

Only candidates that clear Stage 1 are ranked. Higher score = earlier execution. Weights reflect the frozen priors:

| Factor | Direction | Basis |
|---|---|---|
| **Barrier durability** | M6 structural (rule-based, no capital removes it) > M4 > … > M5 behavioral (processing-cost, falls monotonically) | PB-1, EMT §8.2 |
| **A-priori plausibility** | Higher where capital is scarce and the mechanism under-exploited; lower where well-studied | §6.4 |
| **Capability-now** | Available Today > Obtainable Later > Future | D-002 |
| **Refutation cheapness** | Prefer candidates a cheap F1/F2 can kill early — high throughput of the scarce resource | §5.3, PB-1 |

> **Binding operating rule (owner refinement, 2026-07-17):** **Weighted ranking applies only after admissibility. No ranking score may override a failed admissibility gate.** A high-scoring candidate that fails Stage 1 is rejected; the score exists to *order the admissible*, never to *rescue the inadmissible*.

The live scored backlog is in [[OBJECTIVES_2026H2]] §3, not here — it turns over; the rubric does not.

---

## 7. Research Cadence

Two layers that must not be confused: **gate reviews are event-triggered; work is monthly.**

### 7.1 Gate reviews — event-triggered only (there is no calendar review)

Per PG-9, a review is triggered by an **event that could change what the institution believes**. A calendar review, absent an event, is activity that reads as diligence and consumes the scarce resource while appearing to protect it — it is prohibited.

| Trigger | Action |
|---|---|
| **Family milestone** (every N registrations, declared at initiation) | Re-derive C for **every prior claim** — the denominator grew (DG4); confidence fell retroactively |
| **Any VALIDATED** | Independent adversarial review before promotion — **blocked at N=1** (see §9) |
| **Market-structure change (D1)** | **Immediate, highest priority.** M6 mechanisms may have died — decay is a step function on rule change (EV-11) |
| **Confounding discovered** | PG-7 merge evaluated immediately — it cannot be done later (R7.5) |
| **Assumption failure (A1–A8)** | DG8 — every dependent claim re-derives at the tier surviving assumptions support |
| **Termination criterion met (TC1–TC8)** | Mandatory, immediate, non-deferrable (§3, PG-13) |
| **Calendar** | **None** |

### 7.2 Monthly execution rhythm (a work cadence, not a gate)

This is *what the researcher does*, and it produces **no gate decision by the calendar** — it feeds the event-triggered gates above. It is the "monthly cadence" the program runs on without violating PG-9:

| Week | Focus |
|---|---|
| **Wk 1** | **Literature sourcing → intake.** New candidates enter DRAFT; the only blind mechanism supply (LR / S1–S2) |
| **Wk 2–3** | **Experiment execution** on the top-priority *admissible* candidates (§6) through the pipeline S4–S8 |
| **Wk 4** | **Backlog grooming + F1–F9 snapshot + capacity-track check-in.** Groom, don't gate; snapshot the failure distribution; review G-8/G-9 progress ([[OBJECTIVES_2026H2]] O4) |

### 7.3 Annual renewal — the only redesign point, and it is not a redesign

Once per period the **objectives file is renewed** ([[OBJECTIVES_2026H2]] → next horizon). Programs, families, pipeline, lifecycle, metrics, and this cadence are standing and carry forward unchanged. **Renewal is not redesign** — it re-scopes the year's work within a fixed machine. This is the property that lets the program run for years.

---

## 8. Success Metrics

Anchored to the F1–F9 failure distribution (PG-10, §5.3 — *the highest-value analysis the Failure Library enables*), and **deliberately excluding** return/Sharpe/CAGR/win-rate (§1.1, PG-12) and accepted-knowledge count (QS-4 forbids judging an N=1 institution by a number its own rules forbid it to increase).

| Metric | Healthy signal | Basis |
|---|---|---|
| **Failure Library growth** | Steady accumulation of falsifications with complete lineage — the primary cumulative asset | R12, §4.4 |
| **F-distribution shape** | Falsifications concentrated **early and cheap (F1/F2)** — claims killed before spending data/custody/multiplicity | §5.3 |
| **Denominator growth** | Family N rising and honestly recorded — the durable product every successor inherits | R7.5, LIM3, PG-15 |
| **Competent refutations** | Each mapped efficiency boundary is a first-class product, of equal standing to a validated mechanism | R12, PG-11 |
| **Lineage integrity** | **Zero X0** — no irreproducible/void claims; every lineage unbroken | R19, OS-12 |
| **Capacity progress** | Measurable movement toward closing G-8/G-9 (the C3 unlock) | EV-9, [[OBJECTIVES_2026H2]] O4 |

> **The alarm metric: "no failures."** A program with no failures is the most dangerous state, not the best — either its tests could not fail (R2 ⇒ no evidence) or failures are not being recorded (R12 ⇒ every future DSR silently biased). Both are severe; neither is visible from the results. Treat a clean sheet as a defect to investigate.

---

## 9. Exit Criteria for Hypothesis Promotion

Promotion criteria are **not defined here** — they are the gates of [[HYPOTHESIS_LIFECYCLE]] and the caps of [[EVIDENCE_MODEL]] §5. The operating bar a candidate must clear to advance:

1. **Registered (G1 / T4)** — all six §5.2 elements, mechanism blind, family declared, power shown, CRO-approved.
2. **Passes statistical validation (S7)** — clears the pre-registered thresholds under **family-adjusted DSR, FDR, and PBO** (`research/gatekeeper`). Thresholds are declared **per hypothesis at registration** (ex ante, R5) — this document sets none.
3. **Survives robustness (S8)** — significant net of the versioned friction/cost model and across the declared regime scope.
4. **Survives forward evidence within a fixed timebox** — the timebox is fixed at registration and **never extended to rescue** (PG-14, §4.2): *a claim that runs out of time is unproven, not proven.* Concrete per-hypothesis thresholds follow the P0/NR7 precedent (a declared minimum N, a per-trade GO bar, a fixed forward window) but are set at registration, not universally here.
5. **Independent adversarial review (S9 / K7)** — required for C1→C2 and every tier above.

### 9.1 The N=1 ceiling — structural, not a staffing delay

Per **EV-9 / LIM6 / LIM8**, C1→C2 requires K7 adversarial review **by someone other than the author**, which a single-researcher institution cannot supply. Therefore:

> **The terminal evidence tier reachable in this program is C2** ("survived a severe test; not yet independent of its author or its family"; shadow only, **no capital**). Promotion to **ACCEPTED** (T9) requires **C3 = E5 + X3** and is **structurally blocked** until a second, non-author reviewer exists (gap **G-4**). This is recorded as a ceiling, not worked around by lowering the bar ([[RESEARCH_PROTOCOL]] §7.2, ADR-L1-007).

The capacity to lift this ceiling is objective **O4** in [[OBJECTIVES_2026H2]].

---

## 10. Definition of a Validated Market Edge

The definition is owned by [[RESEARCH_VALIDATION_FRAMEWORK]] and [[EVIDENCE_MODEL]]. The operating statement:

> **A market edge is *validated* when a registered hypothesis has cleared all three validation axes on out-of-sample data whose custody was intact, its mechanism was authored blind to the result, its multiplicity family is fully counted, and it has survived forward evidence within a fixed timebox — reaching at minimum E4/C2.**

All three axes are required; passing one does not substitute for another:

| Axis | Requirement | Basis |
|---|---|---|
| **Statistical** | Significant OOS under **family-adjusted DSR, FDR, PBO** | [[RESEARCH_VALIDATION_FRAMEWORK]] §1 |
| **Market** | Survives institutional friction; capacity quantified; stable across (or scoped to) regimes; decay half-life measured | §2 |
| **Scientific** | Explained by market micro-economics; **mechanism authored blind**; independently reproducible from specification alone (X3); novel vs Accepted Knowledge | §3 |

**Two boundaries that make this definition honest:**

- **Profit is not validation.** An unexplained profitable result is R7.1 — *both fortune and error produce them.* It is not an edge; it is an observation awaiting a mechanism.
- **In this institution, "validated" tops out at C2** — *validated pending independent replication.* Full validation to C3+ ("capital, under decay monitoring") requires **E5 + X3**: independent reproduction the institution cannot self-supply at N=1 (EV-9). A C2 edge is real evidence and licenses **shadow deployment only — never capital** ([[EVIDENCE_MODEL]] §3).

---

## 11. Traceability

| This document | Cites (SSOT) | Never restates |
|---|---|---|
| §1 mission, §1.1 non-goals | [[RESEARCH_PROGRAM_STANDARD]] §1, PG-1, PG-12, R7.1 | PG-1/PG-12 |
| §2 active programs, G-6 merge | [[RESEARCH_PROGRAM_STANDARD]] §9, [[RESEARCH_PROGRAM_PLAYBOOK]] §1.2/§4, [[MARKET_INEFFICIENCY_TAXONOMY]] §4, PG-3/6/7 | The register (D-006) |
| §3 pipeline | [[MARKET_INEFFICIENCY_RESEARCH_PIPELINE]] (10 stages) | The stage definitions |
| §4 lifecycle | [[HYPOTHESIS_LIFECYCLE]] §3–§5, HL-1/HL-2 | The state machine |
| §5 intake | [[RESEARCH_PROTOCOL]] §5.2, [[RESEARCH_PROGRAM_PLAYBOOK]] §2.1 | The six §5.2 elements |
| §6 prioritization | [[RESEARCH_PROGRAM_PLAYBOOK]] §1.1/§2.1, PB-1, §6.4, D-002 | §6.4, PB-1 |
| §7 cadence | PG-9, P4 (anti-bureaucracy) | The trigger definitions |
| §8 metrics | [[RESEARCH_PROGRAM_STANDARD]] §5.2, §5.3 (F-distribution), R12, R19, QS-4 | The F-mode definitions |
| §9 exit criteria | [[HYPOTHESIS_LIFECYCLE]] gates, [[EVIDENCE_MODEL]] §5, EV-9 | The gates and caps |
| §10 validated edge | [[RESEARCH_VALIDATION_FRAMEWORK]] §1–§3, [[EVIDENCE_MODEL]] §3 | The three axes' internals |

**Upstream:** [[RESEARCH_PROGRAM_STANDARD]] · [[RESEARCH_PROGRAM_PLAYBOOK]] · [[RESEARCH_PROTOCOL]] · [[DATA_FEASIBILITY_STUDY]] (D-002).
**Downstream / renewable:** [[OBJECTIVES_2026H2]] (objectives + scored backlog — the only file that turns over).
