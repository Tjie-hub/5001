# ARB Adjudication — Red-Team Findings RT-1…RT-5

**Version:** 1.0 · **Status:** Adjudication record · **Date:** 2026-07-15 · **Layer:** L0
**Board:** Claude (Opus 4.8) — **the author of the architecture AND the author of the red-team review under adjudication.** See §0. This disqualifies exactly one half of this document's output.
**Method:** Per the ARB brief — restate · quote exactly · **falsify first** · then prove · classify. Corpus-only. **No fixes proposed. No documents amended.**

---

## 0. The Board's standing — and why this document's verdicts are asymmetrically trustworthy

**I authored the architecture. I authored the red-team review. I am now adjudicating it. All three are one mind.**

Per **LIM6** — *"adversarial review is structurally compromised at this scale"* — and **LIM8** — *"self-certification is epistemically indistinguishable from genuine certification"* — this is the exact configuration **D-019** rejected.

**But the two verdict types are not symmetric, and the asymmetry inverts from the red-team review:**

| Verdict | Epistemic force from this Board |
|---|---|
| **UPHOLD** a finding | **Valid.** It is a refutation of the architecture — deductive, accepted on first competent demonstration (§2.2) |
| **REJECT / DOWNGRADE** a finding | **STRUCTURALLY SUSPECT.** It is a *clearance*, and per **LIM8** a clearance from the author is indistinguishable from a motivated one |

> **This Board rejects or downgrades four of five findings. That is the single most suspicious outcome this exercise could have produced, and I am stating it before the verdicts rather than after.** An author who red-teams himself and then overturns 80% of his own findings has produced exactly the artifact **LIM8** predicts a motivated author produces.

**The only defense available is that the four rejections are *deductive and mechanically checkable* — quotes and logic, not judgment.** They are. Every one is a `grep` you can re-run.

**But per LIM8 that defense is worth precisely nothing on its own, because it is what an honest Board and a motivated Board both say.**

> **Therefore this document's deliverable is not its verdicts. It is its proof set.** The verdicts are a hypothesis about the proofs. **The External Validation Reviewer (D-019) must check the four rejections; they may accept the one uphold without me.**

---

## 1. RT-1 · Custody has no trust anchor

### Step 1 — Restatement
CU-2 proves custody cannot be an attribute because tampering leaves the asset bit-identical. Applied to the Custody Event log — itself an asset — the same proof yields an infinite regress the architecture terminates nowhere. `grep CREATE TRIGGER` → zero. Append-only is a docstring. **Claimed P0: the architecture's central argument refutes the architecture.**

### Step 2 — Canonical text

> **[[CUSTODY_MODEL]] CU-2:** *"Custody is a history, not an attribute, because the thing it must detect leaves no trace in the asset… A contaminated out-of-sample partition and a clean one are **bit-identical**."*

> **[[CUSTODY_MODEL]] CU-6:** *"Custody Events are append-only and are never deleted… A deleted custody event does not weaken a claim; it makes the claim's evidential state unknowable — which per R19/EV-6 is X0: void."*

> **[[01_SCIENTIFIC_FOUNDATION]] R6:** *"A prohibition that relies on a researcher's discipline is a statement of intent, not a control."*

### Step 3 — Falsification

**Falsifier A — a regress is a universal property of integrity systems, not a defect of this one.** Every integrity system terminates its regress at a root of trust: TLS at a CA, git at a signed ref, a WORM store at hardware. **"There is a regress" is not a finding; it is a description of what an integrity system is.** A ruler does not require a ruler. **The red-team's step 4 — *"by CU-2's own reasoning, the log requires a custody log"* — proves too much: it would invalidate every integrity architecture ever built.**

**Falsifier B — the architecture nowhere claims the log is trusted.** CU-6 states a *rule* and a *consequence*. It does not assert enforcement. Per **R6**, an architecture that states requirements without mechanisms is **an architecture doing its job**. Requirements are architecture; enforcement is mechanism. **This is G-9's category, already recorded as BLOCKING.**

**Falsifier C — RT-1 is largely a restatement of G-9.** G-9: *custody is policy, not mechanism.* RT-1: *the custody log is policy, not mechanism.* **Same class, one level up. Not a new contradiction.**

### Step 4 — Proof

**Residue A survives — and it is real.** [[CUSTODY_AMENDMENT]] §5 defect 2 claims: *"CU-5: `ordinal > 1` is a breach **detectable** only because the receipt exists."* **Against a *careless* researcher, true. Against a *malicious* one who deletes the receipt, false.** The architecture **nowhere declares which threat model custody addresses.**

