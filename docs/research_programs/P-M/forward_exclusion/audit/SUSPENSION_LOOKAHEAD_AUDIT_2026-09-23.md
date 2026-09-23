# FWD-PM-VOLEX-001 — suspension look-ahead audit of the backtest reference

**Date:** 2026-09-23 · **Authority:** diagnostic, Owner-requested · **Status:** RECORDED
**Script:** `suspension_lookahead_audit.py` · **Output:** `suspension_lookahead_audit_RESULT.json`

**Scope.** This audit examines the **in-sample backtest reference** quoted in `../PROTOCOL.md` §3
(+0.394%/mo, t 3.74). It does not touch the forward ledger, the frozen protocol, or the decision rule;
§3's PASS/FAIL thresholds are absolute numbers and do not move. This is not a re-run of the forward
primary, which `PROTOCOL.md` §4 forbids.

## 0. Answer

**The look-ahead is real. The effect survives it, but the honest expectation is materially lower.**

`run_forward.py:93-101` masks each suspension from `last_normal_date − 20` sessions to
`resume_date + 20`. The pre-suspension half is unknowable at formation. With it removed (arm B), the
effect is still positive and significant. The inflation is small under the backtest's 21-phase
convention, but **large under the calendar-month cadence the live test actually uses:**

| arm | suspension mask | 21-phase median (reference convention) | **month-end cadence (live convention)** |
|---|---|---|---|
| A · as coded | [i0−20, i1+20] | +0.380 %/mo, t 3.57, P>0 73% | +0.357, t 3.29, n 47 |
| **B · ex-ante** | **[i0, i1+20]** | **+0.371, t 3.19, P>0 70%** | **+0.298, t 2.59, n 48** |
| C · no mask | none | +0.375, t 3.20, P>0 68% | +0.306, t 2.65, n 49 |

- **Reconstruction check.** The script asserts that arm A's eligibility mask equals the runner's own
  `eligible` frame exactly. Arm A reproduces the recorded reference within data drift: +0.386/t 3.67 on
  the raw calendar and +0.380/t 3.57 on complete sessions, against the recorded +0.394/t 3.74.
- **Exit convention** (the runner's drop-if-missing versus last traded close) makes no difference once
  partial sessions are excluded: 5 names are missing at exit in total.

## 1. What this does to VOLEX-001's decision rule

`PROTOCOL.md` §3's power table was built on the reference (+0.394, sd ≈ 0.68). Its decision at
n = 24: PASS requires t > 1.71 and P(>0) ≥ 60%; FAIL is mean < +0.15. Normal approximation:

| expectation used | monthly sd | P(t > 1.71) at n=24 | P(mean < 0.15 ⇒ FAIL) |
|---|---|---|---|
| protocol reference (+0.394) | 0.71 | 0.85 | 0.05 |
| as coded, month-end (+0.357) | 0.74 | 0.74 | 0.09 |
| **ex-ante, month-end (+0.298)** | **0.80** | **0.55** | **0.18** |

**If the true effect equals the honest ex-ante estimate, the frozen test passes only ~55% of the time
and wrongly fails ~18% of the time.** The protocol described it as "powered". It is not, at the
expectation it should have used. This is an **observation, not an amendment**: the rule stays frozen.
Changing it now would be a spec change, which §4 forbids. The Owner should read a future
INCONCLUSIVE or FAIL with this in mind.

## 2. Two live-runner hazards found (forward test, not backtest)

1. **Exits can land on partial sessions.** `score()` indexes the raw session list, and its `dropna()`
   silently removes every name without a close on the exit date. The panel has had such sessions:
   2026-07-08, 07-09, 07-24, 09-16, 09-18 and 09-21 currently fail the runner's own 95% completeness
   guard. On the raw calendar, 794 names went missing at exit in this audit's first pass; excluding
   partial sessions brings that to 5.
   - The guard protects the **formation** date only, not the exit.
   - Once written, an outcome is never re-scored. A partial exit day would permanently freeze a
     degraded outcome into the ledger.
   - First exposure: the 2026-09-15 formation's exit, about 21 sessions after 09-16.
2. **The suspension mask can leak into the forward test, in a small way.** The runner reads
   `suspension_events` at run time. A suspension beginning between the formation date and the run
   date masks the formation date (through the i0−20 half), which is look-ahead of a few sessions.
   This exposure is small, because runs happen within days of formation. But it is not zero.

Fixing either needs a dated `deviation_log.md` entry, or an amendment. **Nothing has been changed**;
both are Owner calls. Hazard 1 is the urgent one, and it is time-bound to the first maturity (≈ mid-Oct).

## 3. Contrast with the sector-neutral result the same day

The pooled top-200 construction survives honest ex-ante construction: t 2.6–3.2. The sector-neutral
all-liquid construction did not: `../../forward_volex/REMEASUREMENT_RESULT_2026-09-23.md`, 2021-26
t 0.70. The two differ in universe (top-200 by ADV versus everything above the floor), sector
neutrality, the zero-volume filter, entry (`close(t+1)` in both, but a 21-session versus a
to-next-formation hold), and data span. **No attribution was run.** It would be another look, and it
is not needed to answer this audit's question.

## 4. Record corrections

- "First verified positive edge" (program memory, 2026-09-16): the **pooled top-200** construction
  survives this audit at a lower level (ex-ante month-end +0.30%/mo, t 2.6). The **sector-neutral**
  construction does not survive its own audit. The two should not be quoted interchangeably.
- `PROTOCOL.md` §3 reference: read it as **+0.30%/mo (ex-ante, month-end)**, not +0.394. The document
  itself is frozen and is not edited.
