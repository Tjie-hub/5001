# Custody Model

> **The single canonical model of Custody in the Institutional Research OS.** There is no other. Any document describing custody is subordinate to this one, and this one is subordinate to [[01_SCIENTIFIC_FOUNDATION]] §2.4/R6.

**Version:** 1.0 · **Status:** Canonical (candidate — inherits an unsigned L1; §0.5) · **Layer:** L2 — Research Architecture
**Owner:** Research Architect · **Last Updated:** 2026-07-15 · **Supersedes:** — (initial version)
**Realized in v3:** **substantially, and unnamed.** `gate_decisions` + `gate_evidence` (append-only, `candidate_hash`/`config_hash`/`dataset_fingerprint`/`git_commit`/`seed`, superseding-by-new-id) realize **Experiment Custody (§6) and Evidence Custody (§7) today**. `hypothesis_links`, `failure_registry`, `regime_profiles`, `research_runs` realize immutable lineage and history. **Dataset Custody (§5) and Publication Custody (§8) have no realization.** Evidence: [[CUSTODY_PROPAGATION_AUDIT]] §8.
**Scientific basis:** [[01_SCIENTIFIC_FOUNDATION]] **§2.4 (the three epistemic custody states) and R6 (custody must be enforced, not requested)** — **this document does not restate them; it obeys them.** Also §2.3 (R5), §4.3 (weight is a property of process), §8 (P8, R19).
**Governance:** [[DECISION_LOG]] **D-022** · [[CUSTODY_AMENDMENT]] (propagation, migration, freeze)

---

## 0. Authority

### 0.1 One definition, and it was already half-written

**The audit's premise was that custody is a first-class concept nowhere in the architecture. That is false, and the correction shrinks this amendment.**

[[01_SCIENTIFIC_FOUNDATION]] **§2.4 already owns custody as an epistemic concept** — three states (Discovery / Confirmation / Accepted Knowledge), each mapped to a custody regime over evidence — and **R6 already supplies the enforcement rule and its entire rationale**, verbatim:

- *why OOS is non-renewable* → R6: *"it can be spent exactly once per hypothesis"*
- *why policy is insufficient* → R6: *"a prohibition that relies on a researcher's discipline is a statement of intent, not a control"*
- *why it must be a mechanism* → R6: *"every unlogged glance silently converts it into in-sample data while leaving its appearance unchanged. **This invisibility is precisely why it requires a mechanism**"*
- *the epistemological rationale* → §2.4: *"unenforced custody produces a system whose evidential state cannot be known even by its own operators"*

> **Therefore this document does not define why custody exists. L1 §2.4/R6 does, and restating it here would create exactly the parallel authority this amendment exists to prevent.**

**What was missing is not the concept. It is the *object*.** L1 §0.5 excludes objects by design: *"It does not define objects, schemas, fields, stages, gates, thresholds… Those are L2+ concerns."* **So L1 declared custody and, correctly, could not model it. Nothing below L1 ever did.** That gap — not the concept — is what this document closes.

### 0.2 Why this document is L2, not L1

Three reasons, and the third is decisive:

1. **L1 already has the epistemology.** Adding it here would duplicate, not complete.
2. **Custody objects are objects.** Per §0.5 they are an L2 concern by L1's own scope rule.
3. **L1 is under pending certification.** Its independent adversarial sign-off is the single open condition of the Phase-A gate ([[DECISION_LOG]] **D-018/D-019**). **Amending L1 now would invalidate the review package and reopen a gate that is one signature from closing.** The custody gap does not require it. **We do not touch a document under review to say something we may say beneath it.**

### 0.3 The two axes — do not collapse them

| Axis | States | Owner | About |
|---|---|---|---|
| **Epistemic custody** | Discovery · Confirmation · Accepted Knowledge | **[[01_SCIENTIFIC_FOUNDATION]] §2.4 — closed set** | *What the institution is licensed to do with a **claim*** |
| **Asset custody** | Created · Registered · Partitioned · Locked · Released · Consumed · Superseded · Archived | **§4 here** | *What state a **research asset** is in* |

**These are orthogonal and both are necessary.** A claim in *Confirmation* is licensed to open one OOS partition once; the partition itself moves Locked → Released → Consumed. The first says *may I*; the second says *has it happened*. **Collapsing them would either put asset mechanics into L1 (violating §0.5) or put epistemic licensing into L2 (creating a second authority over R6).**

> **Rule CU-1 (justified by §2.4, D-020 R-a):** L1 owns the **three epistemic states** as a closed set. This document owns the **eight asset states**. **This document may not add, remove, or reinterpret an epistemic state.** §4.5 maps between them; the mapping is subordinate.

