# Custody Propagation Audit

**Version:** 1.0 · **Status:** Audit record (pre-freeze gate) · **Layer:** L0 — Governance & Scope
**Owner:** Research Program Director · **Date:** 2026-07-15 · **Supersedes:** — (initial version)
**Trigger:** Owner-requested pre-commit audit. *"Apakah G-9 (Dataset/OOS Custody) sudah sepenuhnya terpropagasi ke seluruh dokumen?"* — asked before freezing the corpus as a permanent baseline.
**Method:** Mechanical search of the canonical corpus **and the v3 implementation**, at HEAD `62d68ef` + uncommitted working tree. Four of the nine layers named by the owner (Gatekeeper, Knowledge Base, Audit Trail, Lineage) are **code, not documents** — this audit crosses into the implementation rather than stopping at the corpus.
**Authority:** An audit record. **It creates no rules and amends nothing.**

---

## 1. Verdict

> ## ❌ NO — custody is not propagated. It is not a concept this system has.

**The word `custody` appears zero times in the entire codebase.** Not in the gatekeeper, not in the knowledge base, not in tracking, not in lineage, not in the audit trail. Verified:

```
$ grep -rniE "\bcustody\b" --include="*.py" . | wc -l
0
```

In the canonical corpus it is absent from **five of the nine** named layers, and present **only in the four documents authored in the last two sessions**:

| Layer | Custody mentions | Verdict |
|---|---:|---|
| **Research Object Model** (canonical L2) | **0** | ❌ **The object model has no custody concept** |
| **Research Validation Framework** (= Gatekeeper spec) | **0** | ❌ |
| **Market Inefficiency Research Pipeline** (S1–S10) | **0** | ❌ |
| **Failure Library Schema** | **0** | ❌ |
| **Research Operating Model** | 1 | ⚠️ §7 pipeline mention only; no rule |
| Research Object Schema *(new)* | 15 | ✅ |
| Experiment Standard *(new)* | 11 | ✅ |
| Hypothesis Lifecycle *(new)* | 8 | ✅ |
| Evidence Model *(new)* | 7 | ✅ |
| **All v3 code** | **0** | ❌ |

> **The finding, stated plainly: custody is a vocabulary the new procedural layer invented for a rule L1 has asserted since §2.4 — and which the canonical L2 corpus and the entire running system have never heard of.** The four documents that use the word are the four I wrote. **G-9 is not a gap in enforcement. It is a gap in the concept ever having been introduced.**

**The owner's instinct to audit before freezing was correct.** Freezing now would have made "custody" a term of art that exists in four documents, contradicts nothing because nothing else mentions it, and enforces nothing because no code knows it.

---

## 2. What the owner asked for: the four-stage chain

> Dataset Custody → Experiment Custody → Evidence Custody → Publication Custody

**This chain does not exist as a concept. But three of its four stages exist as unnamed, partially-built mechanisms — and one of them is already correct.** Audited stage by stage:

### 2.1 Dataset Custody — ❌ **ABSENT**

| Question | Finding |
|---|---|
| Is there an in-sample/out-of-sample partition? | **Only as a computation.** `research/walkforward_multi.py:129` `walk_forward_split()` returns `{'train','test',...}` dicts |
| Is there any access control on the test partition? | **None.** It is a function that returns a dataframe. Anyone may call it and read `['test']` |
| Is there a custody receipt (who opened, when, once)? | **None.** The concept does not exist |
| Does anything detect a spent window? | **No** |

> **`walk_forward_split` is a computation, not a control.** Per **R6**: *"a prohibition that relies on a researcher's discipline is a statement of intent, not a control."* There is no control. **G-9 confirmed at the strongest possible level: not weakly enforced — absent.**

### 2.2 Experiment Custody — ⚠️ **PARTIAL, and better than expected**

`research/gatekeeper/storage.py` — `gate_decisions`, **append-only by rule, no UPDATE, no DELETE**:

```
decision_id · run_id · strategy_fn · candidate_hash · config_hash
dataset_fingerprint · git_commit · seed · final_state · failing_stage
forward_test_rule · summary_json · decided_at
```