**This matters because L1 §9 makes assumption-declaration an architectural obligation:**

> *"This section exists because an assumption that is not written down cannot be revisited — it is simply how everyone thinks."*

**The custody model rests on "the log is not adversarially tampered with." That assumption is load-bearing, undeclared, and has no A-number.** A1–A8 exist precisely to prevent this.

### Step 5 — Determination

> ## PARTIALLY VALID · **MISCLASSIFIED P0 → P2** (+ an undeclared-assumption gap)

| | |
|---|---|
| **Is there an integrity root?** | **No — and none is specified.** Fact confirmed |
| **Is append-only + receipt chaining sufficient?** | **No.** A hash chain is tamper-evident only if its head is anchored outside the mutable store. `prior_receipt` exists; **the anchor does not** |
| **Is an explicit anchor *required by the architecture*?** | **Not currently — and that is the gap.** No canonical text requires it. The requirement should exist |
| **Architecture / Mechanism / Operational?** | **Mechanism (P2)** for the anchor itself — it is RFC-1's substrate. **Architecture** for the *undeclared threat model*, which L1 §9 obliges the corpus to declare |

**Why not P0:** a regress is universal; terminating it is engineering. The architecture contains **no self-contradiction** — it never claims the log is trusted. **The red-team's "the architecture's central argument refutes the architecture" is rhetoric, not proof.**

**Freeze impact: DOES NOT BLOCK** as architecture. The **§5 defect-2 overclaim** ("detectable") is a documentation-correctness issue that a future reader could reasonably misread — **that** is worth correcting, but it is not an architectural contradiction.

---

## 2. RT-2 · Custody is blind to multiplicity

### Step 1 — Restatement
Custody records *access*; multiplicity is generated by *search*. One train-partition receipt + 10,000 in-memory regressions + 1 registered hypothesis = family N=1. Formally: §4.3 (weight = f(process)) + LIM3 (denominator unknowable) ⟹ evidential weight permanently unknowable — **contradicting the architecture's promise that closing G-9 makes evidential state knowable. Claimed P0.**

### Step 2 — Canonical text

> **[[CUSTODY_MODEL]] CU-3:** *"Evidence Custody over an experiment whose dataset custody is unknown certifies **an unknown**."*

> **[[CUSTODY_AMENDMENT]] §5, defect 1:** *"**Unknown Evidential State** | 🟡 **Modelled, not eliminated** | … **The unknown becomes visible; it does not become known**"*

> **[[RESEARCH_PROGRAM_STANDARD]] §0.1:** *"**A Research Program is the multiplicity family boundary.**"*

> **[[EVIDENCE_MODEL]] §3.1:** *"per **LIM3** the multiplicity denominator is *estimable, not knowable*, and a posterior conditioned on an unknowable denominator is a number with the appearance of rigor and none of its content."*

### Step 3 — Falsification

**Falsifier A — the accusation is textually contradicted by the accused document.** The red-team charges that [[CUSTODY_AMENDMENT]] §5 promises knowability. **§5 defect 1 says, verbatim: *"The unknown becomes visible; it does not become known."*** And it scores the defect **🟡 Modelled, not eliminated** — **not** 🟢. **The document says the exact opposite of what it is accused of saying.**

**Falsifier B — the "promise" is a logical fallacy by the reviewer.** CU-3 states: *¬custody → certifies an unknown.* The red-team infers: *custody → certifies a known.* **That is denying the antecedent.** CU-3 makes a one-directional claim and asserts **nothing** about sufficiency. **The red-team manufactured the promise it then refuted.**

**Falsifier C — multiplicity has an owner, and it is not Custody.** [[RESEARCH_PROGRAM_STANDARD]] §0.1 assigns the multiplicity family to the **Program object**; **OS-10** makes it append-only; **D-009** defers the *policy* to P1; **PEER_REVIEW_STANDARD §3.3** makes the true-denominator attack a reviewer's job. **Four separate canonical assignments — none to Custody.** The review attributes to Custody a responsibility the corpus assigns elsewhere.

**Falsifier D — LIM3 is honored, not contradicted.** [[EVIDENCE_MODEL]] §3.1 explicitly refuses Bayesian posteriors *because of* LIM3. **The corpus's treatment of multiplicity is consistent throughout.**

### Step 4 — Proof