### 0.4 What this document does not do

No storage engine, no schema DDL, no API, no code. Field *types* appear only where the type is a **scientific** constraint (append-only is **R12**, not a storage preference). Physical realization is L4.

**It also does not redesign anything.** Per §7, Evidence Custody is **formalized, not designed** — it exists and is correct.

### 0.5 Baseline inheritance (binding)

Authored against [[01_SCIENTIFIC_FOUNDATION]] v1.0 — **certified-ready, NOT FROZEN** (**D-018/D-019**). If review alters §2.4 or R6, this document is **void pending re-derivation, not grandfathered** (§0.4 of L1).

---

## 1. Custody, defined

> **Custody is the recorded history of an asset's identity, state, and access.**

Not a property. Not an attribute. **A history.**

> **Rule CU-2 (justified by R6, §2.4):** **Custody is a history, not an attribute, because the thing it must detect leaves no trace in the asset.**
>
> R6: *"every unlogged glance silently converts it into in-sample data **while leaving its appearance unchanged**."*
>
> A contaminated out-of-sample partition and a clean one are **bit-identical**. No inspection of the asset — the rows, the hash, the schema, the file — distinguishes them. **The only difference is what happened to it.** Therefore custody cannot be stored *on* the asset; it must be stored *about* the asset, as an ordered, immutable record of events. **An attribute can be set. A history can only be appended to.**

**This single sentence generates the entire model.** Everything below is a consequence:

| Because custody is a history… | …therefore |
|---|---|
| it cannot be a boolean on a row | **Custody Events** (§2.3) are first-class and append-only |
| it must say *who* and *when* and *once* | **Custody Receipts** (§2.2) exist |
| a partition's state is a fact, not a label | **Dataset Partition** is an **object**, not a column (§5.2) |
| a re-run cannot overwrite | **Superseding** rather than mutation (§4.4) |
| the record must outlive the claim | **Retention** is mandatory (§3.9) |

---

## 2. Custody as a first-class object

Three objects. **These are the amendment.** Everything else is these three applied.

### 2.1 · Custody Domain

The four domains of the chain. **They are not four models — they are one model over four asset classes.**

```
Dataset Custody  →  Experiment Custody  →  Evidence Custody  →  Publication Custody
    (§5)                 (§6)                   (§7)                 (§8)
   ABSENT              PARTIAL              ✅ BUILT               ABSENT
```

> **Rule CU-3:** The chain is **ordered and load-bearing in order.** Evidence Custody over an experiment whose dataset custody is unknown certifies **an unknown**. Per [[CUSTODY_PROPAGATION_AUDIT]] §6, this is why **G-9 precedes G-4**: a reviewer cannot attack a claim whose custody state is unknowable, and per §8.2 a claim that cannot be attacked has *structural immunity from criticism* — which per **P3** means it is **not a knowledge claim**.
>
> **A perfect Evidence Custody built on an absent Dataset Custody is a precise record of an unknown quantity.** That is this system's current state (§7.3).

### 2.2 · Custody Receipt

**The record that an access happened.** Not that it was permitted — that it **occurred**.

| Field | Why |
|---|---|
| `receipt_id` | Identity |
| `asset_ref` + `asset_version` | What was accessed |
| `accessor` | **Who.** A person or a process, never "the system" |
| `purpose_ref` | **Which hypothesis.** OOS is spent *per hypothesis* (R6) |
| `occurred_at` | When |
| `access_kind` | `RELEASE` (granted) / `CONSUME` (read) |
| `ordinal` | **Which access this is.** For a sealed partition it is **always 1** |
| `prior_receipt` | The chain — null only for the first |

> **Rule CU-4 (justified by R6):** **A receipt records an access, never a permission.** A system that records permissions records intentions; per R6 an intention *"is a statement of intent, not a control."* **The receipt is written at the moment of access, by the mechanism performing it — not by the researcher, and not beforehand.**

> **Rule CU-5 (justified by R6, §2.4):** **`ordinal > 1` on a sealed partition is a custody breach, and the breach is the receipt's existence — not its content.** It is detectable **only** because the receipt exists. Absent receipts, a second read is indistinguishable from a first, and per R6 that indistinguishability is the whole problem.

### 2.3 · Custody Event

**The append-only audit record of a state transition.** Every transition in §4 emits exactly one.