**This is Experiment Custody, unnamed, and most of it is right.** `candidate_hash` + `config_hash` + `dataset_fingerprint` + `git_commit` + `seed`, append-only, one decision_id per evaluation, *"a superseding evaluation is a new decision_id"* — **that is precisely OS-4/EX-7 (a re-run is a new family member, never an overwrite), already implemented.**

**What is missing:** the custody receipt. Nothing records **who opened the OOS window, when, and that it was opened once.** The provenance is complete about *the data*; it is silent about *the access*.

### 2.3 Evidence Custody — ✅ **ALREADY BUILT, and it already does what the owner asked**

`research/gatekeeper/storage.py` — `gate_evidence`, **append-only**:

```
evidence_id · decision_id · stage · verdict · statistic_json · ...
    "one row per stage per decision (the 'why')"
    "Append-only by rule: no UPDATE, no DELETE."
```

> **The owner's requirement — *"tidak boleh hasil bootstrap diubah setelah gate; kalau ada rerun, harus Evidence v2, bukan overwrite"* — is already satisfied inside the gatekeeper.** `statistic_json` holds the stage statistics; the table takes no UPDATE and no DELETE; a re-run mints a new `decision_id` with a new evidence set. **Evidence v2, not overwrite. Built. Working. Never called custody.**

**This is the audit's most useful finding and it inverts the expected conclusion:** Evidence Custody is the **strongest** link in the chain, not a gap. It needs to be **named and bound**, not invented.

### 2.4 Publication Custody — ❌ **ABSENT, and nobody has named the concept**

| Question | Finding |
|---|---|
| Is "published" distinguished from "computed"? | **No** |
| What does production read? | `wf_scores`, `wf_edge` via `routes/screener.py`, `screener/brpt_filter.py`, `scheduler/jobs.py` |
| Are those tables immutable? | **No — `INSERT OR REPLACE` and `UPDATE`** (`research/jobs.py:129`, `:135`) |
| Is there a fingerprint over them? | **No** |

**`security/audit_trail.py` exists** (`audit_events`, INSERT-only) but it is **RBAC/security audit — actor_role, actor_fingerprint, action.** It records *who called an endpoint*. It has nothing to do with research custody and should not be conscripted into it.

---

## 3. The mutability map

**Two populations, and the split is generational rather than principled.**

| ✅ Append-only (declared in code) | ❌ Mutable |
|---|---|
| `research_runs` (ledger) | `backtest_cache` — `INSERT OR REPLACE` |
| `hypotheses` — *"append-only EXCEPT status"* | `wf_scores` — `INSERT OR REPLACE` |
| `hypothesis_links` (**lineage** ✅) | `wf_edge` — `UPDATE ... SET run_id` |
| `failure_registry` ✅ | `backtest_windows` — `INSERT OR REPLACE` |
| `regime_profiles` ✅ | `optimizer_results` — upsert |
| `gate_decisions` ✅ | `fastmover_patterns` — `INSERT OR REPLACE` |
| `gate_evidence` ✅ | |

> **The newer research surface (gatekeeper, knowledge, regime, tracking) is append-only and provenance-carrying. The older surface (jobs, optimizer, backtest_cache, wf_scores) overwrites in place.** Nothing names the difference, nothing enforces it, and **nothing prevents a new table from being written in either style.** Per **OS-3**, append-only is a *scientific* requirement (**R12** — a mutable object is a suppressible object); here it is a **coding convention that happened to be adopted twice.**

### 3.1 `dataset_fingerprint` pins less than its name claims

`research/tracking.py:70–95` hashes:
- `ohlcv` — `WHERE COALESCE(is_final,1)=1`, grouped by ticker: `COUNT(*), MIN(date), MAX(date), SUM(CAST(close AS INTEGER)), SUM(CAST(volume AS INTEGER))`
- `corporate_actions` — count, max date, summed value

**It does not cover any derived table.** Not `backtest_cache`, not `wf_scores`, not `wf_edge`, not `optimizer_results`.

