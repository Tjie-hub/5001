# FULL HISTORICAL EMPIRICAL AUDIT — IDX ALPHA / P-M PROGRAM — 2026-09-11

**Authority:** point-in-time forensic audit record. Not canonical, not an amendment, not a
registration. Supersedes nothing. Makes no governance decision.
**Mode:** READ-ONLY. No new hypothesis, no exploratory run, no rerun, no specification change, no
parameter tuning, no rescue specification, no artifact overwritten. All database access `mode=ro` +
`PRAGMA query_only`.
**Reviewer:** Claude (Opus 5) · **Branch:** `ops/hardening-2026-07-10` · **Snapshot:** 2026-09-11 ~11:00 WIB
**Companion:** `FULL_HISTORICAL_EMPIRICAL_AUDIT_LEDGER_2026-09-11.json`
**Predecessors:** `CLAUDE_INDEPENDENT_REVIEW_G1_C7_2026-09-11.md`, `CLAUDE_G1_FORENSIC_AUDIT_2026-09-11.md`

**Evidence convention.** `[measured]` = my own read-only computation, reproducible, **predictor-side
only**. Across this entire audit I computed **no forward return, no θ, no t-statistic, no p-value and
no verdict**. Where I state that a repair would not change an outcome, the arithmetic is done on
**already-published p-values**, by hand, and shown. Nothing was re-executed.

---

## 0 · EXECUTIVE SUMMARY — THE CENTRAL FINDING

The C2 defect is **not isolated**. It is the fourth instance of one recurring defect class, and the
other three sit inside **already-closed, registry-recorded results**:

> **A signed broker-flow "net" quantity is an exchange accounting identity. Total buy value ≡ total
> sell value per stock per day. Any predictor of the form `net / gross` over *all* brokers is
> therefore ≈ 0 by construction — exactly 0 at full population, and ~0.2% of gross under top-25
> truncation. Four registered primary endpoints in this program are built on that quantity.**

| Test | Registered primary predictor | Status of that predictor | Recorded outcome | Correct outcome |
|---|---|---|---|---|
| **BFI-001** | `BFI_broad = NV/GV`, all brokers | degenerate | "not confirmed" (t=0.047) | **INVALID — data failure** |
| **HYP-PM-0003** | `sign(SUM(lot))`, all brokers | degenerate | **FAILED F2**, registry-recorded | **INVALID — data failure** |
| **G1 C2** | `sign(for_net) ≠ sign(loc_net)` | tautological | FAIL | **INVALID — specification failure** |
| **Family map G** | true-net disagreement | degenerate | **correctly BLOCKED** | ✓ the one time it was caught |

The program caught this defect once (family map §3, family G, 2026-09-10) and then executed two
further tests on the same quantity — one of them the day *before* the discovery (HYP-PM-0003,
2026-09-09) and one the day *after* (G1 C2, 2026-09-11).

**Consequence for the ledger:** `FAILURE_REGISTRY.md` records N=3 failures, all coded **F2 ·
Prediction failure**, and its own note diagnoses a program-level *"horizon/friction mismatch"*
pattern. At least one of those three (FAIL-PM-0003) is **mis-coded** — it is a data failure, not a
prediction failure. The institution's failure-mode self-diagnostic is currently reading a
measurement artifact as a market fact.

**Second-order finding:** there are **two disjoint failure registries** (§J-2) and **two disjoint
hypothesis registers** (§J-3), and the program's own reference implementation, **NR7 Breakout, was
falsified by its own gatekeeper and failure registry on 2026-09-03 while remaining `SHADOW` in the
Edge Registry** (§7).

---

## 1 · INVENTORY — HOW IT WAS BUILT

Constructed from artifacts, not from the task list. Sources swept: `HYPOTHESIS_REGISTRY.md`,
`FAILURE_REGISTRY.md`, `roadmap/DECISION_LOG.md` (to D-047), `research_programs/P-M/**`,
`research_programs/P-A/**`, `data/research.db` (6 research-owned tables), `data/walkforward.db`
(82 tables), `registry/edge_registry.yaml`, `data/reports/**`, and `/home/tjiesar/ZCodeProject/**`
(7 program directories).

**Items the task list did not name, found in the artifacts: BFI-001/BROKER-001, LIT-001, LIT-002,
H1, H6, HLIQ, EXP-PA-0001, S2-PM-0004, the six gatekeeper decisions, the Liquidity Sweep and
`distribution` falsifications, and the 9-strategy `wf_edge` scan.** Twenty empirical objects in
total.

---

## 2 · HYP-PM-0001 / EXP-PM-0001

**A · Identity.** M1.1 inventory-imbalance mean reversion (I5), tested vs M2.1 (I7) · registered
2026-07-17T07:15:03Z (sha `540c2d52…`) · executed **2026-07-18T01:09:37Z** ·
`P-M/experiments/EXP-PM-0001/{results.json,MANIFEST.md,run_exp_pm_0001.py,execution.log}` ·
dataset `stockbit_flow_bars` 2025-07-07→2026-07-17, 12,956,970 rows / 867 tickers, 12,642,224
analysis rows, **233 formation days** · primary endpoint signed reversal at **k=15** ·
friction 0.60% RT · family `{I5,I6,I7,I12}`, 1st member.

**B · Registration integrity — REGISTERED.** Registered ~18h before execution; registration sha
recorded inside the result artifact. Executed spec matches. No post-hoc parameter change found.

**C · Data integrity.** `stockbit_flow_bars` is a *vendor aggregate* feed, not broker-level — so it
is **structurally immune to the net≡0 identity** (vendor buy/sell volumes are aggressor-side and do
not balance). Verified independently: the family map §3 notes the vendor feed shows "buy ≠ sell
asymmetry (e.g. BBCA 44.4M vs 63.9M shares)". **This is the one flow test in the program whose
predictor is sound by construction.**

**D · Feature integrity.** OFI from vendor bars; signed reversal `−sign(OFI)·rev`. Non-degenerate.

**E · Inference.** k=15: mean −7.84e-06, se 2.23e-05, **t = −0.352**, CI [−5.15e-05, +3.59e-05].
233 daily observations. Point estimate ≈ 0 with the *predicted* sign absent. Not a borderline miss.

**F · Cost.** Net −0.6008% against a friction-anchored MDE of 0.60% RT. Registered in advance.

**G · Provenance — RECONSTRUCTABLE.** Registration sha, run script, execution log and results all
preserved in the experiment bundle; `data/research.db::research_runs` carries the run spine.

**H · Classification: VALID → NOT CONFIRMED.** (Recorded FAILED F2 — correctly coded.)