| Field | Why |
|---|---|
| `event_id` · `asset_ref` · `asset_version` | Identity |
| `from_state` → `to_state` | The transition (§4) |
| `receipt_ref` | For RELEASE/CONSUME — else null |
| `actor` · `occurred_at` | Who, when |
| `fingerprint_before` / `fingerprint_after` | **A change with equal fingerprints is a no-op; a change with unequal fingerprints on a Locked asset is a violation** |
| `justification_ref` | For SUPERSEDE — what authorized it |

> **Rule CU-6 (justified by R12, OS-3, §4.3):** **Custody Events are append-only and are never deleted.** Per §4.3: *"an institution that discards process history has not merely lost an audit trail — it has destroyed its ability to know what its own numbers mean."* **A deleted custody event does not weaken a claim; it makes the claim's evidential state unknowable — which per R19/EV-6 is X0: void.**

> **Rule CU-7:** **`audit_events` (`security/audit_trail.py`) is NOT the custody log and must not be conscripted.** It is RBAC/security — `actor_role`, `actor_fingerprint`, `action` — recording *who called an endpoint*. Custody records *what happened to a research asset*. **Merging them would subordinate an epistemic control to an access-control table, and the two have different retention, different authority, and different consumers.** See [[CUSTODY_PROPAGATION_AUDIT]] §5.

---

## 3. The custody facet — the nine attributes every asset carries

**This is the ROM amendment** ([[RESEARCH_OBJECT_MODEL]] v2.0 §3, D-022). Every research asset — without exception — declares all nine.

| # | Attribute | Meaning |
|---|---|---|
| **1** | **Identity** | A stable id that survives supersession. **Never a name; names are reused** |
| **2** | **Ownership** | Who may create, transition, supersede, archive. Per [[RESEARCH_OPERATING_MODEL]] §5 |
| **3** | **Custody** | Its custody class (§3.1) and current asset state (§4) |
| **4** | **Lineage** | Inbound and outbound edges. Append-only (**OS-12**) |
| **5** | **Lifecycle** | Its admissible states — a subset of §4's eight |
| **6** | **Fingerprint** | What content-hash pins it, **and explicitly what that hash does not cover** (§5.5) |
| **7** | **Superseding rules** | What a change forks vs. amends. Per **OS-4**, pre-registered content is frozen on use |
| **8** | **Audit requirements** | Which transitions emit Custody Events |
| **9** | **Retention** | How long, and what may never be deleted |

### 3.1 Custody classes

| Class | Rule | Assets |
|---|---|---|
| **C-IMMUTABLE** | No change after creation. A change is a new asset | Evidence, Gate Decision, Custody Event, Receipt, Failure Record, Observation |
| **C-FROZEN-ON-USE** | Mutable until first referenced; frozen thereafter (**OS-4**) | Hypothesis, Feature, Cost Model, Experiment design, Dataset Partition |
| **C-SEALED** | Frozen **and** access-controlled. Release is a metered, receipted event | **OOS and Blind partitions only** (§5.3) |
| **C-APPEND-ONLY** | Grows; never shrinks; never reordered | Lineage, Family declaration, Custody log, Knowledge Record history |
| **C-DERIVED** | Recomputable from custodied inputs. **Carries no custody of its own** | wf_scores, backtest_cache (§8.3) |

> **Rule CU-8:** **Every asset declares exactly one class.** An asset with no declared class defaults to **C-IMMUTABLE** — the safe direction. Per **OS-5/R6**, where a rule can be enforced by structure it must be; an undeclared asset is a rule enforced by nobody.

---

## 4. The Custody State Machine

**Deterministic. Universal across asset classes. Not every state applies to every class (§4.6).**

### 4.1 States

| State | Meaning | Terminal? |
|---|---|---|
| **CREATED** | Exists; no identity assigned; no fingerprint | no |
| **REGISTERED** | Identity assigned; fingerprint computed; lineage bound | no |
| **PARTITIONED** | Divided into named partitions, each a **first-class asset** (§5.2). **Datasets only** | no |
| **LOCKED** | Frozen. Fingerprint is authoritative. **No content change is admissible** | no |
| **RELEASED** | A **specific** partition granted to a **specific** purpose. **Emits a Receipt** | no |
| **CONSUMED** | Read. **For C-SEALED: the window is spent, permanently, for that purpose** | no |
| **SUPERSEDED** | A newer version exists. **The asset itself is unchanged and retained** | no |
| **ARCHIVED** | Retained, out of the active corpus. **Never deleted** | **yes** |

### 4.2 Allowed transitions

