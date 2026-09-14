# G1 FINAL GOVERNANCE STATUS — 2026-09-11

**Task:** finalize G1 registration and remove the freq blocker. **G1 was NOT executed** (step 8: this task ends after registration + governance record + withdrawal + gate representation + preflight).

---

## 1. Verdict

**G1 IS FULLY UNBLOCKED AND REGISTERED — ready for execution on the next authorized command.** All four gates are TRUE on explicit, recorded authorizations; the fail-closed preflight passes with zero blockers; the retained family is {C2, C3} with C1a/C1b registered as WITHDRAWN. Per step 8, execution did not occur in this task.

## 2. Registration identity/version

- **Artifact:** `docs/research_programs/P-M/g1_harness/G1_REGISTRATION_v1_2026-09-11.md`
- **Identity:** NEW, dated **replacement registration** — explicitly **not** the recovered original. `BROKER_FLOW_PREREGISTRATION.md` remains NOT FOUND (fresh check this task + exhaustive retrieval 2026-09-11; corpus machine absent). Nothing was reconstructed from memory, summaries, implementation, or inference: every registered parameter is cited to the design record (`PM_SPECIES_MECHANISM_BFI002_DESIGN_2026-09-10.md`, sha `9c87888f…`), the inherited BFI-001 frozen conventions (`91c0eb9a…`), or an owner directive.
- **Parameters that could not be established from the authoritative record are registered as NOT SET, not invented:** MDE/power (DEP-B row 6 — no power claims authorized); C3's "after NF and ST controls" falsification clause (inapplicable — ST withdrawn with C1a; C3 runs as unconditional state contrast); C2's "species mix as control" (same); a control-conditioned regression variant for C2/C3 (not registered — would require new implementation). Section 9 of the registration lists all of them explicitly.

## 3. Exact owner decisions executed

| Decision | Authorization | Recorded as |
|---|---|---|
| Dated replacement registration for G1 | Task directive item 1 ("Prepare a dated replacement registration… Do not claim it is the recovered original") | `G1_REGISTRATION_v1_2026-09-11.md` |
| Withdraw freq-dependent arms C1a/C1b | Task directive item 2 (probe narrowed freq to transaction-like but did not establish orders-vs-fills; ~124× cross-vendor inconsistency unresolved) | Registration §1; harness `WITHDRAWN_FREQ_DEPENDENT` state; `freq_resolution="withdrawn"` |
| Retain C2/C3 under existing definitions | Task directive item 3 | Registration §4 (definitions unchanged; two design clauses registered as inapplicable, §9.2–9.3) |
| Stockbit NF construction stands | Task directive item 4 (no change) | `G1_GOVERNANCE_UNBLOCK_RECORD_2026-09-11.md` §3, unchanged |
| Gate updates after registration | Task directive item 6 | §7 below |

## 4. Arm status

- **Retained:** C2 (conduit disagreement), C3 (breadth surprise, **lead**). Definitions, thresholds (±0.30 surprise; 0.15 disagreement shares; 60-obs/30-min-history trailing median), k ∈ {3,5,10} with primary k=5, Holm α=0.05 across the retained family at primary k, 0.60% RT cost floor, and all exclusions unchanged.
- **Withdrawn:** C1a, C1b. They never execute while `freq_resolution="withdrawn"` is registered — independent of any gate (verified by test, including with the freq gate OPEN).

## 5. Freq status

`broker_flow.freq` remains **UNKNOWN** (SEMANTIC_REGISTER_v1 unchanged) and is **unused everywhere**: not a denominator, not a transaction count, not read by any retained arm. The probe's findings (near-balance 1.0031; 1-lot floor at p05; ~124× cross-vendor inconsistency; 3.94% sub-1-lot rows) are recorded in `G1_GOVERNANCE_UNBLOCK_RECORD_2026-09-11.md` §2. `freq_semantics_ratified=true` means **only** "the freq question is resolved by registered withdrawal of C1a/C1b" — it is not a claim that freq semantics are known (config note states this verbatim).

## 6. NF status

Unchanged and ratified: `NF = (buy_lot − sell_lot)/(buy_lot + sell_lot)` from production `stockbit_flow` (share-ratio reduction of the owner's value formula), T+1 availability, market-flow-control interpretation only, zero-denominator exclusion, digest `60f5f91c…`. This task's preflight re-verified the digest against the live table: **match** (an initial apparent mismatch was a serialization difference in the check itself — the recorded pin method is `sqlite3 -json` bytes; the run-book mandates re-verification with that exact method).

## 7. Dataset B freeze identity + gate states

- Store sha256 `21661f033145ef90…` — **re-verified this task, matches `DATASET_B_FREEZE_MANIFEST_v1.json`**.
- Gates: `dataset_b_frozen=true` · `prereg_confirmed=true` (replacement registration, per owner authorization item 6) · `freq_semantics_ratified=true` (withdrawal sense) · `net_flow_source_ratified=true` · `synthetic=false` · `freq_resolution="withdrawn"`.
- Config snapshot preserved inside `G1_FINAL_GOVERNANCE_STATUS` companion: the pre-gate-update config was `dataset_b_frozen=true`, all others false (recorded in `G1_EXECUTION_REPORT_2026-09-11.md` §B); no other parameter changed.

## 8. Preflight result (fail-closed run, no execution)

| Assertion | Result |
|---|---|
| `check_gates(real_data=True)` with final config | **empty — zero blockers** |
| Store hash == freeze manifest | **True** |
| NF digest == recorded pin (identical serialization) | **True** |
| PIT roster/calendar artifacts sha-verify; Σ members 30,880 (v1 ≡ v2); 386 sessions | **True** |
| Test suite | **16/16 PASS** (incl. new withdrawn-state test) |
| No production DB write target | loader/connections ro + `query_only`; dry/synthetic paths open no DB |
| No future-data path | synthetic-tested (T+1 dumps, forward-dated rows cannot leak) |
| C1a/C1b non-execution | `WITHDRAWN_FREQ_DEPENDENT` unconditional under `freq_resolution="withdrawn"` (tested with freq gate open AND closed) |

## 9. Remaining blocker

**None.** No engineering, data-integrity, gate-wiring, or registration work remains. The only outstanding item before numbers exist is the execution command itself, which is now an owner scheduling decision:

```bash
cd "/home/tjiesar/10 Projects/idx-walkforward-5001/docs/research_programs/P-M/g1_harness"
G1_CONFIG=./g1_config.json python3 g1_harness.py    # → g1_real_output.json
```

Run-book requirements at that moment: re-verify the store hash (`21661f03…`), the NF digest (`60f5f91c…`, `sqlite3 -json` method), and gate values; then preserve `g1_real_output.json` + config snapshot + code sha256 + timestamps per the standing preservation rule.