**I · Challenge.** Strongest case against: it is an **in-sample** test on a single ~1-year window
with 233 daily observations, and the registry itself notes a "history-maturity gate (validation
in-sample until the ~1yr flow history lengthens)". A null from a short in-sample window is weak
evidence. **But** the point estimate is essentially zero with the wrong sign, so the refutation is
informative rather than vacuous. **No repair required; no rescue available or sought.**

---

## 3 · HYP-PM-0003 / EXP-PM-0003 — **INVALID (DATA FAILURE)**

**A · Identity.** M2.1 adverse-selection permanence (I7) · registered 2026-09-09T09:22:00Z
(sha `a2db9204…`) · executed **2026-09-09T09:44:17Z — 22 minutes later** ·
`P-M/experiments/EXP-PM-0003/{results.json,run_exp_pm_0003.py,FAILURE_ENTRY.md,CLOSE_OUT_REPORT.md}` ·
dataset **Dataset A** (`broker_flow`, frozen, fingerprint `329b22e4…`), 2025-01-02→2026-08-27,
1,222,713 rows / 79 tickers, 20,604 observations (20,509 after the non-zero filter) ·
primary endpoint `signed_continuation_k = sign(net_flow_t) · fwd_ret_k` at **k=7** ·
test `bootstrap_ci` (10,000 draws, seed 20260711) · family `{I5,I6,I7,I12}`, 2nd member.

**B · Registration integrity — REGISTERED, but see §I.** Registered 22 minutes before execution.
That is not disqualifying on its own, but it is the narrowest registration-to-execution gap in the
program and leaves no window for independent pre-execution review.

**C · DATA INTEGRITY — FAILS.** The registered predictor is, verbatim from
`run_exp_pm_0003.py:8` and line 163:

```python
# net_flow(ticker,date) = SUM(lot)  -- already-signed, no BUY-minus-SELL subtraction
net = bf.groupby(["ticker","trade_date"], as_index=False)["lot"].sum()
net = net[net.net_flow != 0]
signed_cont = np.sign(merged.net_flow) * merged.fwd_ret
```

`lot` is signed in production `broker_flow` **[measured]**: BUY 1,607,813 rows (1,581,321 positive),
SELL 1,441,424 rows (1,385,719 negative). So `SUM(lot)` per ticker-day is total buy lots minus total
sell lots — **the exchange accounting identity**. Measured over the exact EXP-PM-0003 window
(2025-01-02→2026-08-27, 97,762 ticker-days) **[measured]**:

```
SUM(lot) exactly zero                        : 66,575 = 68.10% of ticker-days
|SUM(lot)| / SUM(|lot|)   p50 = 0.000000   p90 = 0.002084   p99 = 0.014920   max = 0.333333
|net|/gross < 1%                             : 97.86% of ticker-days
```

**The registered predictor is undefined on 68% of ticker-days and, where defined, is the sign of a
residue worth ~0.2% of the day's turnover.** That residue is not directional flow — it is *which
brokers happened to fall inside or outside the 25-broker disclosure cap*. Corroborated independently
by the program's own family map §3: *"broker_flow per-ticker net is structurally ~0
(P(|nf|≥0.2)=0.0000; p95 |nf|=0.001)"* and *"HYP-PM-0003-style net-flow formulations are not only
falsified but largely **unmeasurable** on this table."* — written 2026-09-10, **one day after
EXP-PM-0003 executed**.

Secondary data defect on record: memory/audit trail records **RAJA stock-split contamination of the
k=7 estimate**; Dataset A has no quarantine mechanism (that was introduced only for Dataset B).

**D · Feature integrity — DEGENERATE.** `sign()` of a near-zero quantity. The `net_flow != 0` filter
silently conditions the sample on the 32% of ticker-days where truncation residue happened to be
non-zero — a non-random, disclosure-driven selection.

