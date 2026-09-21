# NEXT LAWFUL HYPOTHESIS AUDIT — 2026-09-14

**Authority:** generated point-in-time record (audit only). **No empirical execution performed.**
No backtest, no parameter tuning, no methodology change, no registry mutation, no Dataset B change,
no `research.db` write, no production DB write, no C7 change, no C8 registration, no new hypothesis
created.

---

## Scope note on sourcing

This audit deliberately does not re-derive facts from scratch where a prior, dated, independently-
verified forensic document already exists and remains uncontradicted: **`FOUR_TEST_IDENTITY_AND_REGISTRY_AUDIT_2026-09-11.md`**
contains a "Master Experiment Inventory" (its Part E) of **20 objects** spanning every hypothesis,
experiment, and candidate found anywhere in this repository, `research.db`, and the ZCodeProject
side corpus, cross-checked against `HYPOTHESIS_REGISTRY.md`, `FAILURE_REGISTRY.md`, `DECISION_LOG.md`,
and `EXPERIMENT_LEDGER.jsonl`. This audit (a) re-verifies that inventory is still current as of
2026-09-14, (b) re-reads every non-terminal-looking row's source document directly rather than
trusting the summary, and (c) applies this task's specific exclusion/ranking rules to it. Two items
(C7's actual execution, and LIT-002's verdict file, both post-dating or unresolved as of 2026-09-11)
were independently re-verified in this session — see §2 rows 7 and 11.

---

## A. Complete surviving-hypothesis table

"Surviving" = not itself excluded by this task's hard-exclusion list (§3). All 20 inventory objects
plus BROKER-001 (already counted as object 4) are shown; terminal/excluded objects are included for
completeness of the inventory but are struck from candidacy in the **Candidate?** column.