| # | Transition | Guard | Event |
|---|---|---|---|
| **T-C1** | ∅ → CREATED | — | ✅ |
| **T-C2** | CREATED → REGISTERED | Identity + fingerprint + lineage | ✅ |
| **T-C3** | REGISTERED → PARTITIONED | **Datasets only.** Partition scheme declared **ex ante** (§5.4) | ✅ |
| **T-C4** | REGISTERED → LOCKED | Non-partitioned assets: **frozen on first use** (OS-4) | ✅ |
| **T-C5** | PARTITIONED → LOCKED | Every partition sealed; scheme immutable | ✅ |
| **T-C6** | LOCKED → RELEASED | **Purpose named** (a registered hypothesis) · epistemic state permits it (§4.5) · **`ordinal` computed** | ✅ **+ Receipt** |
| **T-C7** | RELEASED → CONSUMED | Read occurred | ✅ **+ Receipt** |
| **T-C8** | CONSUMED → LOCKED | **C-FROZEN-ON-USE only.** A re-readable partition returns to Locked. **Never for C-SEALED** (§4.3) | ✅ |
| **T-C9** | LOCKED / CONSUMED → SUPERSEDED | A new version registered, with justification | ✅ |
| **T-C10** | LOCKED / CONSUMED / SUPERSEDED → ARCHIVED | Retention reached | ✅ |

### 4.3 Illegal transitions — **the substance**

Per [[HYPOTHESIS_LIFECYCLE]] §5's discipline: **the valuable content of a state machine is the paths that were deliberately not built.**

| # | The move | Why there is no path |
|---|---|---|
| **✗ CU-X1** | **CONSUMED → LOCKED, for a C-SEALED partition** | **You cannot un-spend a window.** Per R6 OOS is *non-renewable* — *"spent exactly once per hypothesis."* **This is the machine's load-bearing absence** |
| **✗ CU-X2** | **CONSUMED → RELEASED (same purpose)** | A second read is a **second experiment**, against a window that is now in-sample. Not a re-release — a **new asset and a new family member** (**PG-4, EX-7**) |
| **✗ CU-X3** | **LOCKED → REGISTERED** | Unfreezing. Per **OS-4** mutability after use is **R7.4 enabled by schema** |
| **✗ CU-X4** | **LOCKED → LOCKED with a different fingerprint** | Content change under a lock. **The lock is the fingerprint** |
| **✗ CU-X5** | **PARTITIONED → PARTITIONED (re-partition)** | Re-partitioning after seeing results is **R7.4 applied to data** — it moves the boundary the test was defined against |
| **✗ CU-X6** | **SUPERSEDED → anything but ARCHIVED** | Resurrection. Per **R15/HL-3**, the only path forward is a **new** asset |
| **✗ CU-X7** | **ARCHIVED → anything** | Terminal |
| **✗ CU-X8** | **any → ∅ (delete)** | **Prohibited absolutely.** Per §4.4 a deletion *"corrupts every future multiplicity calculation by hiding the denominator"* — by an amount **LIM3** says is unmeasurable |
| **✗ CU-X9** | **Any transition without a Custody Event** | Per **CU-6** an unrecorded transition **did not occur institutionally**, and per R6 it is indistinguishable from no transition |

### 4.4 Superseding, not overwriting

> **Rule CU-9 (justified by OS-3, OS-4, R12):** **A re-run produces vN+1. It never overwrites vN.**
>
> This is the owner's requirement — *"kalau ada rerun, harus Evidence v2, bukan overwrite"* — stated generally. **It is already how the gatekeeper behaves:** `research/gatekeeper/storage.py:7` — *"A superseding evaluation is a new decision_id."* **§7 formalizes that; it does not change it.**
>
> **vN moves to SUPERSEDED and is retained.** Per **R12**, a mutable object is a suppressible object. The old version is not garbage — it is **the denominator's business** (**R7.5**).

### 4.5 Binding to L1's epistemic states

**The mapping. It is subordinate to §2.4 (CU-1); it does not extend it.**

| Epistemic state (**L1 §2.4**) | Licensed asset transitions |
|---|---|
| **Discovery** | **T-C6/T-C7 on in-sample partitions only, unlimited.** *"Unlimited searching, no claims."* **Everything found is E0** |
| **Confirmation** | **T-C6 on the OOS partition — once, for one registered hypothesis.** `ordinal` must be 1 |
| **Accepted Knowledge** | **No transitions.** *"Sealed. Further contact requires re-registration"* |

