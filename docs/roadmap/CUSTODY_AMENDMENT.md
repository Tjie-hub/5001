# Custody Amendment — Propagation, Compatibility, Audit & Freeze Readiness

**Version:** 1.0 · **Status:** Amendment record · **Layer:** L0 — Governance & Scope
**Owner:** Research Program Director · **Date:** 2026-07-15 · **Supersedes:** — (initial version)
**Trigger:** [[CUSTODY_PROPAGATION_AUDIT]] verdict — custody is not a first-class concept in the architecture. Owner authorized a **canonical architectural amendment**, explicitly requiring Custody to enter the **Research Object Model itself**, not an extension layer.
**Authority:** An amendment and assessment record. **It creates no rules.** The canonical definition is [[CUSTODY_MODEL]]; the object model change is [[RESEARCH_OBJECT_MODEL]] v2.0. Governance: [[DECISION_LOG]] **D-022**.

---

## 1. What changed, and the finding that shrank it

### 1.1 The audit's premise was half wrong — in the useful direction

**The brief held that Custody is a first-class concept nowhere in the canonical architecture. That is false for L1.**

[[01_SCIENTIFIC_FOUNDATION]] **§2.4** already declares three epistemic custody states, and **R6** already supplies the enforcement rule **and all five of the brief's "define why" requirements, verbatim**: OOS is non-renewable · policy is insufficient · it must be a mechanism · the epistemological rationale · why the invisibility is decisive.

> **Consequence — this determined the whole amendment.** Had `CUSTODY_MODEL` restated those five, it would have created **exactly the parallel authority the brief forbids.** Custody's epistemology was never missing. **The *object* was.** L1 §0.5 excludes objects by design (*"those are L2+ concerns"*), so L1 declared custody and correctly could not model it — **and nothing beneath L1 ever did.**

### 1.2 Why the model is L2, not L1 — the decisive reason

**L1 is under pending certification.** Its independent adversarial sign-off is the **single open condition** of the Phase-A gate (**D-018/D-019**).

> **Amending L1 would invalidate the review package and reopen a gate that is one signature from closing.** The custody gap does not require it: L1 already has the epistemology, and per §0.5 the objects belong at L2 regardless. **We do not touch a document under review to say something we may say beneath it.**

### 1.3 The delivered change

| # | Artifact | Change |
|---|---|---|
| 1 | **[[CUSTODY_MODEL]]** *(new, L2)* | **The single canonical definition.** Custody as history; Receipt + Event objects; 8-state machine; the four domains |
| 2 | **[[RESEARCH_OBJECT_MODEL]] v1.0 → v2.0** | **The amendment.** §3 custody facet + class per object; §4 four new objects; §5 compatibility |
| 3 | **[[RESEARCH_VALIDATION_FRAMEWORK]] v1.0 → v1.1** | **Minor.** §0 custody precondition. §1–§3 untouched |
| 4 | **D-022** | Governance record |
| 5 | **This record** | Propagation · compatibility · audit · migration · RFCs · freeze |

**One new canonical document. One major amendment. One minor amendment. Zero redesigns. Zero code changes.**

---

## 2. Deliverables map

The brief requested ten numbered outputs. **Four documents was the wrong shape for one of its own constraints** — *"there must be exactly one canonical definition of Custody."* Four custody documents would have been four authorities. Consolidated:

| Brief | Delivered |
|---|---|
| 1 · CUSTODY_MODEL | [[CUSTODY_MODEL]] §0–§1 (**§0.1 cites L1; does not restate**) |
| 2 · Research Asset Ontology | **[[RESEARCH_OBJECT_MODEL]] v2.0 §3–§4** — *in the object model itself, per the brief's own requirement* |
| 3 · Custody State Machine | [[CUSTODY_MODEL]] §4 |
| 4 · Dataset Custody | [[CUSTODY_MODEL]] §5 |
| 5 · Experiment Custody | [[CUSTODY_MODEL]] §6 |
| 6 · Evidence Custody | [[CUSTODY_MODEL]] §7 — **formalized only** |
| 7 · Publication Custody | [[CUSTODY_MODEL]] §8 |
| 8 · Propagation Matrix | **§3 here** |
| 9 · Backward Compatibility | **§4 here** |
| 10 · Institutional Audit | **§5 here** |
| A–D | **§6–§9 here** |

---

## 3. Propagation Matrix

