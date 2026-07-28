# Research Object Model

**Version:** 2.0 · **Status:** Canonical · **Canonical Status:** Permanent repository document · **Layer:** L2 — Research Architecture
**Owner:** Research Architect · **Last Updated:** 2026-07-15 · **Supersedes:** v1.0 (2026-07-15) — **amended by [[DECISION_LOG]] D-022 to make Custody foundational.** v1.0's objects and fields are **unchanged and backward-compatible**; §3 and §4 are additive.
**Realized in v3:** `research/knowledge` (hypotheses, `hypothesis_links`, receipt-bound `set_status`) · `research/regime` (`regime_profiles`) · edge registry ([[RESEARCH_OS_RECONCILIATION]] §4) · **`gate_decisions` + `gate_evidence` (append-only) realize the custody facet for Evidence and Gate Decision today** ([[CUSTODY_MODEL]] §7)
**Scientific basis:** [[01_SCIENTIFIC_FOUNDATION]] §3 (world ontology — distinct from this artifact ontology), §5.2 (hypothesis admissibility), **§2.4 + R6 (custody states; custody must be enforced, not requested)**

## 1. Definition
The Research Object Model establishes the strict schemas for all scientific entities within the institution.

**Every object in this model is a research asset, and every research asset has custody.** Custody is **not an extension, not a module, and not optional** — it is a mandatory facet of object identity, defined once in [[CUSTODY_MODEL]] and declared here per object (§3, §4). An object without a declared custody class is not specified.

## 2. Core Objects

### Research Hypothesis Object
- **hypothesis_id**: Unique UUID for the hypothesis.
- **mechanism**: The structural or behavioral market inefficiency being investigated.
- **economic_rationale**: Theoretical explanation of why the inefficiency exists and persists.
- **prediction**: The expected empirical observation if the mechanism is active.
- **null_hypothesis**: The baseline state if the market is perfectly efficient with respect to the mechanism.
- **alternative_hypothesis**: The statistically measurable deviation from efficiency.
- **required_data**: Array of dataset references (e.g., Daily OHLCV, Intraday Signed Flow, Broker Summary, Trade Prints). Dataset authority is [[DATA_FEASIBILITY_STUDY]] §4 — the binding scope constraint; `required_data` must resolve to capabilities classified there as *Available Today* or *Obtainable Later*.
- **validation_criteria**: Pre-registered thresholds for significance and effect size.
- **status**: Current state (e.g., REGISTERED, IN_TESTING, VALIDATED, FAILED).

### Literature Card
- **card_id**: Unique identifier.
- **source**: DOI, ArXiv ID, or Journal citation.
- **identified_mechanisms**: List of mechanisms proposed by the authors.
- **empirical_claims**: Specific data-backed claims to be reproduced.
- **limitations**: Boundary conditions of the paper's findings.

### Economic Mechanism
- **mechanism_id**: Unique identifier.
- **classification**: Taxonomy category (e.g., Inventory Risk, Asymmetric Information, Liquidity/Price-Impact Compensation). The taxonomy is [[01_SCIENTIFIC_FOUNDATION]] §3.4 (classes M1–M6).
- **causal_graph**: DAG representing the interaction of market participants.
- **half_life_estimate**: Theoretical duration of the inefficiency before arbitrage correction.

### Dataset Object
- **dataset_id**: Unique identifier.
- **asset_class**: Target universe.
- **resolution**: Granularity (e.g., Daily bar, 1-minute bar, Tick). Attainable resolutions are enumerated in [[DATA_FEASIBILITY_STUDY]] §3–§4.
- **regime_classification**: Market conditions during the sample period.
- **provenance_hash**: Cryptographic hash of the raw data files for reproducibility.

### Experiment Object
- **experiment_id**: Unique identifier.
- **hypothesis_ref**: Link to the target Hypothesis Object.
- **feature_set_ref**: Link to the specific version of the Feature Computation Graph used.
- **in_sample_period**: Dates used for parameter calibration.
- **out_of_sample_period**: Dates used for validation.
- **methodology**: Statistical procedures utilized.