> **Rule CU-10 (justified by §2.4, R6):** **The epistemic state is the guard on T-C6; the asset state is the record of what T-C6 did.** A release without a licensing epistemic state is a breach even if the receipt is perfect — **a perfectly recorded violation is still a violation**, and the receipt's value is that it makes the violation *visible* (**CU-5**), not lawful.

### 4.6 Applicability

| Asset class | CREATED | REGISTERED | PARTITIONED | LOCKED | RELEASED | CONSUMED | SUPERSEDED | ARCHIVED |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| Dataset | ✅ | ✅ | ✅ | ✅ | — | — | ✅ | ✅ |
| **Dataset Partition** | ✅ | ✅ | — | ✅ | ✅ | ✅ | ✅ | ✅ |
| Feature | ✅ | ✅ | — | ✅ | — | — | ✅ | ✅ |
| Hypothesis | ✅ | ✅ | — | ✅ | — | — | ✅ | ✅ |
| Candidate | ✅ | ✅ | — | ✅ | — | — | ✅ | ✅ |
| Experiment | ✅ | ✅ | — | ✅ | — | ✅ | ✅ | ✅ |
| Evidence | ✅ | ✅ | — | ✅ | — | — | ✅ | ✅ |
| Gate Decision | ✅ | ✅ | — | ✅ | — | — | ✅ | ✅ |
| **Publication** | ✅ | ✅ | — | ✅ | ✅ | ✅ | ✅ | ✅ |
| Knowledge Record | ✅ | ✅ | — | ✅ | — | — | ✅ | ✅ |
| Failure Record | ✅ | ✅ | — | ✅ | — | — | — | ✅ |

**Only Dataset Partition and Publication traverse RELEASED/CONSUMED** — they are the only assets whose *access* is itself an event with consequences. **Failure Record never supersedes**: a recorded failure is a fact about what happened, and a later failure is a different fact (**R12**, **OS-7**).

---

## 5. Dataset Custody — **the absent stage**

### 5.1 Current state

Per [[CUSTODY_PROPAGATION_AUDIT]] §2.1: **absent.** `research/walkforward_multi.py:129` `walk_forward_split()` returns `{'train','test',...}` dicts. **It is a computation, not a control.** Nothing prevents reading `['test']`. Nothing records that it was read.

### 5.2 A partition is not an attribute — **the amendment's core claim**

> **Rule CU-11 (justified by CU-2, R6):** **A Dataset Partition is a first-class asset with its own identity, fingerprint, custody class, and state. It is not a column on a dataset, a date range in a config, or a flag on a row.**
>
> **Three reasons, and the third is decisive:**
>
> 1. **It has its own state.** A dataset is Locked; its train partition is Consumed a hundred times; its OOS partition is Locked and, for one hypothesis, Released-then-Consumed once. **One asset cannot hold four states.**
> 2. **It has its own access history.** Custody is a history (**CU-2**). A history attaches to the thing accessed. **The OOS window is accessed; the dataset is not.**
> 3. **An attribute can be set; a history can only be appended to.** If the partition is a field, then *changing the partition* is an UPDATE — and re-partitioning after seeing results (**CU-X5**) becomes a one-line edit that leaves no trace. **Per R6 that is not a weak control. It is the absence of one.**
>
> **Objection, answered:** *"the split is deterministic from a rule, so why store it?"* — Because **determinism is not custody.** `walk_forward_split(train=12, test=3)` deterministically yields the same windows every call, and that is exactly why **anyone can materialize the test window at any time with no record.** Determinism makes the partition *reproducible*; it does nothing to make it *sealed*. **The reproducibility of a window is what makes it dangerous, not what makes it safe.**

### 5.3 Partition kinds

| Kind | Custody class | Epistemic state licensing access | Release |
|---|---|---|---|
| **Train** | C-FROZEN-ON-USE | Discovery | **Unlimited.** Receipts recorded, not metered |
| **Validation** | C-FROZEN-ON-USE | Discovery | Unlimited within Discovery. **Anything found is E0** |
| **Test** | C-FROZEN-ON-USE | Discovery | Unlimited. **Not OOS** — see below |
| **Out-of-Sample** | **C-SEALED** | **Confirmation only** | **Once per hypothesis. `ordinal` must be 1** |
| **Blind** | **C-SEALED** | **Never, until a declared future date** | **Not releasable.** Maximal custody assurance for a Confirmation window — **not E7** (CU-13) |

> **Rule CU-12:** **"Test" and "Out-of-Sample" are different partitions and conflating them is the single most likely way this model gets defeated in practice.** A walk-forward *test* fold is used repeatedly during Discovery — that is its purpose, and it is legitimate. **An OOS partition is spent once, in Confirmation, against one pre-registered hypothesis.** Per R6 the OOS window is the **non-renewable** one. **A system that seals the walk-forward test fold will be worked around within a week, because the researcher needs it; a system that seals only the OOS window is enforceable, because it is only needed once.**