| # | Document | State | Justification |
|---|---|---|---|
| 1 | **[[RESEARCH_OBJECT_MODEL]]** | 🔴 **MAJOR — APPLIED, v2.0** | Custody had **0 mentions**. The brief requires custody *in the object model itself*. §3 declares the facet + class per object; §4 adds Dataset Partition, Candidate, Evidence, Publication, Custody Event/Receipt. **v1.0's 8 objects unchanged** |
| 2 | **[[RESEARCH_VALIDATION_FRAMEWORK]]** | 🟡 **MINOR — APPLIED, v1.1** | Custody had **0 mentions**. Validation presupposes custody: a gate over an unknown-custody partition validates an unknown. §0 added. **§1–§3 untouched — the gatekeeper is correct** |
| 3 | **[[MARKET_INEFFICIENCY_RESEARCH_PIPELINE]]** | 🟡 **MINOR — RFC-2** | 0 mentions. **S4 Data Preparation** must emit a partition scheme; **S6** must consume a released partition. *Also carries **G-7**: S5 demands bit-identity where L1 §8.3 requires conclusion-invariance.* **Deferred — it is a "supporting reference," canonical logic lives in the Operating Model (PHASE_A_ARCHITECTURE_REVIEW R7)** |
| 4 | **[[RESEARCH_OPERATING_MODEL]]** | 🟡 **MINOR — RFC-3** | 1 passing mention, no rule. §7's Discovery→Confirmation→Accepted pipeline **is** L1 §2.4's three states; it must cite [[CUSTODY_MODEL]] §4.5 for the asset binding. **Deferred — touches roles/gates, and RD-2/RD-3 rationale debt is already open there** |
| 5 | **[[FAILURE_LIBRARY_SCHEMA]]** | 🟢 **NO CHANGE** | Already **C-IMMUTABLE** in substance and in code (`failure_registry`, append-only). Custody class declared in ROM §3.2. **Nothing to amend** |
| 6 | **[[RESEARCH_OBJECT_SCHEMA]]** | 🟢 **NO CHANGE** | Already carries `custody_partition` on **O4** and custody in 15 places. **It anticipated this amendment correctly.** Its facet 4 now resolves to [[CUSTODY_MODEL]] §3 rather than to nothing |
| 7 | **[[EXPERIMENT_STANDARD]]** | 🟢 **NO CHANGE** | §3's one-shot procedure is now **backed by a model** rather than by prose. **G-9 stands as recorded** — the model does not build the mechanism (§5.3) |
| 8 | **[[EVIDENCE_MODEL]]** | 🟢 **NO CHANGE** | **DG9** (custody breach → E3+ lost) already exists and now resolves to a defined breach. The X-axis is unaffected |
| 9 | **[[HYPOTHESIS_LIFECYCLE]]** | 🟢 **NO CHANGE** | **T5**'s custody guard now resolves to [[CUSTODY_MODEL]] §5.4. The 12 states are the *claim* axis; custody's 8 are the *asset* axis (**CU-1**) — orthogonal, no collision |
| 10 | **[[RESEARCH_OS_MASTER_ROADMAP]]** | 🟡 **MINOR — RFC-5** | §2 L2 row (now 14 docs); §5 must record that **OOS-custody enforcement is still policy**; **§7 exit checklist unchanged** — custody was never the freeze blocker (§9) |
| 11 | **[[01_SCIENTIFIC_FOUNDATION]]** | 🟢 **NO CHANGE — deliberately** | **§2.4 + R6 already own custody's epistemology.** Amending it would duplicate, and would **invalidate the pending review package (D-019)**. §1.2 |
| 12 | **[[TAXONOMY_AND_NAMING_STANDARD]]** | 🟢 **NO CHANGE** | Custody states are a *Lifecycle State* axis, already provided for in §2/§6. **No new structural axis** |
| 13 | **`research/gatekeeper`** *(code)* | 🟢 **NO CHANGE** | **Already conformant.** §4.2 |
| 14 | **`research/knowledge`** *(code)* | 🟢 **NO CHANGE** | Append-only; lineage conformant. §4.2 |
| 15 | **`security/audit_trail.py`** *(code)* | 🟢 **NO CHANGE — and must not be touched** | RBAC/security, **not** the custody log (**CU-7**). Conscripting it would subordinate an epistemic control to an access-control table |
| 16 | **`research/tracking.py`** *(code)* | 🟡 **MINOR — RFC-6** | `dataset_fingerprint` pins `ohlcv`+`corporate_actions` only. **Sound for the gatekeeper** (it recomputes from raw); **misnamed for anyone else.** Also the weak `SUM(CAST(close AS INTEGER))` digest |
| 17 | **`research/jobs.py`, `wf_scores`, `wf_edge`** *(code)* | 🟡 **MINOR — RFC-7** | Declared **C-DERIVED**. **The overwrite is correct behaviour and is not forbidden.** The defect is that a cache is read as a publication (**CU-18**) |
| 18 | **`research/walkforward_multi.py`** *(code)* | 🔴 **MAJOR — RFC-1** | `walk_forward_split()` is a computation, not a control. **This is G-9** |