### Feature Definition
- **feature_id**: Unique identifier.
- **mathematical_formulation**: LaTeX representation of the feature.
- **code_reference**: Pointer to the implemented logic in the repository.
- **dependencies**: Upstream features or raw data elements.

### Validation Report
- **report_id**: Unique identifier.
- **experiment_ref**: Link to the evaluated experiment.
- **statistical_metrics**: Output of PBO, Deflated Sharpe, etc.
- **reviewer_notes**: Qualitative assessment by the Validation Reviewer.
- **decision**: Pass/Fail outcome.

### Failure Library Entry
- **failure_id**: Unique identifier.
- **hypothesis_ref**: Link to the failed hypothesis.
- **falsification_reason**: Primary driver of failure (e.g., Data Mining, Regime Shift, Transaction Costs).
- **lessons_learned**: Institutional insight gained.

### Accepted Knowledge Object
- **knowledge_id**: Unique identifier.
- **mechanism_ref**: Link to the underlying mechanism.
- **validation_ref**: Link to the passing validation report.
- **decay_monitor_id**: Link to the live process tracking the ongoing validity of the mechanism.

---

## 3. Custody (amendment — D-022)

**Authority:** [[CUSTODY_MODEL]] is the **single canonical definition of Custody**. This section declares custody *within the object model*; it does not define it. The epistemological ground is [[01_SCIENTIFIC_FOUNDATION]] **§2.4 and R6** — not restated here or there.

### 3.1 Custody is a mandatory facet

> Every object above and in §4 declares a **custody class** ([[CUSTODY_MODEL]] §3.1) and carries the **nine-attribute custody facet** ([[CUSTODY_MODEL]] §3): identity · ownership · custody · lineage · lifecycle · fingerprint · superseding rules · audit requirements · retention.

**Custody is a history, not an attribute** ([[CUSTODY_MODEL]] §1) — because per **R6** a contaminated out-of-sample partition and a clean one are *bit-identical*, and *"every unlogged glance silently converts it into in-sample data while leaving its appearance unchanged."* An object therefore does not *hold* its custody state; the **Custody Event log** holds it.

### 3.2 Custody class per object

| Object | Custody class | Note |
|---|---|---|
| Literature Card | **C-IMMUTABLE** | A fact about what was known when |
| Economic Mechanism | **C-FROZEN-ON-USE** | Frozen on first reference by a Hypothesis; `authored_at`/`blind_to` (§7.3) |
| Research Hypothesis | **C-FROZEN-ON-USE** | Frozen at G1 — a one-way door (HL-2) |
| Dataset | **C-FROZEN-ON-USE** | Frozen on fingerprint |
| **Dataset Partition** *(§4.1)* | **C-FROZEN-ON-USE**, or **C-SEALED** for OOS/Blind | **The only assets that meter access** |
| Feature Definition | **C-FROZEN-ON-USE** | Branch-on-upstream-change |
| **Candidate** *(§4.2)* | **C-IMMUTABLE** | `candidate_hash` — realized in `gatekeeper/candidate.py` |
| Experiment | **C-IMMUTABLE** | Immutable on execution; a re-run is a new experiment |
| **Evidence** *(§4.3)* | **C-IMMUTABLE** | **Realized: `gate_evidence`, append-only** ✅ |
| Gate Decision *(≈ Validation Report)* | **C-IMMUTABLE** | **Realized: `gate_decisions`, append-only** ✅ |
| **Publication** *(§4.4)* | **C-IMMUTABLE** | **Absent — the boundary to capital** |
| Accepted Knowledge Object | **C-IMMUTABLE** | Status transitions are receipt-bound (R-10) |
| Failure Library Entry | **C-IMMUTABLE** | **Never superseded, never deleted** (R12) |
| Lineage Edge | **C-APPEND-ONLY** | **Realized: `hypothesis_links`** ✅ |
| **Custody Event / Receipt** *(§4.5)* | **C-IMMUTABLE, append-only** | The log itself |
| `wf_scores` · `wf_edge` · `backtest_cache` | **C-DERIVED** | **Caches. Freely overwritable. NEVER publishable** ([[CUSTODY_MODEL]] §8.3) |