> **So `dataset_fingerprint` names the raw corpus, and only the raw corpus.** For the **gatekeeper this is sound** — it recomputes trades from `ohlcv` via `load_ohlcv_df` (`candidate.py:139–147`), so the raw fingerprint genuinely pins its inputs. **For anything consuming `wf_scores` or `backtest_cache`, the fingerprint pins something the consumer never read.**

**Secondary observation (low severity, worth recording):** the per-ticker digest uses `SUM(CAST(close AS INTEGER))`. Truncation is likely lossless on IDX's integer tick prices, but a **sum is order-insensitive and collision-permissive** — offsetting errors on two days produce an identical digest. For a control whose purpose is *detecting that data changed*, a sum is a weak instrument. Not urgent; not free either.

---

## 4. What is actually sound — stated because an audit that only alarms is not an audit

**The gatekeeper path is clean and the owner should know it.**

```
load_ohlcv_df(ohlcv)  →  recompute trades  →  candidate_hash
                                            →  config_hash
                                            →  dataset_fingerprint(ohlcv + corp_actions)
                                            →  git_commit, seed
                                            →  gate_decisions   (append-only)
                                            →  gate_evidence    (append-only, statistic_json)
```

It recomputes from raw data rather than trusting a mutable cache; it fingerprints what it actually read; it records the commit and the seed; it writes evidence append-only; a re-run is a new decision, never an overwrite. **Per the corpus's own rules that is OS-2, OS-3, OS-4, and EX-7 satisfied — in the one place where a claim is actually adjudicated.**

**`hypothesis_links` (lineage) is append-only** — **OS-12** satisfied. **`failure_registry` is append-only** — **R12/OS-7** satisfied. **`research/knowledge/storage.py:111`** names its single mutation explicitly (*"the one sanctioned mutation… update a hypothesis's label"*) rather than leaving it implicit — which is the correct way to hold an exception.

> **The system is not undisciplined. It is disciplined in the places someone thought about, and silent everywhere else — and it has no word for what the discipline is.** That is exactly what a missing concept looks like from the inside.

---

## 5. Answering the owner's nine layers

| # | Layer | Custody present? | Detail |
|---|---|---|---|
| 1 | **Research Object Model** | ❌ **0 mentions** | The canonical object model has no custody, no immutability, no lifecycle. **Its Dataset Object has `provenance_hash` and no partition** |
| 2 | **Dataset Model** | ❌ | Exists only as O4 in `RESEARCH_OBJECT_SCHEMA` (new, **PROPOSED-adjacent**), with `custody_partition`. **ROM's Dataset Object does not have it** |
| 3 | **Experiment Standard** | ✅ 11 | §3 specifies the one-shot rule + receipt. **§3.2 and G-9 admit it is procedure, not mechanism** |
| 4 | **Evidence Model** | ⚠️ 7 | Custody appears in the E-tier rules; **the X-axis and DG9 reference it. But there is no Evidence Custody concept** — evidence immutability is nowhere in the document |
| 5 | **Gatekeeper** | ❌ **0 in code** | **The mechanism is right; the vocabulary is absent.** `gate_evidence` is Evidence Custody with no name |
| 6 | **Research OS** (corpus) | ⚠️ | 4 of 13 L2 docs. **The four I wrote** |
| 7 | **Research Knowledge Base** | ❌ **0 in code** | `hypotheses` append-only except status; **no custody state on any object** |
| 8 | **Audit Trail** | ❌ | `audit_events` is **RBAC/security**, not research. Wrong instrument — do not conscript it |
| 9 | **Lineage** | ⚠️ | `hypothesis_links` **is** append-only ✅ — but it links hypotheses to sources. **It does not record custody events**, because there are none to record |

---

## 6. Consequence for the owner's proposed priority change

> **Proposed:** P0 = G-9 Dataset Custody · P1 = G-4 Peer Review · P2 = remaining governance.
> **Rationale:** *"Peer Review tidak ada artinya kalau dataset sudah bocor."*

> ## ✅ The audit supports this, and supplies the argument the corpus already contains.

**The rationale is not merely pragmatic — it is [[01_SCIENTIFIC_FOUNDATION]] §2.4 restated:**