**Totals: 1 major applied · 2 minor applied · 1 major deferred (RFC-1) · 5 minor deferred · 9 no change.**

---

## 4. Backward Compatibility Analysis

> ## ✅ Every existing implementation remains valid. Zero code changes are required by this amendment.

### 4.1 The compatibility claim

**The amendment is additive at every point of contact:**

| Surface | Before | After | Break? |
|---|---|---|---|
| ROM's 8 objects + fields | v1.0 | **byte-identical** — §3/§4 appended | **No** |
| `gate_evidence` | append-only, `statistic_json` | **unchanged.** Now named *Evidence, C-IMMUTABLE* | **No** |
| `gate_decisions` | append-only, hashes + provenance | **unchanged.** Now named *Experiment Custody* | **No** |
| `hypothesis_links` | append-only | **unchanged.** Now *C-APPEND-ONLY* | **No** |
| `failure_registry` | append-only | **unchanged.** Now *C-IMMUTABLE* | **No** |
| `regime_profiles`, `research_runs` | append-only | **unchanged** | **No** |
| `research/knowledge` storage | append-only except sanctioned status | **unchanged.** The exception is already named in code | **No** |
| `wf_scores`, `wf_edge`, `backtest_cache` | `INSERT OR REPLACE` | **unchanged — the overwrite stays legal.** Declared C-DERIVED | **No** |
| Validation Framework §1–§3 | FDR/DSR/PBO, market, scientific | **unchanged** | **No** |

### 4.2 Why the gatekeeper needs nothing

**It was already right.** Verified at [[CUSTODY_PROPAGATION_AUDIT]] §8:

```
load_ohlcv_df(ohlcv)  →  recompute trades  →  candidate_hash + config_hash
                                            →  dataset_fingerprint(ohlcv+corp_actions)
                                            →  git_commit + seed
                                            →  gate_decisions  (append-only)
                                            →  gate_evidence   (append-only, statistic_json)
```

It recomputes from raw rather than trusting a mutable cache; it fingerprints what it actually read; a superseding evaluation is a **new `decision_id`** (`storage.py:7`). **That is OS-2, OS-3, OS-4, EX-7 and CU-9 satisfied — in the one place a claim is adjudicated.** The amendment **names** it. It changes nothing.

> **The brief's instruction — *"Do NOT redesign. Only formalize."* — was correct and is honoured literally: [[CUSTODY_MODEL]] §7 contains no design. It contains a citation and a verdict.**

### 4.3 What C-DERIVED buys

Declaring `wf_scores`/`backtest_cache` **C-DERIVED** rather than demanding immutability is what makes this amendment cheap:

> **The tables are caches. Overwriting a cache is correct.** The defect was never the overwrite — it was that a cache is read as a publication. **So no table is rewritten. One boundary is drawn (CU-18), and one object is added at it (Publication).**

**Had the amendment demanded immutability of `wf_scores`, it would have required rewriting `jobs.py`, `optimizer.py`, `backtest_roller.py`, `screener/`, and `routes/` — for no epistemic gain, because a recomputable cache carries no evidence.**

### 4.4 Migration cost of the *architecture*

**Zero.** No table, no column, no function, no test. The corpus's documents change; the running system does not. **What the amendment creates is the obligation to build RFC-1 — and that obligation existed under R6 before this document was written.**

---

## 5. Institutional Audit — does Custody eliminate the six defects?

**Honest scoring. A model is not a mechanism, and the distinction is the whole audit.**