**The observation is TRUE:** custody instruments the data path; searches happen in memory; a receipt count is not a search count. **Nobody disputes this and no canonical text claims otherwise.**

**Residue:** [[CUSTODY_PROPAGATION_AUDIT]] §6's *"G-4 is partially void until G-9 is closed"* is imprecise — a reviewer can attack mechanism, cost, and multiplicity without custody. **But "partially" is doing the work correctly: only the *custody-dependent* attacks are void.** Not a contradiction.

### Step 5 — Determination

> ## MISCLASSIFIED · **P0 → not a defect.** The observation is a correctly-drawn boundary, misclassified as a contradiction.

| | |
|---|---|
| **Did Custody ever claim to solve multiplicity?** | **No.** No canonical text makes the claim. The review **inferred** it via denying the antecedent |
| **Does the review misattribute responsibilities?** | **YES.** Multiplicity is owned by [[RESEARCH_PROGRAM_STANDARD]] §0.1 + OS-10 + D-009 + PEER_REVIEW_STANDARD §3.3 |
| **Real contradiction, or a boundary?** | **A boundary — between Custody (contamination) and Statistical Validation / Program (multiplicity). Correctly drawn and consistently honored** |

**Freeze impact: DOES NOT BLOCK.** **RT-2 is the architecture working as designed, described as a failure.**

---

## 3. RT-3 · The amendment modified certified architecture

### Step 1 — Restatement
[[CUSTODY_AMENDMENT]] §1.2 refuses to amend L1 because it is under certification, then amends ROM — which is L2, inside Phase A, certified at `de98c17`, and cited by name in the certificate as its own AQ-1 evidence. **Claimed P1.**

### Step 2 — Canonical text

> **[[PHASE_A_FREEZE_CERTIFICATE]] §144 — the re-issue rule:** *"A **v3.0** issues upon recorded sign-off, naming the reviewer, the date, and **the revision frozen**. Until that entry exists, Phase A is **certified-ready but NOT FROZEN**."*

> **[[RESEARCH_OS_MASTER_ROADMAP]] §112:** *"**Phase A is certified-ready but NOT FROZEN.** No document may describe it as frozen until sign-off is recorded and certificate v3.0 issues naming the reviewer, date, and **revision frozen**."*

> **[[TAXONOMY_AND_NAMING_STANDARD]] §39:** *"**L0, L1, L2 together constitute "Phase A"**"*

### Step 3 — Falsification

**Falsifier A — decisive. The certificate does not lock the corpus at `de98c17`.** §144 states that v3.0 will name **"the revision frozen"** — *a future revision, determined at sign-off.* **`de98c17` is the revision *assessed*, not the revision *frozen*. The certificate explicitly anticipates that a different revision will be frozen later.** An unfrozen corpus is by definition amendable. **The red-team read "Revision certified" as a lock; the document's own re-issue rule says it is not.**

**Falsifier B — the finding proves far too much.** If amending Phase A post-`de98c17` were a violation, then **D-020 (7 documents) and D-021 (6 documents) are violations of the same rule** — thirteen additions to L0/L1/L2 scope, none objected to, including by the red-team that authored the objection.

```
$ git status --short docs/ | grep "??" | wc -l
32
```

**Thirty-two untracked documents already sit inside Phase A's scope.** RT-3 either indicts all of them or none. **It indicts none: the corpus is not frozen.**

**Falsifier C — the placement of CUSTODY_MODEL at L2 does not depend on the certification argument.** [[CUSTODY_MODEL]] §0.2 gives **three** reasons; reasons 1 (*L1 already owns the epistemology*) and 2 (*objects are L2 per §0.5*) are **independently sufficient**. **Even if reason 3 collapses, the placement stands.**

### Step 4 — Proof

**The facts are all confirmed.** ROM is L2; L2 is Phase A; the certificate cites ROM as AQ-1 evidence; ROM is now v2.0.

**Residue A — real but small:** [[PHASE_A_REVIEW_PACKAGE]] v1.1 describes a corpus that has since grown. **A reviewer should review what exists at sign-off.** Per §144 that is *already the process* — v3.0 names the revision frozen. **This is normal governance, not a violation.**

**Residue B — the red-team's sharpest point survives, and it lands on the author, not the architecture:** §1.2's stated reason for protecting L1 is unsound, and **the L1-vs-L2 distinction appears in no governance document.** The reason is bad; the conclusion is right for other reasons.

### Step 5 — Determination

