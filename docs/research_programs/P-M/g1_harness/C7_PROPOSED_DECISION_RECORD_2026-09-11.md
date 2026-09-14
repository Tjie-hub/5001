# C7 DECISION RECORD — 2026-09-11

**Status: OWNER-APPROVED (six decisions, same date) — EXECUTION NOT YET AUTHORIZED.**
The owner approved the six open C7 decisions on 2026-09-11 (directive "FINALIZE AND VERIFY C7 REGISTRATION"). The registration `C7_REGISTRATION_v1_2026-09-11.md` exited DRAFT and is now REGISTERED with those decisions incorporated verbatim. C7 execution itself remains a separate future authorization and did not occur.

---

## Status: PROPOSED — NOT EXECUTED, NOT AUTHORIZED FOR EXECUTION. This record proposes the governance state after G1's registered FAIL and identifies C7 as the next independent test candidate. It becomes operative only upon owner approval of the decisions it contains.

---

## R-1 · G1 closed as FAIL

G1 Run 1 (2026-09-11, registered under `G1_REGISTRATION_v1_2026-09-11.md`) executed the retained family on frozen Dataset B (store sha256 `21661f03…`, FINGERPRINT_v2 `1a68ab1c…`) and produced:

- C2 (conduit disagreement): primary k=5 θ = +4.9 bp, NW t = +0.548, p = 0.584, **Holm p = 1.0 — NOT CONFIRMED**; signs +/+/−.
- C3 (breadth surprise): primary k=5 θ = +5.8 bp, NW t = +0.323, p = 0.747, **Holm p = 1.0 — NOT CONFIRMED**; signs +/+/−.

Per the registered decision rule (confirmed iff Holm p < 0.05 at primary k AND sign consistency across k ∈ {3,5,10}): **G1 = FAIL.** The failure is determinate (329–365 daily observations per cell), not power-limited, and gross effects sit far below the 0.60% RT floor. Per the no-rescue rule: C2 is not re-run, C3 is not re-run, C1a/C1b remain `WITHDRAWN_FREQ_DEPENDENT`, and no alternative specification may revive them. Evidence: `G1_FINAL_EXECUTION_REPORT_2026-09-11.md`; raw output `G1_REAL_OUTPUT_RUN1_2026-09-11.json` (sha256 `74883c04…`); run manifest `G1_RUN_MANIFEST_RUN1_2026-09-11.json`.

## R-2 · C2/C3 recorded as NOT CONFIRMED

Both arms are recorded as not confirmed on IDX at this specification and data. This record does not weaken, re-interpret, or re-open the G1 result, and does not license any post-hoc subgroup or threshold analysis of it.

## R-3 · C1a/C1b recorded as WITHDRAWN

The freq-dependent arms remain withdrawn under the 2026-09-11 replacement registration: `broker_flow.freq` is UNKNOWN/FORBIDDEN (SEMANTIC_REGISTER_v1; probe evidence in `G1_GOVERNANCE_UNBLOCK_RECORD_2026-09-11.md` §2), the arms never execute (`WITHDRAWN_FREQ_DEPENDENT`, unconditional), and their withdrawal is not a claim that freq semantics are known.

## R-4 · C7 identified as the PROPOSED next independent test

Per the postmortem triage (`G1_POSTMORTEM_FAMILY_TRIAGE_2026-09-11.md` §E): C7 intensity-state (map families D+H) is freq-free, data-ready from the frozen Dataset B store plus production ohlcv, was pre-designated a primary survivor by the custody handoff, and carries the strongest measured descriptive footprint among the unregistered survivors (persistence 45.7–48.1% vs 11.3% base). Its candidate registration is `C7_REGISTRATION_v1_2026-09-11.md`, which contains **NOT SET — OWNER DECISION REQUIRED** items (outcome variable, contrast construction, horizons, multiplicity packaging, MDE stance) that must be decided before any run.

## R-5 · NOT authorized by this record

No C7 execution; no return computation; no threshold tuning or state-boundary optimization; no subgroup search; no overlay; no Dataset B modification; no change to the G1 result or the withdrawn status; no claim that C7 was previously preregistered.

## R-6 · Owner decisions REQUIRED to proceed — **SUPPLIED 2026-09-11 (APPROVED)**

The owner approved the following six decisions verbatim (directive "FINALIZE AND VERIFY C7 REGISTRATION"); they are incorporated in `C7_REGISTRATION_v1_2026-09-11.md` §3:

1. **Outcome = directional forward return** (Dataset B calendar-indexed close→close, strict contiguity).
2. **Contrast = pre-specified high-intensity state vs pre-specified normal/non-high state**, frozen before execution; dates lacking either side skipped and counted.
3. **Horizons k ∈ {3,5,10}, primary k = 5**, program forward-return/session-contiguity conventions.
4. **Multiplicity: C7 is its own independent family** — never pooled with C6/C8.
5. **MDE/power: not used as a confirmation criterion** (registered verbatim).
6. **Descriptive persistence (45.7–48.1% vs 11.3%) is CONTEXT ONLY** — barred from determining thresholds, horizons, contrast, or the decision rule. State definition stands as documented: intensity = gross/ADV20 (median-20, shift-1); high-intensity = intensity ≥ 2.0. C7 remains freq-free.