> **Rule CU-13 (justified by R6, §2.4; corrected per [[DECISION_LOG]] D-023):** **A Blind partition is C-SEALED with no release path until its declared date.** It is the only asset in the institution that is **not readable by anyone, including the CRO**.
>
> **It yields E6-equivalent evidence with maximal custody assurance. It does not yield E7, and no partition can.** Per [[01_SCIENTIFIC_FOUNDATION]] §4.2, E7 requires **data that did not exist at registration** — *"the only evidence immune to **every** retrospective bias"*. A Blind partition's data **existed**: it was universe-selected, corporate-action-adjusted, and vendor-cleaned **with knowledge of its period**, and it inherits every one of those retrospective biases (**A3**, **LIM1**). The object model makes this unavoidable rather than incidental — **T-C2 requires a fingerprint at REGISTERED, and you cannot fingerprint data that does not exist.** Per §4.2, E7 *"accrues in wall-clock time and **cannot be accelerated**."* **A Blind partition does not accelerate it. Nothing can.**
>
> **What it is for.** An ordinary OOS partition is C-SEALED but **releasable** — so per **G-9** nothing mechanically prevents it being read, and per **R6** an unenforced seal *"is a statement of intent, not a control."* **A Blind partition has no release path at all.** Its window is therefore **provably unspent** rather than *supposed* to be — the strongest custody assurance obtainable for a Confirmation test (**E3**). **Its value is on the custody axis, not the evidence axis.**

### 5.4 Release policy

```
RELEASE(partition, purpose) requires:
  [ ] partition.state == LOCKED
  [ ] purpose is a REGISTERED hypothesis (frozen at G1)         (HL-2)
  [ ] purpose.epistemic_state licenses this partition kind      (§4.5)
  [ ] for C-SEALED: ordinal(partition, purpose) == 1            (CU-5)
  [ ] partition.kind != BLIND, or now >= partition.release_date (CU-13)
  ⇒ emit Receipt + Custody Event. THEN release. Never the reverse order.
```

> **Rule CU-14 (justified by R6, CU-4):** **The receipt is written before the data is handed over.** A receipt written after a successful read records reads that succeeded; **a crash between read and receipt would erase the record of a spent window while the window stays spent.** **Receipt-then-release fails safe; release-then-receipt fails silent** — and per R6 silent failure is the entire threat model.

### 5.5 Fingerprint policy — and what today's does not cover

**Current** (`research/tracking.py:70–95`): `dataset_fingerprint` hashes **`ohlcv` (is_final=1) + `corporate_actions`** and **nothing else.**

> **Rule CU-15 (justified by OS-2, §4.3):** **Every fingerprint declares its scope, and the declaration is part of the fingerprint's meaning.** A fingerprint that pins less than its name implies is worse than none: it produces **false confidence that the inputs are pinned**.
>
> **Assessment of the current fingerprint — it is sound where it is used, and misnamed:**
> - **For the gatekeeper: correct.** It recomputes from raw `ohlcv` via `load_ohlcv_df` (`candidate.py:139–147`), so the raw fingerprint genuinely pins what it read. ✅
> - **For any consumer of `wf_scores` / `backtest_cache`: it pins something the consumer never read.** Those tables are `INSERT OR REPLACE` and unfingerprinted (§8.3).
>
> **Amendment: `dataset_fingerprint` is renamed in concept to a *corpus* fingerprint** and each asset declares its own. **Derived assets are C-DERIVED and carry the fingerprint of their inputs, not of themselves** (§8.3).

**Secondary (recorded, low severity):** the per-ticker digest uses `SUM(CAST(close AS INTEGER))`. Truncation is likely lossless on IDX integer tick prices, but **a sum is order-insensitive and collision-permissive** — offsetting errors on two days yield an identical digest. For a control whose purpose is *detecting change*, a sum is a weak instrument. **RFC-6** (§ [[CUSTODY_AMENDMENT]]).

### 5.6 Provenance and immutable history

Every partition carries: the **scheme** that produced it (declared ex ante, **CU-X5**), its **parent dataset** and that dataset's fingerprint, its **own** fingerprint, and its **complete receipt chain** — append-only, never deleted (**CU-6**).

---

## 6. Experiment Custody — **partial, and mostly built**

### 6.1 What exists