| # | ID | Family/Program | Registered? | Tested? | Terminal? | Verdict | Candidate? |
|---|---|---|---|---|---|---|---|
| 1 | HYP-PM-0001 | P-M {I5,I6,I7,I12} | Yes (2026-07-17) | Yes | Yes | FAILED F2 | No — terminal |
| 2 | HYP-PM-0002 | P-M {I5,I6,I7,I12} | **No — DRAFT only, no slot** | No | No | — | No — not registered |
| 3 | HYP-PM-0003 | P-M {I5,I6,I7,I12} | Yes (2026-09-09) | Yes | Yes | FAILED F2 (→ proposed INVALID-DATA/SEMANTICS, unratified reclass) | **No — hard-excluded by task** |
| 4 | BROKER-001 / BFI-001 | none (research.db only; no registry row) | "PREREGISTERED" (DB status, not a HYPOTHESIS_LIFECYCLE term) | **Yes — executed 2026-09-03**, `90_results.json` | Yes (primary); secondaries valid-but-unconfirmed | PRIMARY = INVALID—DATA; structure secondaries (CONC/BREADTH/LOKAL) = VALID → NOT CONFIRMED (Holm 0.097/0.164) | No — already executed |
| 5 | HYP-PM-0004 (C2) | P-M C-family | Yes | Yes | Yes | INVALID (governance/specification) | **No — hard-excluded by task** |
| 6 | HYP-PM-0005 (C3) | P-M C-family | Yes | Yes | Yes | NOT CONFIRMED (valid, bounded) | **No — hard-excluded by task** |
| 7 | HYP-PM-0006 (C7) | P-M C-family | Yes | **Yes — executed 2026-09-14** (`C7_EXECUTION_REPORT_2026-09-14.md`, `runs/RUN-20260914T015335Z-…/c7_real_output.json`; independently observed live in this session, working-tree `g1_config.json` now shows `c7_registered: true`, uncommitted) | Yes | NOT CONFIRMED (per this task's own stated current state) | **No — hard-excluded by task** |
| 8 | C1a | P-M C-family | Registered-then-withdrawn | Withdrawn pre-execution (in-memory compute nulled; non-reportable) | Yes | WITHDRAWN, no numbers | No — withdrawn |
| 9 | C1b | P-M C-family | Registered-then-withdrawn | Never implemented | Yes | WITHDRAWN | No — withdrawn |
| 10 | LIT-001 | LIT line | Registered/frozen | Yes | Yes | REJECTED | No — terminal |
| 11 | LIT-002 | LIT line | **Yes** — `10_PREREGISTRATION_FROZEN.md`, sha `c2b03399…` | **Attempted 2026-08-30; 0/201 required OOS steps observed** | **INCONCLUSIVE, not terminal — but not executable now** | INCONCLUSIVE (power/coverage gate failed at n=0; next eligible re-run date ≈ 2028-04) | **No — see §D, closest near-miss** |
| 12 | H1 foreign-flow continuous | older program | Preregistered | Yes | Yes | null | No — terminal |
| 13 | H6 foreign-flow extremes | older program | Preregistered | Yes | Yes | pressure signal only, not tradable | No — terminal/non-actionable |
| 14 | HLIQ / EXP-HLIQ | H-LIQ line | `08_HLIQ_PREREGISTRATION.md`, sha `a87b5721…` — "SINGLE PRE-REGISTERED EXECUTION" by its own header | **Yes — executed**, `12_HLIQ_RESULTS.json` exists | Yes (single-execution design; already used) | per its own rule | No — already executed (and by design may not be re-run) |
| 15 | NR7 Breakout / P0 | Program P0 | Registered 2026-07-12 | Yes, ×6 + falsification | Yes | FALSIFIED / SHADOW (D-029) | No — terminal |
| 16 | HYP-PA-0001 / EXP-PA-0001 | P-A {I2,I3,I8} | Yes (2026-07-19) | Yes | Yes | FAILED F2 | No — terminal (sole P-A member) |
| 17 | S2-PM-0004 | census | Withdrawn candidate | Executed (read-only census) | Yes | WITHDRAWN | No — withdrawn |
| 18 | Liquidity Sweep | legacy production research | — | Yes | Yes | falsified | No — terminal |
| 19 | distribution (shadow) | legacy production research | — | Yes | Yes | falsified | No — terminal |
| 20 | BFI-001 F3_lots/F3_n2 sub-cells | inside BFI-001 | inside BFI-001 registration | Executed → NaN/no result | Yes (uncomputable) | no result | No — crashed/uncomputable |

**Total: 21 rows (20-object inventory + BROKER-001 already listed as #4). Zero rows are both
(a) registered, (b) untested, and (c) mechanically executable today.**

---

## B. Recommended next lawful hypothesis

**None.**

No object in the complete inventory satisfies the task's own §5 distinction — "registered" is not
the same as "lawfully executable" — for even one of them at the same time. Specifically:

- The only **registered** objects that were never executed at all are **HYP-PM-0002** (DRAFT — not
  actually REGISTERED under this corpus's own status legend, and explicitly noted as consuming no
  family slot) and the withdrawn **C1a/C1b**. None is registered in the binding sense the corpus uses
  (`DRAFT → REGISTERED → ...`); DRAFT and WITHDRAWN are both excluded by the task's own criteria
  ("untested" is necessary but not sufficient — HYP-PM-0002 is untested but unregistered; C1a/C1b are
  untested but withdrawn).
- The only object that is **registered, untested-to-completion, and not hard-excluded** is
  **LIT-002** — and it fails criterion 5 (mechanically executable) outright: its own frozen verdict
  document states the required 201-step OOS power/coverage gate had **0/201** evaluable steps as of
  2026-08-30, and the earliest date at which a re-run could even be attempted is **≈ 2028-04** (≈402
  IDX trading days of passive accrual). It additionally fails criterion 8 (no need for a new
  decision): its own "NEXT ACTION" section requires an explicit Owner choice between two branches
  (pin a fixed 2028 re-run date, or formally retire the lead) before anything can happen to it at all.
- Every other object in the inventory has already been executed to a terminal (or, for C3/C7,
  determinate-null) result, or is explicitly excluded by this task's hard-exclusion list.

**Therefore: NO LAWFUL SURVIVOR.**

---

## C. Exact evidence supporting this status

- `docs/research_programs/HYPOTHESIS_REGISTRY.md` — every row is either terminal (FAILED/INVALID) or
  hard-excluded (C2/C3/C7); the only non-terminal registry entries besides C-family are P-M's own two
  members (HYP-PM-0001, HYP-PM-0003), both FAILED.
- `docs/research_programs/FAILURE_REGISTRY.md` — 5 rows, all terminal/governance-invalidated;
  consistent with the registry.
- `docs/roadmap/DECISION_LOG.md` — last entry **D-049** (2026-09-11); no entry authorizes any new
  execution beyond what §A already accounts for; no D-050+ exists yet even in the current
  (uncommitted) working tree.
- `docs/research_programs/EXPERIMENT_LEDGER.jsonl` — every populated row matches a terminal object in
  §A (HYP-PM-0001/0003, BROKER-001, plus three unlabeled falsified/withdrawn legacy rows); no row
  indicates an untested-and-ready object.
- `data/research.db::hypotheses` (read-only query, this session) — exactly **one** row,
  `BROKER-001`, status `PREREGISTERED`, already executed 2026-09-03 (§A row 4); `hypothesis_links` is
  empty (0 rows) — confirmed live, matches the 2026-09-11 forensic finding.
- `docs/research_programs/P-M/g1_harness/FOUR_TEST_IDENTITY_AND_REGISTRY_AUDIT_2026-09-11.md` Part E —
  the 20-object master inventory this audit is built on; independently re-checked, not contradicted.
- `/home/tjiesar/ZCodeProject/lit002_ofi_reversal_oos/70_LIT002_FINAL_VERDICT.md` — read in full this
  session; confirms INCONCLUSIVE verdict, 0/201 OOS steps, ≈2028-04 earliest re-run eligibility,
  explicit unresolved Owner branch decision.
- Live filesystem check this session — `C7_EXECUTION_REPORT_2026-09-14.md` and
  `runs/RUN-20260914T015335Z-41bea166a025/c7_real_output.json` exist with today's mtimes, confirming
  C7 (row 7) is now executed and correctly hard-excluded per this task's own stated current state.

---

## D. Blockers

1. **No registered-and-untested object exists that is not itself blocked.** This is not a data or
   mechanics problem for most of the inventory — it is that the entire currently-registered set has
   already been run.
2. **LIT-002 (the sole near-miss) is blocked by elapsed calendar time, not by anything correctable
   now:** its own frozen design requires ≈402 IDX trading days of passive OOS accrual before its
   201-step power/coverage gate can even be evaluated (earliest eligible date ≈ 2028-04). No
   acceleration, re-windowing, or threshold change is authorized under its own frozen decision tree —
   attempting one would itself be a prohibited methodology change.
3. **LIT-002 additionally requires an Owner branch decision independent of the accrual clock**: pin
   a single fixed future re-run date and hold the lead dormant with no interim inspection, **or**
   formally retire the k=2 lead unexecuted. Neither branch produces an executable test today.
4. **HYP-PM-0002 is not registered** in the binding sense (`DRAFT`, no slot consumed) — promoting it
   would require a new, dated Owner-authorized registration act, which is explicitly out of this
   task's scope ("no new hypothesis creation," "no registry mutation").
5. **No other program (P-A, P0) has an unconsumed, registered, untested member** — P-A's single
   family slot (HYP-PA-0001) is terminal; P0/NR7 is FALSIFIED/SHADOW and is the frozen reference
   implementation, not a source of new tests.

**Exact governance action needed to continue at all:** either (a) a **new hypothesis registration**
(explicitly out of scope here — this audit does not draft one), which would itself need to clear the
Part G semantic-register hard-gate rule (`FOUR_TEST_IDENTITY_AND_REGISTRY_AUDIT_2026-09-11.md` Part G,
proposed but "not deployed" as of that document) if it touches any broker-flow net/gross construction;
or (b) the Owner's LIT-002 branch decision, which — even taken immediately — does not produce an
executable test before ≈2028-04. There is no governance action available that unlocks a test
executable **today**.

---

## E. Report path

`docs/research_programs/P-M/g1_harness/NEXT_LAWFUL_HYPOTHESIS_AUDIT_2026-09-14.md`

---

## F. Files changed

One file created — this report. No other file in the repository, `research.db`, Dataset B, or the
ZCodeProject side corpus was created, edited, or deleted by this task. (The `git status` state
already includes ordinary unrelated pre-existing changes from before this task — see the prior
session's audit reports for that inventory; nothing in it was added to by this task.)

---

## G. Confirmation

**No empirical test was run.** No backtest, parameter tuning, methodology change, registry mutation,
Dataset B change, `research.db` write, production DB write, C7 change, C8 registration, or new
hypothesis was created or executed by this task.

---

## Final classification

### NO LAWFUL SURVIVOR

Every registered hypothesis/family member in the complete inventory (§A) is either terminal
(executed to a failed/invalid/not-confirmed result), hard-excluded by this task's own instructions,
withdrawn, or — in LIT-002's sole case — registered but mechanically blocked by ~19–20 months of
required, unaccelerable OOS data accrual plus an unresolved Owner branch decision. No candidate
satisfies even the first two of the task's eight ranking conditions (already registered *and* already
Owner-approved *and* untested) simultaneously with mechanical executability today. Continuing the P-M
or P-A programs empirically requires either a genuinely new Owner-authorized registration (out of this
task's scope) or waiting on LIT-002's fixed accrual clock — not a decision this audit can make or
accelerate.
