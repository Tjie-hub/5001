# G1 GOVERNANCE CLOSEOUT — FAMILY DETERMINATION, ARTIFACT AUDIT, PROVENANCE REPAIR PLAN — 2026-09-11

**Mode:** governance analysis only. No empirical execution (C7/C6/C8/G1 untouched). No methodology change. No Dataset B modification.

---

## A. Authoritative facts (verified this task)

1. **Dataset B is frozen and intact.** Store sha256 `21661f033145ef90…` matches `DATASET_B_FREEZE_MANIFEST_v1.json`; FINGERPRINT_v2 `1a68ab1c…` and supplementary fold `13033786…` reproduce.
2. **G1 Run 1 executed 2026-09-11** (exit 0, REAL mode, 28,624 panel rows, 375 formation dates): C2 Holm p = 1.0 (not confirmed), C3 Holm p = 1.0 (not confirmed), C1a/C1b `WITHDRAWN_FREQ_DEPENDENT`. Raw output preserved sha `74883c04…`; run manifest `G1_RUN_MANIFEST_RUN1_2026-09-11.json`.
3. **`HYPOTHESIS_REGISTRY.md`** (append-only): P-M family = **{I5, I6, I7, I12}**, 2 slots consumed (HYP-PM-0001 FAILED F2, HYP-PM-0003 FAILED F2); HYP-PM-0002 DRAFT consumes no slot; membership counted **from registration** and never leaves (PG-3, OS-10). Zero references to broker-flow-v002, H0–H3, C1a/C1b/C2/C3, or C7.
4. **Taxonomy** (`docs/research_os/MARKET_INEFFICIENCY_TAXONOMY.md`): I5 = inventory-imbalance liquidity premium (requires explicit I7-exclusion, LIM2); I6 = illiquidity premium; I7 = adverse-selection premium; I12 = capacity-shielded deviation (**a modifier — testable only through a host entry**, requires a capacity gradient). **No I-entry mentions or maps any C-numbered candidate.**
5. **DECISION_LOG**: latest broker-flow entries are D-032 (window/freeze decisions; Items C, D OPEN) and D-033 (admission path H-1; H-2…H-6 open) — both explicitly note the authoritative broker-flow preregistration corpus lives off-machine and that external owner approvals are recorded "on the same basis". **No DECISION_LOG entry exists for the Dataset B freeze, the G1 replacement registration, the C1a/C1b withdrawal, the NF ratification, the six C7 decisions, or the G1 FAIL.**
6. **Working tree (git):** repository is a git repo; `docs/research_programs/P-M/dataset_b/` and `docs/research_programs/P-M/g1_harness/` are **entirely untracked** (`??`). The broader tree carries many pre-existing unrelated modifications (untouched by this program).

## B. Determinations supported by existing governance

### B1. Family/multiplicity mapping for C2, C3, C7 — **UNRESOLVED**

The authoritative hierarchy determines the *frame* but not the *assignment*:

- The P-M multiplicity family is defined over taxonomy entries {I5, I6, I7, I12}; membership is created by registration and is append-only.
- The G1 replacement registration and the C7 registration use **C-numbers** (discovery-candidate labels from the family map), and **no authoritative document assigns any C-number to an I-taxonomy entry**. The taxonomy itself imposes mapping-conditional obligations (I5 requires an I7-exclusion statement; I12 is testable only through a host entry with a capacity gradient) — obligations that differ per entry and therefore change what a mapping would commit us to.
- Plausible affinities exist (C3/C7 touch flow-premium/liquidity territory near I5/I6; C2 near I5/I7), but affinity is not assignment, and the taxonomy's own rules (LIM2/LIM3: unseparated confounds have tested neither; pooling corrupts the family denominator) make a wrong assignment worse than none.

**Determination: UNRESOLVED — the mapping requires an explicit owner/CRO taxonomy assignment per arm.** It cannot be derived from HYPOTHESIS_REGISTRY, DECISION_LOG, the design memo, the family map, or the registrations without inventing it.