> *"unenforced custody produces a system whose evidential state cannot be known **even by its own operators**."*

A peer reviewer's mandate (**PV-2**) is to attempt refutation. **A reviewer cannot attack a claim whose custody state is unknowable** — they cannot determine whether the out-of-sample result they are reviewing was out-of-sample. Per **§8.2**, a claim that cannot be attacked has *structural immunity from criticism*, and per **P3** that is **not a knowledge claim.**

> **So G-4 is not merely less urgent than G-9. G-4 is partially void until G-9 is closed.** Hiring a second researcher to review claims whose evidential state cannot be determined buys the *appearance* of independent review over an *unknowable* substrate. Per **LIM8** that appearance is indistinguishable from the real thing — which makes it worse than no review, because it would be recorded as a review.

**The ordering is correct and the audit strengthens it: G-9 before G-4 is not a preference about sequencing. It is a precondition for G-4 to mean anything.**

### 6.1 One refinement the audit suggests

**The chain's stages are not equally missing, so a flat "custody" P0 would mis-target effort:**

| Stage | State | Work |
|---|---|---|
| **Dataset Custody** | ❌ **absent** | **The real P0.** Partition + access control + receipt |
| **Experiment Custody** | ⚠️ partial | Add the receipt to an otherwise-correct `gate_decisions` |
| **Evidence Custody** | ✅ **built** | **Name it. Bind it. Do not rebuild it** |
| **Publication Custody** | ❌ absent | The `wf_scores`/`wf_edge` surface |

> **The owner's P0 instinct lands on precisely the stage that is absent.** Evidence Custody — the concept that prompted this audit — turns out to be the one already working.

---

## 7. Recommendation

**Do not freeze. Do not commit.** The audit's own finding is that the corpus would freeze a term of art that four documents use, nine layers do not know, and no code enforces.

**Proposed sequence — owner decision required:**

1. **Author a `CUSTODY_MODEL.md` (L1)** defining the four-stage chain as one concept with one vocabulary. It must **name and bind `gate_evidence` and `gate_decisions` as existing realizations** (per [[RESEARCH_OS_RECONCILIATION]] §4: *cite the implementation; never re-spec it*) rather than inventing a parallel design. **Evidence Custody is a naming exercise; Dataset Custody is a design exercise.**
2. **Propagate** into the five layers with zero mentions — which per **D-020** means **ROM and the Validation Framework require amendments this session has withheld authority for.** That is now unavoidable: **custody cannot be a strict extension, because there is nothing upstream to extend.**
3. **Re-run this audit.** It is mechanical and cheap.
4. **Then** freeze and commit.

> **Note for step 2 — the honest complication.** D-020/D-021 held because every gap was an *absence* that could be filled downstream without touching a certified document. **Custody breaks that pattern.** A custody concept that lives only in the procedural layer while ROM's Dataset Object has no partition is not an extension — it is a **second authority**, which is the AQ-1 defect the corpus closed at `de98c17`. **Custody must go into L1 and ROM, or it must not go in at all.**

---

## 8. Evidence index

| Claim | Command / location |
|---|---|
| `custody` = 0 in code | `grep -rniE "\bcustody\b" --include="*.py" .` → 0 |
| ROM has no custody | `grep -ci custody docs/research_os/RESEARCH_OBJECT_MODEL.md` → 0 |
| `gate_evidence` append-only | `research/gatekeeper/storage.py:1–9`, `GATE_EVIDENCE_DDL` |
| Evidence v2 not overwrite | `storage.py:7` — *"A superseding evaluation is a new decision_id"* |
| Mutable tables | `research/jobs.py:129,135`; `optimizer.py:289`; `backtest_roller.py:105,204` |
| Fingerprint scope | `research/tracking.py:70–95` — `ohlcv` + `corporate_actions` only |
| Gatekeeper reads raw | `research/gatekeeper/candidate.py:139–147` → `load_ohlcv_df` |
| No OOS access control | `research/walkforward_multi.py:129` — a split function |
| `audit_events` is RBAC | `security/audit_trail.py:3–26` |
| Lineage append-only | `research/knowledge/storage.py:2`; `trace.py:2` |