**E · Inference.** k=7 point +0.000538, bootstrap CI [−0.000656, +0.001768]. The estimator is sound;
the input is not. Power: `HYP-PM-0003_POWER.md` §8 reports a naive MDE ladder of **0.168% / 0.533% /
1.684%** at N_eff = 20,604 / 2,060 / 206, and concludes *"power was 'abundant', friction was [the
binding constraint]"*. The later V13 audit found the ρ-deflation heuristic *"fundamentally
inapplicable to a sign-conditioned estimator"*, and the identifiability audit put the realistic
requirement at **~54.6% annualized gross alpha** at k=7 — i.e. the test **could not have refuted any
economically plausible effect**. Under rule R2 ("corroboration from a test that could not have
refuted carries zero evidential weight"), the symmetric reading applies: this null carries near-zero
weight even before the predictor defect.

**F · Cost.** Net −0.546% at k=7 against the 0.60% floor. Registered in advance; not manipulated.

**G · Provenance — RECONSTRUCTABLE.** Registration sha, run script, dataset fingerprint, execution
log all preserved.

**H · Classification: INVALID — DATA FAILURE.** Minimum supporting evidence: the predictor is zero
on 68.10% of ticker-days and <1% of gross on 97.86% [measured]; the program's own family map
declares the quantity "unmeasurable" on this table.

**I · CHALLENGE AND REPAIR.**

*Strongest case against the existing conclusion:* `FAIL-PM-0003` is recorded in the **append-only,
immutable** `FAILURE_REGISTRY.md` as **F2 · Prediction failure** — an assertion that the market did
not behave as M2.1 predicted. That assertion is unsupported: M2.1 was never tested. The registry
currently shows N=3, all F2, and draws a program-level inference from that distribution. One of the
three is a measurement artifact.

*Can the defect be repaired without changing the estimand?* **No, not on Dataset A.** The estimand
is "signed broker net flow predicts continuation". On a top-25-truncated table the signed net flow
of the *whole* market is not observable — it lives in the undisclosed tail. No reconstruction of
Dataset A recovers it.

*Is a repair possible at all?* Only by **changing the instrument**, which changes the test. On
Dataset B (full population) the quantity is **exactly** zero, so it is worse, not better. The only
observable signed net in the estate is the vendor aggregate (`stockbit_flow`) — which is a different
instrument, and is what HYP-PM-0002 (still DRAFT) targets.

*Verdict:* **no legitimate repair of EXP-PM-0003 exists.** Reclassification is the only correct
action, and it is an owner decision because the Failure Registry is immutable and can only be
corrected by a new dated superseding entry.

*Explicitly rejected as rescues:* re-running on Dataset B (the predictor is identically zero there);
substituting the vendor net (different instrument, different hypothesis); dropping the `net_flow != 0`
filter (does not create information); weighting by |net| (post-hoc).

---

## 4 · BFI-001 / BROKER-001 — **PRIMARY INVALID (DATA FAILURE); SECONDARIES VALID → NOT CONFIRMED**

**A · Identity.** "Broker Flow Imbalance baseline (IDX80 PIT, bfi001)" · registered in
`data/research.db::hypotheses` as `BROKER-001`, status **PREREGISTERED**, proposed 2026-09-03 10:58:54,
prereg_ref `/home/tjiesar/ZCodeProject/bfi001_broker_flow/00_PREREGISTRATION_FROZEN.md` ·
executed 2026-09-03 · artifacts `90_results.json`, `20_primary_spread_series.csv`,
`21_family_results.csv`, `25_execution_run_log_2026-09-03.txt` · broker_flow 2,955,547 rows span
2025-01-02→2026-09-03 · **350 formation dates**, median 74 names/day ·
primary **`BFI_broad(i,t) = NV/GV`** (prereg §66, all brokers, all investor types) at k=5 ·
**family of 14 prespecified cells, Holm α=0.05**.

**B · Registration integrity — REGISTERED.** Prereg sha `91c0eb9a4a42630f…` recorded in the result
JSON and **independently re-verified by me against the file today: exact match.** A separate
`11_prereg_hash_2026-09-03.txt` exists. This is the best-documented registration in the program.

**C/D · DATA + FEATURE INTEGRITY — PRIMARY FAILS.** `NV/GV` over *all* brokers is the same
accounting identity as §3. Consistent with that:

| Cell | Predictor | mean bp | NW t | p | Holm p | Degenerate? |
|---|---|---|---|---|---|---|
| **PRIMARY_bfi_k5** | BFI_broad | +1.36 | **+0.047** | 0.962 | 1.000 | **YES** |
| F1_bfi_k1 / k2 / k10 / k20 | BFI_broad | −15.3 / −31.2 / +25.5 / +45.9 | −1.34 / −1.73 / +0.50 / +0.56 | .18/.083/.62/.57 | 1.0/.747/1.0/1.0 | **YES (same predictor)** |
| F3_lots_k5 | BFI_lots = NVL/GVL | **NaN** | NaN | NaN | — | **YES** |
| F3_n2_k5 | — | −162.4 | **NaN** | NaN | — | did not compute |
| F2_asing / lokal / pemerintah k5 | per-slice NV/GV | +6.3 / **+52.9** / +12.2 | 0.37 / **2.434** / 0.69 | .71/**.015**/.49 | 1.0/.164/1.0 | No |
| F3_n1_k5 | — | −28.5 | −1.02 | .31 | 1.0 | No |
| F4_binf_k5 | informed-subset NV/GV | +2.0 | 0.086 | .93 | 1.0 | No |
| **F4_conc_k5** | concentration | **−56.9** | **−2.648** | **.008** | **.097** | No |
| **F4_breadth_k5** | breadth | **+46.1** | **+2.409** | **.016** | **.164** | No |

A t-statistic of **+0.047** on the primary is precisely the signature of a predictor with no
variation. The per-investor-type splits are *not* degenerate (individual slices do not balance),
which is why F2_lokal produced a real statistic — and why the sub-slices, not the aggregate, carry
whatever information exists.

**E · INFERENCE — FAMILY CONTAMINATION.** Holm was applied across a prespecified family of 14 in
which **six cells (PRIMARY + four F1 horizons + F3_lots) are the same degenerate predictor** and two
returned NaN. A degenerate cell can never reject, so including it only inflates the multiplicity
denominator against the live cells. **This is a conservative defect — and per critical rule 6 it
still invalidates the registered estimand**, because the registered family is not the family that
was scientifically at risk.

*Does removing them rescue anything? No — computed by hand from the published p-values, no rerun:*
sorted live p-values are F4_conc 0.008, F2_lokal 0.0149, F4_breadth 0.016, F1_k2 0.083…
With the degenerate cells removed (m = 8), Holm step-down gives F4_conc → 8 × 0.008 = **0.064**, then
F2_lokal → max(0.064, 7 × 0.0149) = **0.104**. **No cell reaches 0.05 under any admissible family
size.** The correction is real; the outcome does not change.

**R3 label-permutation anomaly — unexplained, flagged.** `R3_label_permutation` reports
`observed_binf_spread_nw_t = 0.086` against `perm_binf_spread_nw_t_mean = **1.377**` over 100
permutations. Under a correctly specified permutation null the mean NW-t should sit near **zero**,
not +1.38. Either the permutation does not break the structure it is meant to break, or the NW-t on
this daily-spread estimator is not centred at zero. **This matters beyond BFI-001: the same
estimator family (NW(k) on a daily spread series) is the registered inference for G1 C2/C3 and for
the proposed C7.** I am not asserting miscalibration — I am recording an unexplained diagnostic that
the program has not addressed and that bears on every test using this estimator.

**F · Cost.** Gross spread +1.36 bp/step; turnover ~0.73 one-way per step; **net at 10 bp
= −14.6 bp/step, at 15 bp = −22.0, at 25 bp = −36.7.** Fourth independent instance of the
friction-floor pattern.

**G · Provenance — RECONSTRUCTABLE (best in program).** Prereg hash verified today; execution log,
per-cell CSVs, results JSON, and dataset fingerprint all preserved. Not under this repository's git,
but intact and self-consistent.

**H · Classification.** **PRIMARY: INVALID — data failure.** **F1 horizons + F3_lots: INVALID —
same predictor.** **F2/F3_n1/F4 cells: VALID → NOT CONFIRMED.**

**I · CHALLENGE AND REPAIR.**

*Strongest case against the existing use of this test:* the family map and the BFI-002 memo carry
**F4_conc's t = −2.65 forward as C6's supporting prior** — *"CONC event-like … BFI-001 prior
t=−2.65"*, *"C6 credibility: Medium (prior −2.65)"* — **without disclosing that its registered Holm
p is 0.097 and it did not survive its own family correction.** That is a Holm-failed secondary being
promoted to "prior evidence" for a new candidate. The same applies to F4_breadth (t = +2.41, Holm
0.164), which is the **same measurement surface as G1 C3** — and C3 subsequently returned null
(§6.4). Two tests of breadth, one nominal positive that failed multiplicity and one clean null.

*Repair without changing the estimand?* For the **primary: no** — same reasoning as §3.
For the **secondaries: no repair needed**; they are valid and not confirmed. Re-reporting them with
the corrected family size is a *reporting* fix, not a re-test, and it changes no verdict (shown
above).

*Rejected as rescues:* citing F4_conc's raw p = 0.008 without its Holm p; treating any secondary as
a standalone finding; re-cutting the family after seeing results.

---

## 5 · LIT-001 and LIT-002 (OFI reversal line)

### 5.1 LIT-001 — VALID → NOT CONFIRMED

Preregistered (`00_PREREGISTRATION_FROZEN.md`), executed; verdict artifact
`70_LIT001_FINAL_VERDICT.md`. Sample 2025-01-02→2026-08-28, **383 formation days, 56,735 stock-days**,
universe top-500-by-ADV20 ∩ price≥100. Predictor `OFI = (BuyVol−SellVol)/(BuyVol+SellVol)` from
**`stockbit_flow` vendor aggregate** — again *not* degenerate (aggressor-side, does not balance).

**Primary: REJECTED.** −3.59 bp/day, t = −0.51 (NW −0.54), gross Sharpe −0.41, cumulative −16.0%.
Point estimate has the **wrong sign** (continuation, not reversal). Break-even cost −1.8 bp/side —
"no gross profit for costs to consume". Look-ahead audit documented clean.

**Exemplary discipline, and I want it on the record:** the 2-day cell showed **+49.9 bp/step,
t = +2.74** — the single largest nominal effect anywhere in the program — and the verdict document
itself records it as *"the lone positive cell … family-corrected p ≈ 0.04–0.10 and inconsistent with
its neighbors … recorded as a lead (FUTURE EXPERIMENT — NOT TESTED), not as a finding."* That is
exactly correct handling.

**Incidental finding, correctly not claimed:** Fama–MacBeth shows a significant **continuation**
coefficient (+0.00068 per unit rank, t = +3.84, NW +3.60) surviving every prespecified control
individually. This is the opposite sign to the registered hypothesis and therefore **exploratory**,
not confirmatory — but it is a nominally strong, replicated-across-controls effect on a
non-degenerate predictor, and it is the closest thing in the program to a live lead (§L).

### 5.2 LIT-002 — UNRESOLVABLE (insufficient evidence)

Preregistered (`10_PREREGISTRATION_FROZEN.md`, sha `c2b03399…`, **`prereg_hash_verified: true`**),
executed 2026-08-30. Frozen OOS rule: **formation dates t > 2026-08-28**; required **201 evaluable
steps** for 80% power at the LIT-001 effect.

**Result: `evaluable_oos_steps = 0` vs gate 201 → `gate_pass: false` → verdict INCONCLUSIVE**, and —
critically — `outcome_statistics_computed: false`. Per prereg §I.2 **no OFI-conditioned return,
spread or IC was computed for any date; the series CSV contains headers only.** This is the single
best piece of governance discipline in the whole corpus: the coverage gate fired, and the analyst
did not look.

**Challenge — a real design defect, in the *permissive-to-nobody* direction.** The frozen OOS
boundary (`t > 2026-08-28`) equals the dataset's own maximum date (`flow_max_date: 2026-08-28`,
`ohlcv_max_date: 2026-08-28`). **The test was structurally impossible at the moment it was frozen** —
zero OOS days could exist. This is a specification/scheduling defect, not a data defect.