**Multiplicity consequences of that unresolved state:** until the assignment exists, G1's C2/C3 FAIL and any future C7 result **cannot be counted into the P-M family denominator** (slot consumption is undefined), and no statement about the P-M family's multiplicity position relative to {I5,I6,I7,I12} is possible. This does not affect the internal validity of the G1 run itself — only its ledger registration.

### B2. Governance-artifact audit — authoritative vs working documents

| Artifact | Current status | Basis | Gap |
|---|---|---|---|
| Dataset B freeze manifest v1 + store | **Authoritative (executed freeze)** | Owner directive (task step 1); hashes pinned; integrity verified | Freeze act not yet receipted in DECISION_LOG (no D-entry) |
| G1 replacement registration v1 | **Authoritative-by-owner-directive** | Task directive item 1 (previous execution task); incorporates the six C7-adjacent owner decisions | Not entered in HYPOTHESIS_REGISTRY or DECISION_LOG; no canonical receipt (R-1 analog outstanding — same pattern D-033 ruled sufficient for Dataset A, Option A) |
| C1a/C1b withdrawal | **Authoritative-by-owner-directive** | Registration §1 + unconditional harness behavior + owner directive item 2 | Same receipt gap |
| NF ratification (stockbit_flow share-ratio) | **Authoritative-by-owner-directive, validated** | `G1_GOVERNANCE_UNBLOCK_RECORD` §3; validation results recorded | Same receipt gap; semantic register still has no `stockbit_flow` entry |
| C7 registration v1 | **Authoritative-by-owner-directive (six decisions incorporated)** | Task directive + owner's six decisions | Same receipt gap; execution gated on `c7_registered` |
| G1 FAIL result | **Empirical fact, preserved** | Run manifest + immutable raw copy | Registry/ledger entry owed (append-only) |
| All G1-era reports (readiness, semantics audit, retrieval, triage, unblock record) | **Working documents / evidence records** | Cite authoritative sources; they are not themselves governance acts | — |

**Summary:** every G1/C7 governance act in this program was issued by explicit owner directive and recorded faithfully in the harness directory — but **none has been receipted into the canonical governance corpus** (DECISION_LOG entry + registry row). Per the repository's own D-032/D-033 precedent, such directives are recorded in DECISION_LOG "on the same basis"; those entries do not yet exist for this sequence.

### B3. G1 classification ledger (proposed — consistent with authoritative evidence)

| Arm | Proposed classification | Evidence |
|---|---|---|
| C1a | **INVALID / non-reportable** | WITHDRAWN before execution; freq UNKNOWN; produced no numbers; no substitute computed |
| C1b | **WITHDRAWN / never implemented** | Withdrawn at registration; no C1b cell ever existed in the harness (family-level label only) |
| C2 | **INVALID** (governance-invalidated, not empirically refuted) | Executed, but its registered control structure (species-mix control, memo §7) was unimplementable (freq-dependent); the registered execution form was an unconditional contrast, which does not test the designed conditional estimand. Registration §9.3 recorded this limitation before the run. |
| C3 | **VALID → NOT CONFIRMED (bounded)** | Executed exactly as registered (unconditional state contrast was its complete registered form; the ST-control clause was registered inapplicable). Determinate null at primary and all horizons; robust to family recomposition (Holm over {C3} alone still yields p = 0.747 — arithmetic on the existing output, no re-run). |
| **G1 overall** | **SPLIT / governance-invalidated** | One valid bounded null (C3) + one governance-invalidated arm (C2) + two withdrawn arms. The family verdict cannot be treated as a clean test of the original three-arm design; the only reportable empirical content is C3's bounded null. |

No authoritative evidence contradicts these classifications; they are adopted as proposed.

## C. Unresolved owner decisions