> **Rule ROM-1 (justified by CU-8, OS-5/R6):** An object with no declared custody class defaults to **C-IMMUTABLE** — the safe direction. An undeclared class is a rule enforced by nobody.

---

## 4. Objects introduced by the Custody amendment (D-022)

**Four additions. Each closes a gap that made custody unmodellable; none alters an existing object.**

### 4.1 Dataset Partition Object
**Why it exists:** a partition is **not** an attribute of a Dataset ([[CUSTODY_MODEL]] §5.2). It has its own state, its own access history, and its own fingerprint. A Dataset is Locked while its train partition is Consumed a hundred times and its OOS partition is Released once — **one object cannot hold four states.**
- **partition_id** · **dataset_ref** → Dataset · **kind**: Train | Validation | Test | **Out-of-Sample** | **Blind**
- **scheme_ref**: the split rule, declared **ex ante** (re-partitioning after results is CU-X5)
- **fingerprint**: its own, distinct from the parent Dataset's
- **custody_class**: C-FROZEN-ON-USE, or **C-SEALED** for Out-of-Sample and Blind
- **release_date**: Blind partitions only — before it, releasable by **nobody, including the CRO** (CU-13)
- **receipt_chain**: append-only; **`ordinal` must be 1 for a C-SEALED release** (CU-5)

### 4.2 Candidate Object
**Why it exists:** `candidate_hash` is already computed and persisted (`gatekeeper/candidate.py:40`, `gate_decisions.candidate_hash`) — **the object exists in code and was never in the model.** This declares what is already built.
- **candidate_id** · **candidate_hash** · **strategy_fn** · **hypothesis_ref** → Hypothesis
- **trades / scan_family / wf / oos summaries** · **partition_refs[]** → Dataset Partition

### 4.3 Evidence Object
**Why it exists:** evidence was implicit inside the Validation Report. **It is already a separate, append-only table** (`gate_evidence`) and is the institution's strongest custody surface ([[CUSTODY_MODEL]] §7).
- **evidence_id** · **decision_ref** → Gate Decision · **stage** · **verdict** · **statistic_json**
- **Custody: C-IMMUTABLE.** No UPDATE, no DELETE. **A re-run mints a new `decision_id`** — Evidence v2, never an overwrite (CU-9).
- **Realized in v3 exactly as specified. This model changes no column.**

### 4.4 Publication Object
**Why it exists:** *"A Publication is any assertion that leaves the research boundary"* ([[CUSTODY_MODEL]] §8.1) — the boundary [[01_SCIENTIFIC_FOUNDATION]] §0.1 makes one-directional (*research produces knowledge; capital consumes it*). **It is currently uncontrolled.**
- **publication_id** · **content_fingerprint** · **supersedes** → Publication
- **The five lineages, all mandatory** (CU-17): **evidence_ref** → Gate Decision · **dataset_lineage[]** → Dataset Partition · **experiment_lineage** (run_id, git_commit, seed) · **version_lineage** · **fingerprint_lineage**
- **Custody: C-IMMUTABLE.** A Publication may be *materialized from* a C-DERIVED cache; **it may never be one** (CU-18).

### 4.5 Custody Event & Custody Receipt Objects
Defined in full at [[CUSTODY_MODEL]] §2.2–§2.3. Declared here as first-class objects of this model.
- **Custody Receipt** — that an access **occurred**: `asset_ref` · `accessor` · `purpose_ref` · `ordinal` · `prior_receipt`
- **Custody Event** — the append-only record of a §4 state transition: `from_state` → `to_state` · `fingerprint_before/after` · `receipt_ref`
- **Neither is `audit_events`** (`security/audit_trail.py`), which is RBAC/security and must not be conscripted (CU-7).

---

## 5. Backward compatibility (D-022)

**v1.0's eight objects are unchanged.** No field renamed, removed, or re-typed. §3 adds a declaration; §4 adds four objects. Every v1.0 consumer remains valid.

**Already-conformant in v3, requiring no change:** `gate_evidence` · `gate_decisions` · `hypothesis_links` · `failure_registry` · `regime_profiles` · `research_runs` · `research/knowledge` storage. See [[CUSTODY_AMENDMENT]] §9.