**Repair: YES, and it is the cleanest repair available anywhere in this audit.** Re-execute the
**identical frozen specification** once ≥201 evaluable OOS steps have accumulated (~10 months of
sessions past 2026-08-28, i.e. roughly mid-2027). It requires **no new registration** (the spec is
frozen and hash-verified), the original data are sufficient *plus* elapsed time, and the result
would be **confirmatory**, not exploratory. Label it **REPRODUCTION / deferred execution of
LIT-002**, not a new experiment.

---

## 6 · G1 RUN 1 (BFI-002) — C1a, C1b, C2, C3

Fully audited in `CLAUDE_G1_FORENSIC_AUDIT_2026-09-11.md`; summarised here for the ledger with one
new cross-test observation.

**A · Identity.** Replacement registration `G1_REGISTRATION_v1_2026-09-11.md` (dated 2026-09-11,
original `BROKER_FLOW_PREREGISTRATION.md` NOT FOUND) · executed 2026-09-11T02:31:18Z · Dataset B
frozen store (`21661f03…`, FINGERPRINT_v2 `1a68ab1c…`), 2025-01-02→2026-08-27, 1,518,727 flow rows,
28,624 panel rows, 375 formation dates · k ∈ {3,5,10}, primary k=5 · Holm over retained {C2,C3}.

**6.1 C1a — INVALID (implementation failure).** Executed despite a registered withdrawal that states
it "never executes … no numbers" (`g1_harness.py:821`, unconditional). Full `theta_t` (152/148/142)
and `detail` (190/185/179) preserved; θ recoverable from the un-nulled `theta_net_cost_floor`.
Contained: legs are a **median of 1 name**, 97% singleton bucket-cells, 148 of 375 dates. Not
reportable. **No repair — the breach cannot be undone, only quarantined.**

**6.2 C1b — WITHDRAWN.** Never implemented; zero cells exist. The report's "all six C1a/C1b cells"
is a reporting error in the safe direction.

**6.3 C2 — INVALID (specification failure).** Two independent defects [measured]:
(i) net ≡ 0 on **100.00%** of 30,624 ticker-days ⇒ `sign(for_net) ≠ sign(loc_net)` is tautological;
(ii) the 15% gate was swapped from the descriptive generator's `|net| > 0.15·gross`
(`12_discovery_structures.py:122`) to gross-participation ≥ 0.15 (`g1_harness.py:478-480`), taking
incidence from **26.6% → 98.5%**. Supporting evidence (30.2%) is **Dataset A**
(`discovery_structures.json`, n = 103,389, production `broker_flow`). **No repair — see §3.I.**

**6.4 C3 — VALID → NOT CONFIRMED (bounded).** Count-based, cap-robust, identity-free; healthy legs
(median 14 broad v 16 narrow over 329 dates) [measured]; incidence 18.9%/20.5% [measured]. Holm
p = 1.0, signs +/+/−, −54 bp net.

> **NEW CROSS-TEST OBSERVATION.** C3's surface was already tested once: **BFI-001's `F4_breadth_k5`
> returned +46.1 bp, t = +2.409, raw p = 0.016, Holm p = 0.164** on the same broker-flow corpus
> (Dataset A, 350 dates), five months earlier. So breadth has now been measured twice: nominally
> positive but multiplicity-failed in BFI-001, and null in G1 C3. Neither is a confirmation, but
> **G1 C3 was not the first test of breadth**, and the BFI-002 memo does not disclose the prior. For
> multiplicity purposes C3 is a **second look at a previously-tested surface**, not a fresh one.

**6.5 G1 overall — PARTIAL, not a clean FAIL.** One valid non-confirmation, one invalid arm, two
withdrawn (one executed in breach).

---

## 7 · NR7 BREAKOUT / PROGRAM P0 — **INVALID AS AN EDGE CLAIM; FALSIFIED**