| # | Defect | Eliminated? | Assessment |
|---|---|---|---|
| **1** | **Unknown Evidential State** | 🟡 **Modelled, not eliminated** | The model makes the state **expressible and checkable** — a claim can now *say* its partition was released once, to this hypothesis, at this time. **But until RFC-1 exists, the field is filled by the researcher.** Per **R6** an attestation *"is a statement of intent, not a control."* **The unknown becomes visible; it does not become known** |
| **2** | **Invisible OOS contamination** | 🟡 **Made visible in principle** | **CU-5**: `ordinal > 1` is a breach detectable **only because the receipt exists**. **The model creates the instrument; RFC-1 installs it.** Today there is no receipt, so contamination remains invisible |
| **3** | **Policy-only enforcement** | 🔴 **NOT eliminated — and this is the point** | **The amendment is architecture. R6 demands mechanism.** [[CUSTODY_MODEL]] §5.1 states plainly that Dataset Custody is absent. **A model of a control is not a control.** **G-9 remains open at BLOCKING** |
| **4** | **Hidden review invalidation** | 🟢 **Eliminated conceptually** | **CU-3** makes the dependency explicit and non-optional: Evidence Custody over unknown Dataset Custody certifies an unknown. **This was the hidden thing** — it is now the model's second-most prominent rule, and it is why G-9 precedes G-4 |
| **5** | **Evidence ambiguity** | 🟢 **ELIMINATED** | Evidence is **C-IMMUTABLE**, append-only, superseded-never-overwritten, bound to a decision, provenance-carrying — **and it was already all of those.** The ambiguity was **naming**, and naming is exactly what this amendment does. **Genuinely closed** |
| **6** | **Reproducibility gaps** | 🟡 **Narrowed** | Fingerprint scope is now declared (**CU-15**) rather than assumed; **Environment Identity is recorded as absent** (§6.2) rather than silently missing. **G-7 (bit-identity vs conclusion-invariance) is recorded per ADR-L1-008, not resolved** |

### 5.1 The audit's verdict

> **One of six eliminated. Three modelled. One narrowed. One explicitly not.**

**That is the correct outcome and inflating it would be the failure.** Per **R6**, the gap between *modelled* and *eliminated* is precisely the gap between **a statement of intent and a control** — and this amendment is, by its own nature, a statement of intent. **It makes the right thing sayable, checkable, and mandatory in the architecture. It does not make it true.**

> **Defect 5 is genuinely eliminated because it was never a design gap — it was a naming gap, and naming is what an architecture does.** Defects 1–3 are design gaps whose closure is code (**RFC-1**), and no document closes them.
>
> **An amendment that claimed to eliminate all six would be claiming that writing the model built the mechanism. Per LIM8 the claim and the reality would be indistinguishable on inspection of the corpus — which is exactly the failure mode custody exists to prevent.**

---

## 6. A · Architectural Impact Assessment

### 6.1 Impact

| Dimension | Assessment |
|---|---|
| **Scope** | 1 new canonical doc · 1 major amendment (ROM v2.0) · 1 minor (RVF v1.1) · 5 deferred RFCs |
| **Blast radius** | **L2 only.** L1 untouched (§1.2). L0 untouched. **No layer boundary moves** |
| **Code impact** | **Zero.** §4 |
| **Parallel authority** | **None.** One definition ([[CUSTODY_MODEL]]); L1 §2.4/R6 remains the epistemology and is **cited, never restated** |
| **New structural axis** | **None.** Custody states are a *Lifecycle State* per [[TAXONOMY_AND_NAMING_STANDARD]] §2/§6 |
| **Reversibility** | **High.** Additive; ROM v1.0 is recoverable |

### 6.2 The one structural change that matters

> **Dataset Partition is promoted from attribute to object.** Everything else follows.

Per **CU-11**: a Dataset is Locked while its train partition is Consumed a hundred times and its OOS partition is Released once. **One object cannot hold four states.** And per **CU-2**, custody is a *history* — a history attaches to the thing accessed, and **the window is accessed; the dataset is not.**

**The counter-argument, answered:** *the split is deterministic from a rule, so why store it?* — **Determinism is not custody.** `walk_forward_split(12, 3)` yields identical windows on every call, **which is precisely why anyone can materialize the test window at any time with no record.** **Reproducibility is what makes a window dangerous, not what makes it safe.**

### 6.3 What this amendment deliberately did not do