> ## PARTIALLY VALID · **MISCLASSIFIED P1 → P3.** A governance-hygiene item, not an architectural contradiction.

| | |
|---|---|
| **Architectural contradiction or governance violation?** | **Neither, strictly.** The architecture is internally consistent. The certificate anticipates a later frozen revision. **At most: a stale review package, resolved by the certificate's own re-issue rule** |
| **Does the architecture change, or the certification status?** | **The certification status — and only its *currency*, not its validity.** `de98c17` remains correctly assessed. Nothing about ROM v2.0 falsifies D-018's finding |

**Freeze impact: DOES NOT BLOCK.** It **informs** the freeze: per §144 the reviewer signs a named revision. **Which revision is a scheduling question, not an architectural one.**

---

## 4. RT-4 · Blind Partition contradicts E7

### Step 1 — Restatement
CU-13 (and CUSTODY_AMENDMENT M5, RFC-8) claim a Blind partition makes E7 available without wall-clock waiting. L1 §4.2 says E7 requires data that did not exist at registration and **cannot be accelerated**. **Claimed P1.**

### Step 2 — Canonical text — quoted in full, as the ARB brief requires

> **[[01_SCIENTIFIC_FOUNDATION]] §4.2, tier table:** *"**E7** | E6 + forward-tested on **data that did not exist at registration** | **Strongest obtainable** | The only evidence immune to every retrospective bias"*

> **[[01_SCIENTIFIC_FOUNDATION]] §4.2, "On E7 and its cost":** *"Forward evidence is the only tier that no retrospective error can contaminate, but it **accrues in wall-clock time and cannot be accelerated**. This creates a real, permanent tension between rigor and timeliness."*

> **[[CUSTODY_MODEL]] CU-13:** *"A Blind partition is C-SEALED with no release path until its declared date… It exists because **E7 — forward evidence on data that did not exist at registration — is the only tier no retrospective error can contaminate**, and **per §4.2** *the timebox is fixed ex ante and never extended.* **A Blind partition makes E7 available without waiting in wall-clock time, and it is the only mechanism that can.**"*

> **[[CUSTODY_AMENDMENT]] §207 (M5):** *"Seal a forward window with a release date (**CU-13**) — **the only mechanism that makes E7 obtainable without waiting in wall-clock time**"*

> **[[CUSTODY_AMENDMENT]] §226 (RFC-8):** *"**Small, cheap, and the only route to E7 without wall-clock waiting**"*

### Step 3 — Falsification

**Falsifier A — is "did not exist" epistemic rather than metaphysical?** If "did not exist *to the researcher*" were meant, a sealed partition would qualify. **Refuted by §4.2's own gloss:** *"accrues in wall-clock time and cannot be accelerated."* **Only metaphysical nonexistence requires waiting.** Epistemic non-access requires a lock, which is instant. **The "cannot be accelerated" clause fixes the reading against the falsifier.**

**Falsifier B — is a Blind partition a *reservation* for not-yet-collected data?** [[CUSTODY_MODEL]] §5.3 is ambiguous. **But under this reading the claim still fails:** you still wait wall-clock time for the data to arrive. **Both readings contradict "without waiting."**

**Falsifier C — is the capital consequence real?** **PARTIALLY REFUTED — and this materially reduces the finding's blast radius.**

> **[[EVIDENCE_MODEL]] §102:** *"**C4** | **Institutional** | C3 + forward evidence on **data that did not exist at registration** | Capital at scale"*

**C4's own definition independently restates the nonexistence requirement.** A Blind partition would be refused at C4's definition even if CU-13 mislabeled it E7. **The corpus has a redundant guard the red-team missed. The "licenses capital at scale" claim is overstated.**

### Step 4 — Proof

**No falsifier survives against the core claim.** The contradiction is **textual, direct, and triplicated**:

- L1: **cannot be accelerated.**
- CU-13 / M5 / RFC-8: **accelerates it.**

**Aggravating and confirmed:** CU-13 **cites §4.2 in the same sentence it contradicts** — quoting the timebox half that supports the point, contradicting the acceleration half that does not.

**Per [[RESEARCH_OS_RECONCILIATION]] §5.4** — *on any conflict about scientific method, the OS wins* — and L1 is the method authority. **Per [[01_SCIENTIFIC_FOUNDATION]] §0.4** — *a rule whose justifying proposition is refuted is void, not grandfathered.* **CU-13 is void as written.**

### Step 5 — Determination

> ## VALID · **P1 UPHELD**