**A · Identity.** The v3 Edge Pipeline reference implementation. `registry/edge_registry.yaml`:
v1 `SUPERSEDED` (approved 2026-07-04), **v2 `SHADOW`** (demoted 2026-08-19 per D-029 — the Evidence
Model's C3/E5+X3 capital bar "which this entry's evidence never satisfied").

**B/E · Gatekeeper record — `data/research.db::gate_decisions`, 6 rows, all `NR7 Breakout`:**

| decided_at | final_state | failing stage |
|---|---|---|
| 2026-07-12 04:18:49 · 05:04:20 · 05:25:39 · 07:13:41 | **REJECT** ×4 | `walk_forward` |
| 2026-07-14 13:51:55 | **REJECT** | `walk_forward` |
| 2026-09-03 12:37:41 | **REJECT** | `walk_forward` |

**The gatekeeper has issued zero PROMOTE decisions, ever.** `gate_evidence` (48 rows) shows the
2026-07-12 decision passing `min_sample`, `multiplicity` (raw p 0.00355, BH 0.0249, family_size 7)
and `psr` (0.996) — and then failing `walk_forward`.

**C/D · Falsification, 2026-09-03** (`data/reports/nr7_falsification_2026-09-03.md`, and
`data/research.db::failure_registry` id `9681dbdc`):

> *"NR7 Breakout: falsified as a strategy-level edge. Persisted wf_edge positive expectancy
> (+1.64pp, 54 cells) is a **selection artifact of the n≥20 aggregation floor** — pooled over ALL
> 858 tickers producing NR7 OOS trades, expectancy is **−0.18%/trade** (6,183 trades, bootstrap 95%
> CI [−0.37, +0.02] includes 0)."*

Supporting detail from the report: positive in **only 1 of 5 years** (2025 +0.95pp; 2022 −1.23,
2023 −1.70, 2024 −0.24, 2026 YTD −0.88); losses concentrate in illiquid names (low tercile −0.72pp);
outlier-dependent (dropping the top 10 trades moves expectancy to −0.25pp); and the multiple-testing
context table shows NR7's positive-cell share of **79.6% vs a 23.1% mean across 9 strategies** —
which is exactly the signature of the n≥20 floor, not of an edge.

**H · Classification: INVALID as an edge claim — implementation/selection failure.** (The six
gatekeeper decisions themselves are VALID → NOT CONFIRMED; they did their job.)

**I · Challenge.** *The most consequential unresolved contradiction in the corpus:* `CLAUDE.md` and
the governance corpus describe **P0 (NR7) as "delivered — the reference implementation proving the
framework produces validated knowledge."** The framework's own gatekeeper rejected it six times and
its own failure registry falsified it on 2026-09-03. The Edge Registry still carries it as `SHADOW`,
not `RETIRED`. **No repair exists — the falsification is sound and well-evidenced.** What is
required is that the registry status and the corpus narrative be brought into line with the
program's own evidence. That is a governance act, not a research act.

---

## 8 · OTHER EXECUTED TESTS

### 8.1 H6 foreign flow — **UNREGISTERED / EXPLORATORY — the only surviving nominal positive**

`/home/tjiesar/ZCodeProject/h6_foreign_flow/{results.json,H6_BACKTEST_REPORT.md,H6_INVESTIGATION_AND_PREREGISTRATION.md,sim_h6.py}`.
Executed 2026-08-29T14:27:38. Primary: **mean signed CAR10 = +0.756%, t_cluster = 2.771**,
n = 1,514 events over 350 anchor dates, CI95 [+0.221%, +1.291%], hit rate 52.4%. Market-adjusted vs
equal-weight U1, clustered by anchor date. Decomposition: n_buy = 553, mean CAR = **−1.02%**;
n_sell = 961, mean CAR = **+0.60%** — i.e. **extreme foreign-broker flow events revert**.

**Challenge — three reasons this is not a finding:**
1. **Holdout fails.** in-sample t = 2.176 (n=1,063); **holdout t = 1.713 (n=451), CI95
   [−0.129%, +1.915%] includes zero.** The confirmation half did not confirm.
2. **Not in any corpus registry.** Absent from `HYPOTHESIS_REGISTRY.md`, `FAILURE_REGISTRY.md`,
   `DECISION_LOG.md` and `data/research.db::hypotheses`. It consumed no multiplicity slot and was
   never gated.
3. **Friction.** +0.756% gross over a 10-day hold against the estate's 0.60% RT floor leaves ~+0.16%
   — inside the noise, and the holdout point estimate cannot support it.

**Classification: UNREGISTERED / EXPLORATORY.** **Not a rescue of anything and not a result.** It is
the one lead in the program with a non-degenerate predictor, a positive point estimate, and a
mechanism story — and it belongs in §K-7 as a *candidate for future registration*, nowhere else.

### 8.2 H1 foreign flow — UNREGISTERED / EXPLORATORY (null)
`h1_foreign_flow/results.json`: every coefficient |t| < 1.6 across models A/B/C/BC/D
(z_flow5 t = −0.465 in A, −0.479 in D full); ΔR² of adding flow to controls = 0.0095;
spread_5m1 t = −1.088; ic_flow t = −1.456. n = 369 dates. Null, and unregistered.

### 8.3 HLIQ liquidity shock — VALID → NOT CONFIRMED (with an inference caveat)
`hliq_liquidity_shock/12_HLIQ_RESULTS.json`, prereg sha `a87b5721…`, dataset sha `30d2c287…` —
both recorded. Primary n = 80, mean −1.785%, t = −1.847, p_one = 0.956 (wrong tail).
Placebo clean (pre-event T−20..T−11 t = −0.060). **Inference caveat:** cluster-robust SEs computed
on **14 clusters**. Cluster-robust inference with G = 14 is materially biased and requires a
small-sample correction (G−1 df at minimum, ideally wild-cluster bootstrap). The reported CI is
likely too narrow. Direction of the defect is **permissive**, so it does not rescue the null — but
it is a real inference defect and the same class of issue should be checked in EXP-PA-0001, which
does use `df = G − 1` (§8.4).

### 8.4 HYP-PA-0001 / EXP-PA-0001 — VALID → NOT CONFIRMED
`P-A/experiments/EXP-PA-0001/results.json`, registration sha prefix `3692e69a`, executed
2026-08-19T07:09:22Z. 210 raw CSV rows → 192 distinct → **180 measured** (82 ADD / 98 DELETE),
12 excluded and individually reported with reasons. k_reversal = 5td, estimation window 230td,
gap 20td, IHSG market model, friction 0.60% RT. `decision: {test1_pass: false, test2_pass: false,
verdict: REFUTED}`. **Good practice noted:** `resolved_spec_ambiguities` documents six
implementation choices explicitly, and `cr1_dof` uses `df = G − 1` — the correction HLIQ omitted.
Recorded FAILED F2; correctly coded.

### 8.5 S2-PM-0004 · I3 open-integrity census — VALID → CONFIRMED (the stop rule)
`P-M/S2-PM-0004_G1_RESULT.md`, 2026-08-25. Governed by `S2-PM-0003_G1_PREREGISTRATION.md`,
sha `de2b7288…` — **verified EXACT MATCH before execution**, both artifacts byte-identical to the
2026-08-21 freeze. Rule F2: `open == prev_close` rate in the liquid stratum ≥ 50% → observed
**51.94%** → rule fires → stop, no G-2, no universe restriction.
This is a **data-integrity census, not a return test**. Its design worked exactly as specified.
Classify as VALID → CONFIRMED (the integrity defect it was built to detect was detected). Note the
third distinct meaning of "G1/G-1" in the corpus (§J-5).

### 8.6 Liquidity Sweep — VALID → NOT CONFIRMED (falsified)
`data/research.db::failure_registry` id `4c2f5932`, 2026-09-03: pooled OOS expectancy negative under
**both** registered exit rules — unbounded baseline −1.01%/trade (33,122 trades), hold_days=10
parity rule −1.00%/trade (40,539 trades); positive-cell share falls 21.4% → 19.0% under parity.
Diagnosis on record: *"Per-ticker positive tail inside a negative cross-ticker mean = multiplicity
artifact."* Same selection-floor mechanism as NR7.

### 8.7 `distribution` (SELL/detector path) — VALID → NOT CONFIRMED
`failure_registry` id `4e833d8b`: **forward** shadow cohort, 2,133 closed trades, −0.05%/trade,
negative in every month Jun–Sep 2026. The **largest genuinely forward (non-backtest) sample in the
system**, and it is negative. Evidence class K6 (forward) — the highest-ceiling class in the
Evidence Model — and it refutes.

### 8.8 The 9-strategy `wf_edge` scan — UNREGISTERED / EXPLORATORY
From the NR7 falsification report's multiple-testing table: NR7 +1.64pp (54 cells) is the **only**
positive; momentum −0.69, vwap_reversion −0.86, ORB −0.95, Liquidity Sweep −0.98, vol_weighted
−1.06, Volume Profile POC −1.13, conservative −1.13, Inside Bar Breakout −2.31. Nine strategies
scanned, no registered family, no multiplicity control. **This scan is the multiplicity context for
every NR7 claim** and should be cited whenever NR7's cell-level numbers are.

### 8.9 TOWR deep-dive — UNREGISTERED / EXPLORATORY
`ZCODE_TOWR_BREAKOUT_PULLBACK_DEEP_DIVE_2026-09-10.md`, family map §8. 1,625 analogue events, 677
CONT / 948 FAIL. Self-classified *"No new family … INTERESTING BUT UNPROVEN"*, and the
"same-agent persistence through retracement" hypothesis **tested NEGATIVE** (identity overlap/flip
features show zero discrimination). **Correctly handled** — but note it is a historical **analogue**
analysis, and its intensity profile (breakout 4.20/2.05 FAIL vs 2.97/1.24 CONT) is now cited as
supporting C7. Analogue evidence is K3-class observational at best; it cannot support a predictive
claim (§J-8).

### 8.10 Family map descriptive passes A–P — UNREGISTERED / EXPLORATORY
`ZCODE_ALPHA_DISCOVERY_FAMILY_MAP_2026-09-10.md`, 16 families, all on **Dataset A**. Descriptive
only, correctly labelled. **The portability problem is systemic**: every prevalence figure in this
map (C2's 30.2%, C7's 18.11%, C8's 5.2%, C3's 23%, K's 9.1%) was measured on top-25-truncated
Dataset A and none has been re-measured on Dataset B. Two have now been checked and both moved
materially: C2 26.6%→98.5% as implemented (§6.3), **C7 18.11%→12.29%** [measured].

### 8.11 HYP-PM-0002 — DRAFT, never executed. Consumes no slot. Correctly recorded.

---

## 9 · J · CROSS-TEST CONSISTENCY

**J-1 · The net ≡ 0 identity invalidates four registered primaries across three programs.** §0.
The program discovered the fact on 2026-09-10 (family map §3), blocked family G correctly, and did
not retro-apply it to BFI-001 (2026-09-03) or HYP-PM-0003 (2026-09-09), nor prospectively to G1 C2
(2026-09-11). **Prior conclusions requiring downgrade: FAIL-PM-0003 (F2 → data failure);
BFI-001 primary (not confirmed → invalid).**

**J-2 · Two disjoint Failure Registries.** `docs/research_programs/FAILURE_REGISTRY.md` holds
{FAIL-PM-0001, FAIL-PM-0003, FAIL-PA-0001}; `data/research.db::failure_registry` holds
{Liquidity Sweep, `distribution`, NR7 Breakout}. **Zero overlap.** Six recorded failures, two
registries, neither complete, both described as append-only and immutable. The markdown registry's
program-level inference ("all three are F2 … horizon/friction mismatch") is drawn from half the
evidence — and would change if NR7's selection-artifact failure and the two production
falsifications were in the same table.

**J-3 · Two disjoint hypothesis registers.** `HYPOTHESIS_REGISTRY.md` holds HYP-PM-0001,
HYP-PM-0003, HYP-PA-0001. `data/research.db::hypotheses` holds exactly one row — **BROKER-001
(BFI-001), status PREREGISTERED** — which appears nowhere in the markdown registry and consumed no
P-M family slot. `hypothesis_links` is **empty (0 rows)**, so no hypothesis↔evidence trace exists in
the DB at all, despite Phase E being recorded as delivered.

**J-4 · Dataset A vs Dataset B portability is unvalidated program-wide.** §8.10. Every C-candidate
threshold in flight was calibrated on A and will execute on B.

**J-5 · "G1" has four distinct meanings** — the institutional Gate (G1–G4, TAXONOMY standard, and
the sense used in `HYPOTHESIS_REGISTRY.md` line 3 "counted … from G1/REGISTERED"); the BFI-002
experiment; `S2-PM-0004`'s I3 preregistration gate; and `regime_config.yaml`'s per-hypothesis
statistical floor referenced in D-047 ("a trade-level, per-hypothesis/G1 statistical floor").

**J-6 · C-family vs I-family taxonomy was never reconciled.** The declared P-M family is
`{I5, I6, I7, I12}` (inventory / illiquidity / adverse-selection / capacity-shielded). C2, C3, C6,
C7, C8 have **never been mapped onto any I-entry** in any document. BFI-001 and G1 both ran against
the P-M corpus outside the declared family entirely.

**J-7 · The same surface tested under different names.** Breadth: BFI-001 `F4_breadth_k5`
(t = +2.41, Holm 0.164) and G1 `C3` (null) — same measurement, two tests, prior undisclosed.
Concentration: BFI-001 `F4_conc_k5` (t = −2.65, Holm 0.097) is the sole basis for C6.
Foreign flow: H1, H6, BFI-001 `F2_asing_k5` **and** the executed form of G1 C2 (§6.3) are four looks
at foreign-broker flow.

**J-8 · Descriptive/analogue evidence treated as predictive evidence.** C7's ranking rests on
P(next-day high | high) = 45.7–48.1% vs 11.3% base — **volume clustering, a property of the
predictor**. The TOWR analogue profile is cited as support. Neither is outcome-axis evidence. Under
`EVIDENCE_MODEL` U10 / ADR-L1-003 this cannot support a return claim.

**J-9 · Five independent deaths against the same 0.60% friction floor.** HYP-PM-0001 (−0.60%),
HYP-PM-0003 (−0.55%), BFI-001 (−14.6 bp/step at 10 bp costs), G1 C2/C3 (−44 to −67 bp), LIT-001
(break-even cost −1.8 bp/side — no gross profit at all). The Failure Registry names this pattern.
It is the single most reproducible empirical fact the program has produced.

**J-10 · An unexplained inference diagnostic spans the estimator family.** BFI-001's R3 permutation
null is centred at t = +1.377, not 0 (§4.E). The same NW-on-daily-spread estimator is used by G1 and
proposed for C7.

---

## 10 · K · MASTER LEDGER

| # | Test | Registration | Data | Implementation | Inference | Provenance | Final classification | Legitimate repair? |
|---|---|---|---|---|---|---|---|---|
| 1 | HYP-PM-0001 / EXP-PM-0001 | REGISTERED | OK | OK | OK | RECONSTRUCTABLE | **VALID → NOT CONFIRMED** | n/a |
| 2 | HYP-PM-0003 / EXP-PM-0003 | REGISTERED (22 min) | **FAIL** | OK | undermined | RECONSTRUCTABLE | **INVALID — data failure** | **No** |
| 3 | BFI-001 primary (`BFI_broad`) | REGISTERED (hash ✓) | **FAIL** | OK | family inflated | RECONSTRUCTABLE | **INVALID — data failure** | **No** |
| 4 | BFI-001 F1 k1/k2/k10/k20 | REGISTERED | **FAIL** | OK | — | RECONSTRUCTABLE | **INVALID — data failure** | No |
| 5 | BFI-001 F3_lots | REGISTERED | **FAIL** | NaN | — | RECONSTRUCTABLE | **INVALID — data failure** | No |
| 6 | BFI-001 F2/F3_n1/F4 (7 cells) | REGISTERED | OK | OK | family inflated (conservative) | RECONSTRUCTABLE | **VALID → NOT CONFIRMED** | reporting fix only |
| 7 | G1 C1a | WITHDRAWN | OK | **BREACH** | n/a | **BROKEN** | **INVALID — implementation failure** | **No** |
| 8 | G1 C1b | WITHDRAWN | n/a | never built | n/a | **BROKEN** | **WITHDRAWN** | n/a |
| 9 | G1 C2 | AMBIGUOUS | **FAIL** | **FAIL** | n/a | **BROKEN** | **INVALID — specification failure** | **No** |
| 10 | G1 C3 | AMENDED (vs memo) | OK | window deviation | OK | **BROKEN** | **VALID → NOT CONFIRMED** (bounded) | n/a |
| 11 | LIT-001 | REGISTERED (frozen) | OK | OK | OK | RECONSTRUCTABLE | **VALID → NOT CONFIRMED** | n/a |
| 12 | LIT-002 | REGISTERED (hash ✓) | coverage 0 | OK | not computed | RECONSTRUCTABLE | **UNRESOLVABLE — insufficient evidence** | **YES — deferred REPRODUCTION** |
| 13 | H1 foreign flow | UNREGISTERED | OK | OK | OK | RECONSTRUCTABLE | **UNREGISTERED / EXPLORATORY** (null) | n/a |
| 14 | H6 foreign flow | UNREGISTERED (in corpus) | OK | OK | cluster-by-date | RECONSTRUCTABLE | **UNREGISTERED / EXPLORATORY** (nominal +, holdout fails) | new registration only |
| 15 | HLIQ | REGISTERED (hash ✓) | OK | OK | **G=14 caveat** | RECONSTRUCTABLE | **VALID → NOT CONFIRMED** | n/a |
| 16 | HYP-PA-0001 / EXP-PA-0001 | REGISTERED | OK | OK | OK (df=G−1) | RECONSTRUCTABLE | **VALID → NOT CONFIRMED** | n/a |
| 17 | S2-PM-0004 (I3 census) | REGISTERED (hash exact ✓) | OK | OK | n/a (census) | **IMMUTABLE** | **VALID → CONFIRMED** (stop rule fired) | n/a |
| 18 | NR7 / P0 (edge claim) | gatekeeper-registered | OK | **selection floor** | REJECT ×6 | RECONSTRUCTABLE | **INVALID — implementation failure** (falsified) | **No** |
| 19 | Liquidity Sweep | production-era | OK | OK | pooled | RECONSTRUCTABLE | **VALID → NOT CONFIRMED** | n/a |
| 20 | `distribution` (SELL) | production-era | OK | OK | forward K6 | RECONSTRUCTABLE | **VALID → NOT CONFIRMED** | n/a |
| 21 | 9-strategy wf_edge scan | UNREGISTERED | OK | selection floor | no multiplicity | RECONSTRUCTABLE | **UNREGISTERED / EXPLORATORY** | n/a |
| 22 | TOWR deep-dive | UNREGISTERED | OK | analogue | descriptive | RECONSTRUCTABLE | **UNREGISTERED / EXPLORATORY** | n/a |
| 23 | Family map A–P | UNREGISTERED | Dataset A only | descriptive | none | RECONSTRUCTABLE | **UNREGISTERED / EXPLORATORY** | re-measure on B |

### K-1 · Tests that remain valid
HYP-PM-0001 · BFI-001's seven non-degenerate cells · G1 C3 (bounded) · LIT-001 · HLIQ (with the
G=14 caveat) · EXP-PA-0001 · S2-PM-0004 · Liquidity Sweep · `distribution` · the six NR7 gatekeeper
decisions. **All are null or refuting. Not one is a confirmation of an edge.**

### K-2 · Tests that are invalid
HYP-PM-0003 (data) · BFI-001 primary + 4 F1 horizons + F3_lots (data) · G1 C2 (specification) ·
G1 C1a (implementation) · NR7 as an edge claim (selection).

### K-3 · Merely exploratory
H1 · H6 · TOWR · family map A–P · the 9-strategy scan · LIT-001's 2-day pocket and its FM
continuation coefficient · all C6/C7/C8 descriptive evidence.

### K-4 · Requiring owner decisions
HYP-PM-0003 reclassification (immutable registry) · BFI-001 primary reclassification and family-slot
question · G1 verdict amendment · C1a redaction · NR7 Edge Registry status vs falsification ·
registry reconciliation (J-2, J-3) · the C-family ↔ I-family mapping (J-6).

### K-5 · Can legitimately be reproduced
**LIT-002 only** — identical frozen spec, once ≥201 evaluable OOS steps exist (~mid-2027). Label
**REPRODUCTION**. No new registration needed; would be **confirmatory**.
*(Secondarily: BFI-001's Holm recomputation over the non-degenerate family is a paper exercise, not
a rerun — already done by hand in §4.E, outcome unchanged.)*

### K-6 · Must never be rerun
G1 C2 · G1 C1a/C1b · EXP-PM-0003 · BFI-001's `BFI_broad` cells — all four rest on a predictor that
is zero by accounting identity. Re-running any of them produces a different number from the same
non-information. G1 C3 must not be rerun either, under the registered no-rescue rule.

### K-7 · New hypotheses that may be worth registering later
**Only these three are directly implied by an identified defect or result.** Each would be a
**new, separately registered hypothesis consuming its own slot** — none is a repair of an old test.

1. **Own-side conduit imbalance.** *Implied by:* the C2 defect. Because market-wide net ≡ 0, the
   *only* non-degenerate ownership construct is each group's imbalance **relative to its own side's
   gross**, not to total gross. A genuinely different estimand — must not be presented as C2 repaired.
2. **Vendor-aggregate signed net flow.** *Implied by:* HYP-PM-0003's defect + LIT-001's significant
   FM **continuation** coefficient (t = +3.84, NW +3.60, survives every prespecified control). The
   vendor feed is the only signed net observable in the estate, and the evidence points to
   continuation, not reversal — the opposite of both HYP-PM-0001 and HYP-PM-0003. This is the
   strongest outcome-axis lead in the program. *(Overlaps HYP-PM-0002's instrument — resolve before
   registering.)*
3. **Extreme foreign-flow event reversal (H6 formalisation).** *Implied by:* H6's +0.756% / t = 2.77
   with a failing holdout. Would need a genuine out-of-sample window, a cost model, and a
   multiplicity slot. Register or discard — it must not keep circulating as informal support.

**Explicitly NOT admitted as hypotheses:** BFI-001's F4_conc (a Holm-failed secondary), F4_breadth
(same, and its surface already retested null), LIT-001's 2-day pocket (already correctly held as a
lead pending LIT-002), and any C1a-derived construct.