`research/gatekeeper/storage.py`, `gate_decisions`, **append-only, no UPDATE, no DELETE**:

```
decision_id · run_id · strategy_fn · candidate_hash · config_hash
dataset_fingerprint · git_commit · seed · final_state · failing_stage
forward_test_rule · summary_json · decided_at
```

**Mapped to the brief's required identities:**

| Required | Realized | State |
|---|---|---|
| **Execution Identity** | `decision_id`, `run_id` | ✅ |
| **Configuration Identity** | `config_hash` | ✅ |
| **Code Identity** | `git_commit` | ✅ |
| **Seed / Randomness** | `seed` | ✅ |
| **Input Fingerprints** | `dataset_fingerprint`, `candidate_hash` | ✅ **scope-limited — §5.5** |
| **Output Fingerprints** | `summary_json`, `gate_evidence` | ⚠️ recorded, not hashed |
| **Execution Provenance** | `decided_at` + `research_runs` envelope | ✅ |
| **Environment Identity** | — | ❌ **absent** |
| **Experiment Receipt** | — | ❌ **absent** |

### 6.2 The two gaps

> **Rule CU-16:** **An Experiment Receipt binds an execution to the custody events that fed it.** `gate_decisions` records *what the experiment used*. It does not record *that the OOS partition was released to this hypothesis, once, at this moment, to this accessor.* **Provenance answers "what data"; custody answers "by what right, and had it been spent."**

**Environment Identity** is absent: interpreter, library versions, hardware class. Per **§8.3** the requirement is **conclusion-invariance, not bit-identity** — so environment is recorded to **explain** a divergence, never to require identity. **RFC-4.**

---

## 7. Evidence Custody — **formalize only. Do not redesign.**

### 7.1 It exists and it is correct

`research/gatekeeper/storage.py`, `gate_evidence`, **append-only**:

```
evidence_id · decision_id · stage · verdict · statistic_json · ...
    "one row per stage per decision (the 'why')"
    "Append-only by rule: no UPDATE, no DELETE."
    "A superseding evaluation is a new decision_id."
```

### 7.2 Why this already satisfies institutional Evidence Custody

| Requirement | Satisfied by | Rule |
|---|---|---|
| Evidence is immutable | `gate_evidence` takes **no UPDATE, no DELETE** | **C-IMMUTABLE**, OS-3 |
| Bootstrap results cannot change after the gate | `statistic_json` is written once per stage per decision | **CU-9** |
| A re-run yields v2, not an overwrite | *"A superseding evaluation is a new `decision_id`"* | **CU-9, T-C9** |
| Evidence is bound to its decision | `decision_id` FK; one row per stage | Lineage |
| The decision is immutable | `gate_decisions` append-only | **C-IMMUTABLE** |
| Provenance travels with it | `dataset_fingerprint`, `git_commit`, `seed`, `config_hash` | **OS-2** |

> **Verdict: `gate_evidence` + `gate_decisions` are a correct, complete implementation of Evidence Custody. They require no change.**
>
> **This amendment gives them a name, a class (C-IMMUTABLE), a place in the chain (§2.1), and an entry in the object model. It changes not one line of code and not one column.** Per [[RESEARCH_OS_RECONCILIATION]] §4: *where an OS concept maps to an existing v3 mechanism, the OS document must **cite** the implementation… never a silent re-spec.*

### 7.3 The uncomfortable corollary

**Evidence Custody is the chain's strongest link and it is built on its weakest.**

Per **CU-3**, `gate_evidence` immutably records a statistic computed from a partition whose custody state is **unknown**. **The evidence is perfectly preserved. What it is evidence *of* is not established.**

> **This is not a criticism of the gatekeeper — it is the argument for §5.** An immutable record of an unknown quantity is a **precise record of an unknown quantity.** Per §2.4: *"unenforced custody produces a system whose evidential state cannot be known even by its own operators."* **The gatekeeper is the best-built component in the system, and it is currently certifying inputs the institution cannot vouch for.**

---

## 8. Publication Custody — **absent**

### 8.1 What a Publication is

> **A Publication is any assertion that leaves the research boundary.**

Research reports · Knowledge Base records · `wf_edge` · `wf_scores` · promotion reports · dashboard surfaces · the edge registry manifest.

**Per [[01_SCIENTIFIC_FOUNDATION]] §0.1 this is the exact boundary the architecture cares about:** *"research produces knowledge; capital allocation consumes it. The reverse dependency… is prohibited."* **Publication is where that one-directional edge is crossed — and it is currently uncontrolled.**

### 8.2 The five lineages