| Not done | Why |
|---|---|
| Amend L1 | **§1.2** — L1 has the epistemology; amending it invalidates D-019's review package |
| Redesign the gatekeeper | **It is correct** (§4.2). The brief said *formalize only* |
| Make `wf_scores` immutable | **§4.3** — it is a cache; the overwrite is correct |
| Conscript `audit_events` | **CU-7** — RBAC ≠ custody |
| Build RFC-1 | **This is an architectural amendment.** Mechanism is a separate, larger decision |
| Claim the six defects are closed | **§5.1** — three are code, not prose |

---

## 7. B · Migration Strategy

**Architecture: complete on merge. Implementation: staged, and RFC-1 is the only one that matters.**

| Stage | Work | Breaks? | Effort |
|---|---|---|---|
| **M0 · Naming** | Declare classes on existing tables. `gate_evidence` = Evidence (C-IMMUTABLE); `hypothesis_links` = C-APPEND-ONLY; `wf_scores` = C-DERIVED | **No** | **Documentation only — done in ROM §3.2** |
| **M1 · Custody log** | `custody_events` + `custody_receipts`, append-only. **Additive tables; nothing reads them yet** | **No** | Small |
| **M2 · Partition objects** | Materialize `dataset_partitions` from the existing deterministic scheme. **`walk_forward_split` keeps working unchanged** | **No** | Small |
| **M3 · Release gate** ⚠️ | Route OOS reads through a release function that writes a receipt first (**CU-14**). **This is RFC-1 and the only stage with teeth** | **Yes — deliberately.** Direct OOS reads must stop being possible | **Medium.** The real work |
| **M4 · Publication object** | Materialize publications from caches at the research boundary; five lineages (**CU-17**) | Low | Medium |
| **M5 · Blind partition** | Seal a window with a release date (**CU-13**) — **the only mechanism giving a Confirmation window a *provably unspent* custody state, because it has no release path at all.** *Yields E6 + maximal custody assurance, **not** E7 — corrected per **D-023*** | **No** | Small, **high value** |

> **M0–M2 and M5 are non-breaking and can land in any order.** **M3 is the amendment's purpose.** A migration that stops at M2 has built a custody log that records nothing — **which per LIM8 is indistinguishable from custody, and is therefore worse than none.**

> **Rule for M3:** **receipt-then-release, never release-then-receipt** (**CU-14**). A crash between read and receipt would erase the record of a spent window while the window stays spent. **Receipt-first fails safe; release-first fails silent — and silent failure is the entire threat model.**

---

## 8. C · RFC List

| # | RFC | Priority | Owner | Notes |
|---|---|---|---|---|
| **RFC-1** | **Dataset Custody mechanism** — sealed OOS partitions, receipt-gated release (M3) | **P0** | Research Architect | **This is G-9.** The only RFC that converts intent into control. **The only blocking gap the institution can close by itself** |
| **RFC-2** | Pipeline S4/S6 custody + **G-7** bit-identity | P2 | Research Architect | Supporting reference; low leverage |
| **RFC-3** | Operating Model §7 ↔ [[CUSTODY_MODEL]] §4.5 | P2 | CRO | Touches roles/gates; RD-2/RD-3 debt open |
| **RFC-4** | Experiment Receipt + Environment Identity | P1 | Research Architect | §6.2. Environment **explains** divergence, never requires identity (§8.3) |
| **RFC-5** | Roadmap §2/§5 | P1 | Program Director | **§7 exit checklist unchanged** |
| **RFC-6** | Fingerprint scope + the `SUM(CAST(close AS INTEGER))` digest | P2 | Research Architect | Sound for the gatekeeper; misnamed elsewhere |
| **RFC-7** | Publication object over `wf_scores`/`wf_edge` (M4) | P1 | Research Architect | The research→capital boundary (§0.1) |
| **RFC-8** | Blind partition (M5) | **P1** | Research Architect | **Small, cheap, and the only way to make a Confirmation window *provably* unspent rather than *supposedly* unspent.** *No E7 claim — see **D-023*** |

### 8.1 Priority, restated against the owner's ordering

The owner proposed: **P0 G-9 · P1 G-4 · P2 governance.** **The audit and this amendment both support it, and supply the argument:**

> **G-4 is partially void until G-9 closes.** A reviewer's mandate is to attempt refutation (**PV-2**). **A reviewer cannot attack a claim whose custody state is unknowable** — they cannot determine whether the out-of-sample result before them was out-of-sample. Per §8.2, a claim that cannot be attacked has *structural immunity from criticism*; per **P3** that is **not a knowledge claim**.
>
> **Hiring a second researcher to review an unknowable substrate buys the appearance of independent review. Per LIM8 the appearance is indistinguishable from the real thing — which makes it worse than no review, because it would be recorded as one.**