---

## 11 · L · PROGRAM-LEVEL VERDICT

**What empirical evidence is still trustworthy?**
Eight results, and they are all negative or null: HYP-PM-0001, LIT-001, HLIQ, EXP-PA-0001, G1 C3,
Liquidity Sweep, `distribution`, and BFI-001's seven non-degenerate cells. Plus one clean positive
of a different kind — **S2-PM-0004**, where a preregistered integrity census correctly fired its own
stop rule on a hash-verified spec. The program's most trustworthy output is its **methodology**, not
its findings.

**What must be discarded?**
Every result resting on all-broker `net/gross`: **HYP-PM-0003, BFI-001's primary and its four F1
horizons and F3_lots, and G1 C2.** Plus **G1 C1a** (executed in breach) and **NR7's +1.64pp
wf_edge expectancy** (a selection artifact of the n≥20 floor, on the program's own analysis).

**Is HYP-PM-0003 genuinely failed after the audit?**
**No.** It is **INVALID — data failure**, not F2 · prediction failure. The predictor is zero on
68.10% of ticker-days and under 1% of gross on 97.86% [measured]. M2.1 / I7 was never tested. It
currently occupies a slot in an immutable registry under the wrong failure mode, and the registry's
own program-level diagnosis is drawn partly from that mis-coding.

**Is G1 genuinely failed, or split/invalidated?**
**Split.** C3 is a valid non-confirmation (bounded — the registered statistic diverged from the memo
and the executable NF-control clause was skipped). C2 is invalid. C1a is invalid and in breach. C1b
never ran. A family-level "FAIL" asserts the family was tested; half of it was not.

**Is there any legitimate surviving positive signal?**
**No confirmed one — and this is unambiguous.** Nothing in the program has ever passed a registered
primary endpoint with multiplicity control. Three nominal positives survive as *leads only*:
LIT-001's FM continuation coefficient (t = +3.84, wrong sign for its own hypothesis, therefore
exploratory); H6's event reversal (t = 2.77 overall, **holdout CI includes zero**, unregistered);
and BFI-001's F4_conc (t = −2.65, **Holm p = 0.097 — failed its own correction**). The gatekeeper
has issued **zero PROMOTE decisions in its entire history**.

