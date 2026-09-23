# FWD-PM-VOLEX-SN-001 — D-053 re-measurement: FAILS the gate · REFUSED AT G1

**Date:** 2026-09-23 · **Authority:** D-053 (pre-declared, single run) · **Status:** RECORDED, terminal
**Script:** `remeasure/remeasure_v2.py` sha256 `5caa68b8bdd3d65ec8250d5133ed32fa9bb1d8df695de2ecfff00e015959e80b`
(pinned in commit `f6ebd8f` before execution) · **Output:** `remeasure/RESULT.json` sha256
`96a94c957a2f115d1b4cf5bb52250ce4328aa90bcacda06e0bbce926916eabae`

## 0. Result

Gate (frozen in D-053): pre-2021 formations **t ≥ 2.87 AND mean ≥ +0.10%/mo**.

| window | valid months | mean %/mo | sd | **t** | NW(3) t | P(>0) | net %/mo |
|---|---|---|---|---|---|---|---|
| **pre-2021 (gating)** | 88 | +0.123 | 0.833 | **1.39** | 1.47 | 62.5% | +0.110 |
| full panel | 155 | +0.091 | 0.734 | 1.55 | 1.63 | 59.4% | +0.079 |
| 2021-26 (known data) | 67 | +0.050 | 0.581 | 0.70 | 0.72 | 55.2% | +0.038 |

**Verdict: FAILS.** The mean condition holds, but t = 1.39 is far below 2.87.

Per D-053:
- **HYP-PM-0013 is not registered.** The ID is reserved-retired and never assigned (the D-052 precedent
  for 0011).
- **No family slot is consumed**, and `{V1}` is not opened. The D-053 determination stays on record for
  any future candidate.
- **No re-cut is permitted.**

## 1. What changed between the evidence and this measurement

The 2026-09-19 evidence reported, sector-neutral: pre-2021 **+0.300, t 3.48** and 2021-26 **+0.201,
t 3.31**. Under spec v2 these fall to **+0.123, t 1.39** and **+0.050, t 0.70**. v2 differs from that
evidence in four ways:

1. **ex-ante zero-volume filter only.** The evidence also required a fully traded *holding* month
   (`z_fwd`, look-ahead, F-1).
2. **entry at `close(E)`.** The evidence entered at the formation-day close that computed the signal
   (F-3).
3. **hold to the next formation's entry, with last-traded-close exits.** The evidence used a
   row-based 21-bar hold and dropped name-months without a forward price (F-8).
4. **the `UNLABELLED` bucket is held.** The evidence's `groupby('sector')` silently dropped
   unlabelled names from the held book.

**No attribution among these four was run.** Decomposing them would mean further looks at the same
data, and it cannot change this verdict. Whether to run a descriptive attribution, labelled as such,
is an Owner call.

Descriptive only, never a basis for a re-cut: by ADV tercile, pre-2021, the lowest tercile is
−0.045 (t −0.24), the middle +0.247 (t 1.70), and the top +0.153 (t 1.57).

## 2. Consequences beyond this candidate — for the Owner

1. **The program's "first verified positive edge" is downgraded.** Built ex-ante, sector-neutral
   volatility tail-exclusion is +0.05%/mo (t 0.70) on 2021-26 and not significant on 26 years. The
   claim that the extended panel "clears a multiplicity-corrected bar out-of-sample"
   (`../data_gaps/EXTENDED_PANEL_RESULT_2026-09-19.md` §0/§5) does not survive the removal of its
   look-ahead filter. That document is a point-in-time record and is not edited. This note supersedes
   its conclusion.
2. **FWD-PM-VOLEX-001's backtest reference may carry a similar defect.** Its universe excludes names
   "within ±20 sessions of a suspension window" (`../forward_exclusion/run_forward.py:93-101`). That
   window starts **20 sessions before** `last_normal_date`, which is unknowable at formation. The
   forward test itself is unaffected: `suspension_events` cannot contain a future suspension at run
   time. But its expectation (+0.394%/mo, t 3.74) was very likely computed with this filter. **Not
   investigated here.** The forward test continues unchanged under its frozen protocol.
3. **`BOOK_OVERLAY_POLICY.md` is unchanged by rule** (its §7 review is tied to VOLEX-001's decision
   point). Its evidential basis is weaker than recorded, and the Owner may wish to review it early.
4. **Two mechanical lessons, recorded because both recur:**
   - A tradeability filter written as a symmetric window (`±N`, or "clean in the holding period")
     is look-ahead by default. The forward half must be proven absent, not assumed.
   - A result that holds only with a filter the live system cannot apply is not a result.

## 3. Status changes applied

- `PROTOCOL_DRAFT.md`: status line → REFUSED AT G1. Sections 0–8 are unchanged, and the v2 sha256
  pinned in D-053 is preserved in the file's header.
- `EXPERIMENT_LEDGER.jsonl`: one appended record (`record_type: "pre_registration_remeasurement"`).
- `HYPOTHESIS_REGISTRY.md` and `FAILURE_REGISTRY.md` are **not** touched. The candidate was never
  registered, and `FAILURE_REGISTRY` records only registered hypotheses (pattern-scan precedent,
  2026-09-17).