1. **Taxonomy/family assignment (the blocker):** assign C2, C3, C7 (and C6/C8 prospectively) to I-taxonomy entries — or register them as a separately-defined family with its own denominator — by a dated DECISION_LOG/registry entry. Required before any of their results can be counted in the P-M multiplicity position.
2. **Receipt of the directive sequence:** a DECISION_LOG entry (D-032/D-033 basis) receipting the Dataset B freeze, the G1 replacement registration, the C1a/C1b withdrawal, the NF ratification, the six C7 decisions, and the G1 FAIL — closing the "external directive, unreceipted" gap for the whole chain.
3. **Registry bookkeeping:** append the G1 FAIL row + the C1a/C1b withdrawal + the C7 registration to `HYPOTHESIS_REGISTRY.md` per the append-only rule (currently zero references).
4. **D-032 Items C/D** (§4/§5 contradiction; turnover definition) remain OPEN and are unaffected by G1's FAIL (the retained arms were not H1-specification tests).
5. Commit decision for the untracked program directories (§E).

## D. Exact next gate

**OWNER: taxonomy/family assignment + governance receipt.** C7 remains paused until decision 1 (assignment) and decision 2 (C7 registration receipt) land; the C7 harness gate `c7_registered` is true, but the governance gate above stands ahead of it. No engineering work is blocked or owed.

## E. Provenance / ownership repair

### E1. Working-tree state (recorded)