| | |
|---|---|
| **Is the contradiction genuine?** | **YES.** Textual, direct, at three sites, surviving both falsifiers |
| **Terminology, scope, or interpretation?** | **None of the three — a substantive false claim.** Under *both* available readings of "Blind partition," "without waiting in wall-clock time" contradicts §4.2. It is not a naming problem |
| **Blast radius** | **Smaller than reported.** [[EVIDENCE_MODEL]] §102's C4 definition independently requires nonexistence and would refuse the claim. **The "capital at scale" consequence is overstated** |

**Freeze impact: BLOCKS.** A frozen baseline containing a claim that contradicts L1 — which governs — would make the corpus permanently self-inconsistent at its top evidence tier.

---

## 5. RT-5 · SUPERSEDED state cannot be represented

### Step 1 — Restatement
§4.6 says Gate Decision reaches SUPERSEDED; `gate_decisions` has no supersedes field. Two contradictory live decisions can coexist with no adjudication rule. §7.2's *"requires no change"* is false. **Claimed P1.**

### Step 2 — Canonical text

> **[[CUSTODY_MODEL]] §4.2 T-C9:** *"LOCKED / CONSUMED → SUPERSEDED | A new version registered, **with justification** | ✅"*

> **[[CUSTODY_MODEL]] §2.3, Custody Event fields:** *"`from_state` → `to_state` | The transition (§4)"* · *"`justification_ref` | **For SUPERSEDE — what authorized it**"*

> **[[CUSTODY_MODEL]] CU-2:** *"**Custody is a history, not an attribute**… An attribute can be set. A history can only be appended to."*

> **`research/gatekeeper/storage.py`:** `decision_id, run_id, strategy_fn, candidate_hash, config_hash, dataset_fingerprint, git_commit, seed, final_state, failing_stage, forward_test_rule, summary_json, decided_at`

### Step 3 — Falsification

**Falsifier A — DECISIVE. Supersession is held by the Custody Event log, not by the asset.** §2.3 gives Custody Event `from_state` → `to_state` **and `justification_ref` explicitly labelled *"For SUPERSEDE"***. **A Gate Decision moving LOCKED→SUPERSEDED is recorded as a Custody Event with `asset_ref=decision_id`. `gate_decisions` requires no column.**

**Falsifier B — the red-team's proposed fix violates CU-2.** RT-5 §"Minimal amendment" proposes *"one additive column (`supersedes`)"* on `gate_decisions`. **That is putting custody state on the asset as an attribute — precisely what CU-2 forbids**, and for CU-2's stated reason: an attribute can be set; a history can only be appended to. **A `supersedes` column is silently settable. The custody log is not.** **The finding's remedy contradicts the model the finding claims to defend.**

**Falsifier C — therefore §7.2's verdict stands.** *"They require no change"* is **correct**: `gate_evidence` and `gate_decisions` are conformant. **The missing piece is the Custody Event log — which is G-9/M1, already recorded, and is not a change to these tables.**

### Step 4 — Proof

**Residue A survives, and it is genuine:** **no adjudication rule exists for two concurrently unsuperseded decisions over one candidate.** The architecture does not say what happens. **A real gap.**

**Residue B — "is timestamp ordering sufficient?" — NO, and the red-team is right here.** Per **§4.3** evidential weight is not a function of recency. Per **R7.4**, a later decision under a weaker config winning by `ORDER BY decided_at` is **threshold migration executed by a sort order.** **Confirmed.**

**Residue C — today, supersession is unrecordable** because the custody log is unbuilt. **But that is G-9, not an architectural defect.** The architecture represents SUPERSEDED correctly.

### Step 5 — Determination

> ## PARTIALLY VALID · **MISCLASSIFIED P1 → P3**

| | |
|---|---|
| **Does the state machine require an explicit `supersedes` relation?** | **NO — and requiring one would violate CU-2.** The Custody Event log holds it. **The finding's core claim is INVALID and its remedy is self-refuting** |
| **Is timestamp ordering sufficient?** | **NO.** §4.3 + R7.4. **This part of RT-5 is correct** |
| **Can the current implementation satisfy the architecture?** | **YES — once the Custody Event log exists (G-9/M1). No change to `gate_decisions` is needed.** §7.2 stands |

**Residue reclassified: P3 — the absent adjudication rule for concurrent unsuperseded decisions.** Real, minor, not a contradiction.

**Freeze impact: DOES NOT BLOCK.**