> **Rule CU-17:** **Every Publication preserves five lineages, and a Publication missing any is not publishable.**
>
> **Evidence** → `decision_id` · **Dataset** → partition ids + fingerprints · **Experiment** → `run_id`, `git_commit`, `seed` · **Version** → the publication's own version + what it supersedes · **Fingerprint** → of the published content itself.
>
> Per §4.3: *"the evidential weight of a result is not recoverable from the result."* **A published number stripped of its lineage is a number whose weight is unknowable — and it is precisely the form in which capital will encounter it.**

### 8.3 The current state: C-DERIVED masquerading as published

Per [[CUSTODY_PROPAGATION_AUDIT]] §2.4: `wf_scores`, `wf_edge`, `backtest_cache` are **`INSERT OR REPLACE` / `UPDATE`**, unfingerprinted, and read by `routes/screener.py`, `screener/brpt_filter.py`, `scheduler/jobs.py`.

> **Rule CU-18:** **A C-DERIVED asset may be overwritten freely — and may never be published.**
>
> The tables are **caches**. Overwriting a cache is correct behaviour and this amendment does not forbid it. **The defect is not the overwrite. It is that a cache is read as a publication.**
>
> **Therefore the resolution is not to make `wf_scores` immutable.** It is to declare it **C-DERIVED**, and to require that anything crossing the research boundary is a **Publication** (C-IMMUTABLE, five lineages, fingerprinted). A Publication may be *materialized from* a cache; it may never *be* one.

> **This is why Publication Custody is a smaller change than it appears.** No table is rewritten. One boundary is drawn, and one object is added at it.

---

## 9. Retention

| Asset | Retention | Basis |
|---|---|---|
| **Custody Events, Receipts** | **Permanent** | **CU-6** — the only record of an invisible fact |
| **Evidence, Gate Decisions** | **Permanent** | C-IMMUTABLE |
| **Failure Records** | **Permanent, never deleted** | **R12**, §4.4 — *"an empty Failure Library silently biases every DSR"* |
| **Lineage** | **Permanent** | **OS-12** |
| **Family declarations** | **Permanent** | **R7.5** — the denominator every successor inherits |
| **Dataset Partitions** | Permanent while any claim depends on them | **R19** — a broken lineage voids the claim |
| **C-DERIVED caches** | **None. Discardable** | Recomputable by definition |
| **Superseded versions** | **Permanent** | **R12** — a mutable object is a suppressible object |

> **Rule CU-19:** **C-DERIVED is the only class with no retention requirement, and that is what makes the class worth having.** Without it, "never delete anything" becomes unaffordable and will be violated selectively — and a selectively-violated retention rule is worse than a scoped one, because nobody knows which parts held.

---

## 10. Traceability

| This document | Extends | **Never restates** |
|---|---|---|
| §0.1 why custody exists | **[[01_SCIENTIFIC_FOUNDATION]] §2.4, R6** | **§2.4 and R6 — the five "why" bullets live there** |
| §0.3 two axes | §2.4 (three epistemic states, **closed**) | The three states |
| §1 custody is a history | **R6** (*"leaving its appearance unchanged"*) | R6 |
| §3 the nine-attribute facet | [[RESEARCH_OBJECT_SCHEMA]] §1 (nine facets) | The facet list |
| §4 asset state machine | — (**new axis**; subordinate to §2.4 via CU-1) | — |
| §4.3 illegal transitions | [[HYPOTHESIS_LIFECYCLE]] §5's discipline; R7.4, R15, R19 | X1–X10 |
| §5 Dataset Custody | **R6** (non-renewable), §4.2 (E7) | R6 |
| §6 Experiment Custody | `gate_decisions` (**cited, not re-spec'd**) | The schema |
| **§7 Evidence Custody** | **`gate_evidence` — formalized only** | **The implementation** |
| §8 Publication Custody | §0.1 (the research/capital boundary), §4.3 | §0.1 |
| CU-7 (not audit_events) | `security/audit_trail.py` | — |

**Amends:** [[RESEARCH_OBJECT_MODEL]] v2.0 (§3's facet + 3 objects) · [[RESEARCH_VALIDATION_FRAMEWORK]] v1.1.
**Consumed by:** [[EXPERIMENT_STANDARD]] §3 · [[EVIDENCE_MODEL]] · [[RESEARCH_OBJECT_SCHEMA]] · [[HYPOTHESIS_LIFECYCLE]] T5.
**Delivery:** [[CUSTODY_AMENDMENT]] — propagation matrix, backward compatibility, migration, RFCs, freeze readiness.