- Untracked (this program's entire output): `docs/research_programs/P-M/g1_harness/` (harness, tests, probes, registration, all governance/execution reports, G1 run artifacts) and `docs/research_programs/P-M/dataset_b/` (foundation/validate/fingerprint/backfill code, artifacts incl. freeze manifest, and the 276 MB frozen store with live `-wal`/`-shm`).
- Unrelated pre-existing modifications elsewhere in the tree: untouched, not listed here, not this program's concern.

### E2. Files that must be committed before future execution (exact)

**Must commit (governance + reproducibility chain):**
```
docs/research_programs/P-M/g1_harness/g1_harness.py
docs/research_programs/P-M/g1_harness/g1_config.json
docs/research_programs/P-M/g1_harness/g1_synthetic.py
docs/research_programs/P-M/g1_harness/test_g1_harness.py
docs/research_programs/P-M/g1_harness/test_c7_registration.py
docs/research_programs/P-M/g1_harness/freq_probe.py
docs/research_programs/P-M/g1_harness/nf_validate.py
docs/research_programs/P-M/g1_harness/G1_REGISTRATION_v1_2026-09-11.md
docs/research_programs/P-M/g1_harness/C7_REGISTRATION_v1_2026-09-11.md
docs/research_programs/P-M/g1_harness/G1_GOVERNANCE_UNBLOCK_RECORD_2026-09-11.md
docs/research_programs/P-M/g1_harness/C7_PROPOSED_DECISION_RECORD_2026-09-11.md
docs/research_programs/P-M/g1_harness/G1_OWNER_DECISION_PACKET_2026-09-11.md
docs/research_programs/P-M/g1_harness/G1_MECHANICAL_READINESS_2026-09-10.md
docs/research_programs/P-M/g1_harness/G1_PREEXECUTION_SEMANTICS_AUDIT_2026-09-10.md
docs/research_programs/P-M/g1_harness/G1_AUTHORITATIVE_PREREG_RETRIEVAL_2026-09-11.md
docs/research_programs/P-M/g1_harness/G1_FREEZE_READINESS_2026-09-11.md
docs/research_programs/P-M/g1_harness/G1_POSTMORTEM_FAMILY_TRIAGE_2026-09-11.md
docs/research_programs/P-M/g1_harness/G1_FINAL_GOVERNANCE_STATUS_2026-09-11.md
docs/research_programs/P-M/g1_harness/G1_EXECUTION_REPORT_2026-09-11.md
docs/research_programs/P-M/g1_harness/G1_FINAL_EXECUTION_REPORT_2026-09-11.md
docs/research_programs/P-M/g1_harness/G1_GOVERNANCE_CLOSEOUT_2026-09-11.md
docs/research_programs/P-M/g1_harness/G1_REAL_OUTPUT_RUN1_2026-09-11.json
docs/research_programs/P-M/g1_harness/G1_RUN_MANIFEST_RUN1_2026-09-11.json
docs/research_programs/P-M/dataset_b/artifacts/DATASET_B_FREEZE_MANIFEST_v1.json (+ .sha256)
docs/research_programs/P-M/dataset_b/artifacts/  (all Dataset B artifacts: roster/calendar v1+v2 + sidecars, FINGERPRINT v1+v2 + sidecar, SEMANTIC_REGISTER, VALIDATION_REPORT, GAP_CLASSIFICATION, OUTSIDE_BAND_INVESTIGATION, CAPTURE_COMPLETENESS)
docs/research_programs/P-M/dataset_b/*.py  (foundation, validate, fingerprint, fingerprint_v2, build_calendar_and_roster, backfill_broker_flow, gap_classifier, investigate_outside_band)
docs/research_programs/P-M/dataset_b/DATASET_B_FOUNDATION_CLOSURE_REPORT_2026-09-10.md
docs/research_programs/P-M/dataset_b/DATASET_B_FINAL_RECONCILIATION_2026-09-11.md
docs/research_programs/P-M/dataset_b/DATASET_B_BROKERFLOW_BACKFILL_REPORT_2026-09-11.md
```
Plus, once the owner issues it: the DECISION_LOG receipt entry for the directive sequence (§C item 2).
Note: this report itself (`G1_GOVERNANCE_CLOSEOUT_2026-09-11.md`) belongs on the same list.

**Hold out of git (record by hash only):** the 276 MB frozen store binary (`DATASET_B_BROKER_FLOW_STORE_v1.sqlite` + wal/shm) and the G1 trial raw/ corpus — their integrity is pinned by the freeze manifest and digests; committing multi-hundred-MB binaries to git is an owner policy decision, not a provenance requirement.

**Do NOT commit:** anything outside the program dirs; the unrelated dirty worktree files.

### E3. Provenance repair mechanism (DESIGN ONLY — not implemented)

`runs/<run_id>/` immutable run directories, fail-closed on drift:

1. **Run ID:** `RUN-<UTC yyyyMMddTHHMMSSZ>-<first12 of preflight digest>`.
2. **Preflight step (new, wrapper-level):** before any load, compute sha256 over: executed Python sources (g1_harness.py + imported program modules), config file, registration document, freeze manifest, store file (or its recorded freeze hash), NF window extract digest, roster/calendar artifact hashes. Write `runs/<run_id>/preflight_manifest.json` (sources, hashes, gate values, registration reference). Verify every hash against its registered pin — **any mismatch aborts before data access**.
3. **Execution:** the run writes ALL outputs (raw output, post-run manifest, log) only into `runs/<run_id>/`. The harness core is unchanged; the wrapper computes digests, creates the directory, invokes the run, and closes it.
4. **Post-run step:** re-hash sources + config; mismatch vs the preflight manifest ⇒ the run is stamped `INVALID_PROVENANCE` (output retained but marked non-reportable) — fail-closed after the fact as well.
5. **Append-only:** `runs/` is never cleaned or overwritten; `runs/index.jsonl` gains one line per run (run_id, digests, verdict). G1 Run 1 is grandfathered by re-certification: its already-preserved output + manifest hashes are recorded as `RUN-G1-RUN1` in the index without re-execution.
6. **Gate integration:** `c7_registered`/future gates stay as they are; the wrapper adds the provenance layer without touching methodology.

## F. Exact next gate (single)

**OWNER decision: taxonomy/family assignment for C2/C3/C7 (±C6/C8) + governance receipt entry.** Until that dated record exists, C7 stays paused and the G1 FAIL remains unregistered in the canonical ledger. After it, C7's execution authorization is the owner's one-key act (`c7_registered=true`) with the §E3 wrapper in place.

---

*Stop condition honored: no empirical execution of any kind. This report is the only file created by this task.*