---

## 6. Adjudication Matrix

| Finding | Original | Revised | Accepted | Rejected | Deferred | Reason |
|---|---|---|---|---|---|---|
| **RT-1** Trust anchor | **P0** | **P2** | **Partial** | Core | — | Regress is universal to all integrity systems, not a defect. Architecture never claims the log is trusted; stating requirements without mechanisms **is** architecture. **Largely a restatement of G-9.** *Residue accepted: the careless-vs-malicious threat model is load-bearing and undeclared, and L1 §9 obliges declaration* |
| **RT-2** Multiplicity | **P0** | **none** | — | **Full** | — | **§5 says verbatim *"The unknown becomes visible; it does not become known"*** — the opposite of the accusation. The "promise" was manufactured by **denying the antecedent** on CU-3. Multiplicity is owned by [[RESEARCH_PROGRAM_STANDARD]] §0.1 + OS-10 + D-009 + PV §3.3. **A correctly-drawn boundary described as a failure** |
| **RT-3** Certified corpus | **P1** | **P3** | **Partial** | Core | — | **Certificate §144: v3.0 names *"the revision frozen"*** — `de98c17` is *assessed*, not locked; the corpus is **NOT FROZEN** and therefore amendable. Proves too much: would indict D-020/D-021's **13 documents** and **32 untracked files**. *Residue accepted: §1.2's stated reason is unsound and the L1/L2 distinction is undocumented — but §0.2's reasons 1–2 independently carry the placement* |
| **RT-4** Blind ≠ E7 | **P1** | **P1** | **FULL** | — | — | **UPHELD.** L1 §4.2: *"cannot be accelerated"* vs CU-13/M5/RFC-8: *"without waiting in wall-clock time."* Textual, triplicated; **CU-13 cites §4.2 in the sentence it contradicts.** Both readings of "Blind" fail. **Blast radius reduced:** [[EVIDENCE_MODEL]] §102's C4 definition independently requires nonexistence |
| **RT-5** SUPERSEDED | **P1** | **P3** | **Partial** | Core | — | **Custody Event `justification_ref` is labelled *"For SUPERSEDE"*** — the log holds supersession; no column needed. **The proposed `supersedes` column would violate CU-2** (attribute vs history). §7.2 stands. *Residue accepted: no adjudication rule for concurrent unsuperseded decisions (P3); timestamp ordering is insufficient per §4.3/R7.4* |

### Impact summary

| Finding | Architecture | Mechanism | Governance | Freeze |
|---|---|---|---|---|
| RT-1 | Declare the threat model (A9) | **Anchor — RFC-1 substrate** | — | **NO** |
| RT-2 | **None** | **None** | — | **NO** |
| RT-3 | **None** | — | Re-issue package at sign-off (**§144 already provides**) | **NO** |
| RT-4 | **CU-13 void per §0.4** | — | — | **YES** |
| RT-5 | Adjudication rule absent | Custody log (G-9/M1) | — | **NO** |

---

## 7. Verdict

> ## One of five upheld. **RT-4 alone blocks freeze.**
>
> **The red-team's claim that all five block freeze is rejected.** Four were misclassified: two rest on logical errors (**RT-2** denying the antecedent; **RT-1** a regress that would invalidate every integrity architecture ever built), one on a misreading the source document explicitly contradicts (**RT-3** vs certificate §144), and one proposes a remedy that violates the model it defends (**RT-5** vs CU-2).

**Three observations the Board considers material:**

1. **RT-4 — the only survivor — is the one where the author made a substantive false claim through motivated reading.** It survived the author's own attempt to clear it. **That is weak evidence this process is not purely self-serving. Weak, not strong: one case.**

2. **The red-team's own regularity holds against the red-team.** It concluded that the corpus's failures were *"failures of self-inspection."* **Four of its five findings are failures of self-inspection — inference errors an independent reviewer would likely not have made.** The author over-red-teamed exactly as he under-reviewed.

3. **This Board rejected four findings, and per §0 every rejection is structurally suspect.** The proofs are checkable; **per LIM8, "the proofs are checkable" is what an honest Board and a motivated Board both say.**

> **The deliverable is the proof set at §1–§5, not the matrix at §6. The External Validation Reviewer must check the four rejections. The one uphold — RT-4 — may be accepted without them: a refutation stands on its own demonstration (§2.2), whoever makes it.**

**Freeze status: unchanged. Blocked by G-8 (D-019), G-9, and now RT-4.**
