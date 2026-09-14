# FAMILY DECISION IMPLEMENTATION — 2026-09-11

**Task:** implement Owner family decision **Option B** — formalize {C2, C3, C7} as a separately-denominated hypothesis family, enter the governance receipts, preserve the G1 classification ledger, and run the mechanical C7 eligibility check. **No empirical execution of any kind.** The G1 result, Dataset B, and the withdrawn arms are untouched.

---

## A. Owner decision

**Option B** (from `OWNER_DECISION_PACKET_FAMILY_ASSIGNMENT_2026-09-11.md`): the already-registered arms **{C2, C3, C7}** are formalized as a **separately-denominated hypothesis family** ("P-M · C-family"), opened per the registry's own family-opening precedent (D-028, PG-3), with the G1 replacement registration as the first registration act. **No I-taxonomy assignment** (I5/I6/I7/I12) was made or inferred; the assignment question remains an Owner prerogative for the future. The P-M {I5, I6, I7, I12} denominator is unchanged.

## B. Exact registry changes (`HYPOTHESIS_REGISTRY.md`, append-only rows)

- **Three new "Registered & in-flight" rows:**
  - **HYP-PM-0004** — P-M · C-family · **C2** conduit disagreement — **INVALID (governance)**: executed in G1 Run 1, NOT CONFIRMED (Holm p = 1.0); registered species-mix control unimplementable (freq-dependent).
  - **HYP-PM-0005** — P-M · C-family · **C3** breadth surprise — **NOT CONFIRMED (VALID, bounded)**: primary k=5 Holm p = 1.0; determinate null, 329 daily observations.
  - **HYP-PM-0006** — P-M · C-family · **C7** intensity-state — **REGISTERED**, pending execution (gated).
- **New Family-slot ledger row:** `P-M · C-family {C2, C3, C7}` — 3 members, opened per **D-048** (Owner Option B); separately-denominated from {I5,I6,I7,I12}; C1a/C1b WITHDRAWN pre-execution and **not counted**; C7 execution gated (`c7_registered=false` + runs/<run_id> provenance wrapper per D-048).
- Header "Last updated" → 2026-09-11.
- **Unchanged:** the {I5, I6, I7, I12} ledger row (2 consumed members), all prior rows, the notes for HYP-PM-0001/0003/PA-0001.

## C. Exact decision-log receipts (`DECISION_LOG.md`, new section **2i**, entry **D-048**)

D-048 (APPROVED, Owner, Option B) entered with a scope note (owner directives issued via the ZCode session, recorded on the same basis as D-032/033) and a **seven-item governance receipt table**:

1. Dataset B freeze — store `21661f03…`, manifest v1 `95f2c998…`, FINGERPRINT_v2 `1a68ab1c…`.
2. BFI-002 replacement registration — `G1_REGISTRATION_v1_2026-09-11.md`; original NOT FOUND; not a reconstruction.
3. C1a/C1b withdrawal — unconditional, freq UNKNOWN/FORBIDDEN.
4. NF ratification — stockbit_flow share-ratio NF; digest `60f5f91c…`.
5. Six C7 owner decisions — incorporated in `C7_REGISTRATION_v1` §3.
6. G1 Run 1 + classification ledger (see §E).
7. The C-family decision itself (D-048).

Plus: the **provenance condition on future execution** (commit list per closeout §E2; `runs/<run_id>/` wrapper implemented or execution explicitly gated on it) and the explicit not-authorized list (no C7 run, no empirical run, no methodology/I-taxonomy change).

Also updated: `FAILURE_REGISTRY.md` — two new rows receipting the G1 outcome (**FAIL-PM-0004-G1** = C2 INVALID/governance; **FAIL-PM-0005-G1** = C3 NOT CONFIRMED, VALID bounded) with the mode-distribution note amended.

## D. Multiplicity consequences

- **P-M {I5, I6, I7, I12}: unchanged** — 2 consumed members (HYP-PM-0001, HYP-PM-0003); no C-arm assigned to it; no retroactive reclassification.
- **P-M · C-family: opened with 3 registered members** — C2 (consumed: INVALID), C3 (consumed: NOT CONFIRMED), C7 (registered, pending). C1a/C1b withdrawn pre-execution, not counted.
- The two families are **separately denominated**: no cross-family pooling; LIM2/LIM3 obligations were not triggered because no I-assignment was made.

## E. G1 classification preserved (verbatim)

C1a = **INVALID / non-reportable** · C1b = **WITHDRAWN / never implemented** · C2 = **INVALID** · C3 = **VALID → NOT CONFIRMED, bounded** · **G1 overall = SPLIT / governance-invalidated**. Receipted in D-048 and mirrored in the failure registry (FAIL-PM-0004-G1, FAIL-PM-0005-G1).

## F. C7 eligibility status

**GOVERNANCE-ELIGIBLE — execution not yet authorized.** Mechanical preflight (9/9 checks PASS): D-048 present in DECISION_LOG; registry contains the C-family row and HYP-PM-0004/0005/0006; failure registry contains the G1 outcome rows; store hash matches the freeze manifest; G1 gates all TRUE; `synthetic=false`; `freq_resolution="withdrawn"`; `c7_registered=false`. The harness C7 dispatch refuses (exit 2) until `c7_registered=true` — which is now purely an Owner execution-authorization act.

## G. Provenance / commit status

- **Working tree:** `g1_harness/` and `dataset_b/` are **entirely untracked** in git (verified via `git status`). All other modifications in the tree pre-date this program and were not touched.
- **Files that must be committed before any future empirical execution:** the exact list is in `G1_GOVERNANCE_CLOSEOUT_2026-09-11.md` §E2 — the harness + tests + probes, all registration/governance/report documents (including this file and the closeout), the Dataset B code + artifacts (including `DATASET_B_FREEZE_MANIFEST_v1.json` + sidecar), and the two governance registries as amended. The 276 MB frozen store binary is **held out of git by design** (pinned by the freeze manifest hashes); committing it is an owner policy decision.
- **Ownership:** `g1_harness/` is established as ZCode-owned and ZCode-maintained (all files created and executed by this side; no other author has touched it).
- **Provenance wrapper:** designed (closeout §E3), **explicitly gated** per D-048: no future empirical execution until the `runs/<run_id>/` wrapper is implemented and the pre/post-run digest gates pass.

## H. Remaining blockers

1. **Commit** of the governance/harness/registry files above (owner workflow act).
2. **`runs/<run_id>/` provenance wrapper implementation** (closeout §E3 design) — explicitly gating C7 execution per D-048.
3. **Owner execution authorization** for C7 (`c7_registered=true`) — after which `python3 g1_harness.py c7` executes the registered test end-to-end.

No empirical test was run in this task. No methodology, threshold, k-set, cost, exclusion, or inference parameter was changed. The G1 classification ledger is preserved verbatim.