**Single highest-value next empirical test.**
**None, yet — and that is the answer.** The highest-value *action* is not a test: it is re-measuring
every Dataset-A-derived prevalence on Dataset B before any candidate executes (§8.10), because two
of two checked so far moved materially, and one of those two silently voided a registered test.
That is cheap, consumes no slot, and is the precondition for every C-candidate.

When a test does run, the ranking on outcome-axis evidence is:
**(1) vendor-aggregate signed net flow (K-7.2)** — the only lead with a significant, control-robust,
non-degenerate outcome-axis coefficient; **(2) C6/concentration**, provided its prior is restated
honestly as Holm p = 0.097 rather than t = −2.65; **(3) C7**, and only on an execution/liquidity
outcome. Against a 0.60% round-trip floor that has now killed five independent mechanisms (J-9), any
new *return* test at swing horizons should state its friction-anchored MDE up front and be declared
underpowered before it runs, not after.

**Governance / data / provenance blocker that must be closed first.**
**One, and it is not the family question.** It is the **net ≡ 0 identity**: it must be written into
the Semantic Register as a hard prohibition — *no candidate may use an all-broker net/gross quantity
as a signal, control, or state condition, on either dataset* — and applied **retroactively** to
HYP-PM-0003 and BFI-001. Until that is recorded, the defect has already recurred four times in nine
days and there is nothing in the process to stop a fifth.

The **multiplicity family determination** (C-family ↔ I-family, J-6) is the immediate blocker for
C7/C6/C8 specifically. The **provenance repair** for G1 (untracked directory, executed code
destroyed by a concurrent writer) is the immediate blocker for trusting any future run in that
directory.

---

*No code modified. No data modified. No test rerun. No new empirical hypothesis executed. No
specification changed. No parameter tuned. No rescue specification created. No artifact overwritten.
No registry or decision-log entry created or edited. No commits. No governance decision made. All
`[measured]` values are read-only predictor-side computations; no forward return, θ, t-statistic or
p-value was computed anywhere in this audit. Where an outcome is stated to be unchanged by a repair,
the arithmetic was performed by hand on already-published p-values and is shown in the text.*