**G-9 before G-4 is not a sequencing preference. It is a precondition for G-4 to mean anything.**

---

## 9. D · Freeze Readiness

### 9.1 Is the architecture complete?

> ## ✅ Yes. The conceptual gap is closed.

Custody is now: defined once ([[CUSTODY_MODEL]]) · grounded in L1 §2.4/R6 without duplication · **a mandatory facet of the Research Object Model itself, not an extension** ([[RESEARCH_OBJECT_MODEL]] v2.0 §3) · modelled as a deterministic state machine · declared per object · propagated with every remaining delta named as an RFC.

**The brief's critical requirements, checked:**

| Requirement | Met |
|---|---|
| No parallel authority | ✅ One definition; L1 cited, never restated |
| **Custody in the ROM itself, not an extension** | ✅ **ROM v2.0 §3–§4** |
| Backward compatible | ✅ **Zero code changes** (§4) |
| Evidence Custody formalized, not redesigned | ✅ §7 contains a citation and a verdict |
| No unrelated redesign | ✅ Blast radius L2; §6.3 |
| Minimal canonical change | ✅ 1 new doc, 1 major, 1 minor |

### 9.2 Can Research OS v1.0 be frozen?

> ## ❌ NO — and custody was never the reason.

| Blocker | Status | Closed by |
|---|---|---|
| **G-8 · L1 unsigned** | **OPEN — BLOCKING** | **An external adversarial signature (D-019).** Unchanged since D-018 |
| **G-4 · T9 unreachable at N=1** | **OPEN — BLOCKING** | A second researcher. **And per §8.1, partially void until G-9** |
| **G-9 · Dataset Custody unmechanised** | **OPEN — BLOCKING.** *Now modelled, still unenforced* | **RFC-1** |
| **G-1 · O10–O14 proposed** | OPEN — MAJOR | A **D-005** amendment |
| **G-6 · P1/P2/P3 family merges** | OPEN — MAJOR | CRO, **before P1's first registration** |

**The custody amendment closes a *conceptual* gap. It does not touch the condition that has blocked the freeze since D-018: one external signature.**

> **The clean statement: custody was never the freeze blocker. G-8 was, and still is.** What this amendment changes is that a freeze would no longer be freezing an architecture with a hole in it. **It would be freezing a complete architecture that is one signature and one mechanism from being true.**

### 9.3 The condition on freezing that this amendment creates

> **Rule (D-022):** **Research OS v1.0 must not be frozen while G-9 is open, even if D-019 is signed tomorrow.**

**Not because the architecture is incomplete — §9.1 says it is complete — but because of what a freeze *means*.** A freeze declares a baseline the institution builds on. Per **R6** and **§2.4**:

> *"unenforced custody produces a system whose evidential state cannot be known even by its own operators."*

**Freezing a v1.0 in which custody is modelled but unenforced would make "custody exists" a true statement about the corpus and a false statement about the institution.** Per **LIM8** those two are indistinguishable to any reader of the frozen baseline — and a frozen baseline is precisely the artifact future readers will trust without re-deriving.

**Freeze order:**

```
1. RFC-1  (G-9)   ← mechanism. The institution can do this alone.
2. D-019  (G-8)   ← external signature. Requires a person.
3. D-005  (G-1)   ← admit O10–O14
4. Re-run CUSTODY_PROPAGATION_AUDIT   ← mechanical, cheap
5. FREEZE v1.0
—— G-4 (N=2) does not block the freeze. It blocks Accepted Knowledge.
```

### 9.4 The honest summary

**Three sessions produced three findings, each beneath the last:**

| | Finding |
|---|---|
| **Knowledge Corpus** | **G-4** — the institution cannot *accept* knowledge at N=1. **A ceiling it can see** |
| **Protocol Layer** | **G-9** — the rule everything rests on is unenforced. **A floor it cannot see** |
| **This amendment** | **The floor was never in the blueprint.** Custody was declared in L1 and modelled nowhere — so there was nothing to build even had someone tried |

> **The amendment does not fix the floor. It puts it in the drawing.** That is what an architecture can do, and it is the necessary precondition for RFC-1 — because you cannot build a mechanism for a concept the object model does not contain.
>
> **G-9 remains the institution's most urgent problem and its only blocking gap solvable without hiring anyone.**
