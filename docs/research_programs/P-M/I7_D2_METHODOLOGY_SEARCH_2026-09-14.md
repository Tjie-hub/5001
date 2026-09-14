# I7 — D-2 AUTHORITATIVE-METHODOLOGY SEARCH — 2026-09-14

**Authority:** generated point-in-time record. **Scope:** determines whether the corpus contains a
genuinely applicable authoritative methodology supplying I7's ex-ante MDE / assumed σ / feasibility gate,
per the Owner's D-2 instruction.

> **Nothing was invented, inferred, reverse-engineered or transferred.** No MDE, σ, power target, minimum
> sample size, feasibility threshold or stopping rule is proposed. No I7 outcome, return, IC or p-value was
> inspected or computed. v003, v004 and the I7 specification are unmodified. **I7 is NOT registered and NOT
> executed.** D-1 remains ACCEPTED and CLOSED; the null remains H₀ : θ ≤ 0 against H₁ : θ > 0.

---

# DETERMINATION

## **No genuinely applicable authoritative methodology exists. D-2 remains OPEN.**

The corpus authorizes **one of the three components** §13 requires, and supplies **neither of the other
two**. Partial authorization does not satisfy the gate, and completing it would require exactly the acts the
Owner prohibited.

---

## 1 · What the search covered

`RESEARCH_PROTOCOL` · `EXPERIMENT_STANDARD` · `RESEARCH_QUALITY_STANDARD` · `PEER_REVIEW_STANDARD` ·
`HYPOTHESIS_LIFECYCLE` · `MARKET_INEFFICIENCY_TAXONOMY` · `WORKED_EXAMPLE_END_TO_END` ·
`RESEARCH_PROGRAM` §5–§9 · `HYP-PM-0001_POWER.md` · `HYP-PM-0002_POWER.md` · `HYP-PM-0003_POWER.md` ·
`C7_REGISTRATION_v1` · `HYPOTHESIS_REGISTRY` · `engine/exits/costs.py`.

## 2 · What IS authoritative — the friction anchor

**Source.** `HYP-PM-0001_POWER.md` §3–§4, ratified at registration for **two** hypotheses
(`HYPOTHESIS_REGISTRY`: HYP-PM-0001 and HYP-PM-0003 each *"registered under a **friction-anchored MDE**
(round-trip ≈ **0.60%** from the cost authority, `engine/exits/costs.py`)"*).

**Rule, verbatim:**

> *"**Therefore the ex-ante MDE must be economic, not statistical.** The registered threshold should be a
> **friction floor** — the reversal must exceed round-trip cost (net-of-cost > 0) to be an edge — taken from
> the versioned cost model, **not** the … power floor."*
>
> **R2 verdict:** *"the **friction floor does the work of making the test severe**."*

**Program-level support.** `RESEARCH_PROGRAM` §6.1 (*"Predicted effect < friction → **F4** — free kill under
the cost model"*) and `EXPERIMENT_STANDARD` §1 Question 2 / **PR-3** (*"Is the predicted effect larger than
the friction to capture it?"*) apply to every hypothesis, not to one.

**It applies to I7 without import.** I7's specification **already declares this floor** — §14:
`theta_net = theta_primary − 0.006`, *"per program convention"*. Recognising it as the economic MDE
transfers nothing and changes no substantive field. `engine/exits/costs.py` exists and is the versioned
authority both precedents cite.

> **So the effect-size half of §13 has an authoritative, already-declared anchor: the 0.60% round-trip
> friction floor.**

## 3 · What is NOT authoritative — and why the gate still fails

### 3.1 No authorized σ for I7's estimand

`HYP-PM-0001_POWER` §1 measured σ as a **custody-clean nuisance parameter**: *"median 1-min log-return
volatility … from `flow_bars.price`"*, **σ₁ₘᵢₙ = 0.287%/min** over a **12,728,445-bar** panel — a property
of the price series, computed without touching the hypothesis relation.

**That quantity is not I7's.** I7's estimand is `theta_primary` = the mean of a **daily series** `m(d)` of
cross-sectional LATE−EARLY **differences**. Its standard deviation is a different object at a different
grain. Obtaining it would require constructing `m(d)`, which requires forward returns — i.e. **touching the
sealed relation and using the 76-session sample**. Both are expressly forbidden by this decision and by
R5/§2.3 (*"criteria chosen after the data are seen are not criteria; they are descriptions"*).

**No σ for I7 exists anywhere in the corpus, and none may lawfully be produced before registration.**

### 3.2 No authorized feasibility gate

I7 §13 requires *"a **pre-execution feasibility gate** [specifying] a **minimum count of qualifying
event-days per state**, with shortfall terminating the hypothesis as **RETIRED — UNPOWERED**."*

**No source in the corpus supplies a minimum-N rule of any kind.** `HYP-PM-0001_POWER` needed none — it
concluded power was *abundant* and therefore not binding. That conclusion rested on a **12.7-million-bar**
panel. I7's daily series has **at most 76 points**. The premise that made friction binding for HYP-PM-0001
**does not transfer**, and testing whether it holds for I7 would require §3.1's forbidden computation.

### 3.3 The corpus prescribes the requirement, not a procedure

`EXPERIMENT_STANDARD` §1 Q1 (*"Run the power/MDE analysis (**R2**)"*, rule **EX-1**: *"a hard stop, and it
is the one you will want to skip"*) and `RESEARCH_PROTOCOL` §5.2 (*"POWER / MDE (R2): could this test have
failed?"*) both **mandate the analysis and prescribe no method and no values**.

### 3.4 The corpus's own evidence that this does not auto-apply

**`HYP-PM-0003_POWER.md` left it open rather than inheriting.** Despite HYP-PM-0001 having been registered
under the friction anchor eight weeks earlier, HYP-PM-0003's power document records: *"test selection, MDE,
and alpha/power target **remain CRO-open**."*

> **The second hypothesis in the same family, on the same program, did not treat the first's MDE as
> transferable.** That is direct evidence the friction anchor is ratified **per hypothesis under R5**, not
> established as a self-applying general methodology. A third hypothesis may not claim otherwise.

### 3.5 The C7 precedent is a decision, not a methodology

`C7_REGISTRATION_v1` §3 item 5 records the Owner ruling *"No MDE or formal power claim is authorized unless
already supported by an existing authoritative methodology." None exists.* → *"MDE/power not used as a
confirmation criterion."* **That is an Owner decision about C7**, not a method that derives values. Per this
D-2 instruction it is **not substituted**, and it is reported here only because it is the corpus's most
recent ruling on the identical question.

---

## 4 · Why this is not a weakening, and not a rescue

The G1 requirement is **not** reduced. §13 demands three things — an ex-ante MDE, a stated assumed σ, and a
feasibility gate. One has an authoritative anchor; two do not. **A partially-satisfied gate is an
unsatisfied gate**, and `RESEARCH_PROGRAM` §5.1 is explicit that G1 *"REFUSES (not defers)"*.

Three specific temptations were available and were declined:

| Available move | Why declined |
|---|---|
| Adopt the friction floor as "the MDE" and declare §13 satisfied | Leaves σ and the feasibility gate empty. Would satisfy the gate's wording while defeating it |
| Measure σ from the v004 cohort's price series as a "nuisance parameter" | Would require constructing `m(d)` from forward returns — touching the sealed relation and the 76-session sample. Forbidden by this decision, and by R5 |
| Apply the C7 ruling by analogy | An Owner decision about a different hypothesis, not a methodology. Expressly excluded |

---

## 5 · Answer to the five reporting questions

The Owner's five-part report is required only *"if an authoritative methodology does exist."* It does not,
so the questions are answered negatively and specifically:

| # | Question | Answer |
|---|---|---|
| 1 | Exact source | **Partial only** — `HYP-PM-0001_POWER.md` §3–§4 supplies a friction anchor; no source supplies σ or a feasibility gate |
| 2 | Exact applicable rule | *MDE := round-trip friction from the versioned cost model* — covers effect size only |
| 3 | Why it applies to I7 | It does apply, and is **already declared** in I7 §14 (`θ_net = θ − 0.006`) — but it is one of three required components |
| 4 | Exact values authorized | **Δ = 0.60% round-trip** (`engine/exits/costs.py`). **σ: none. Feasibility threshold: none. Power target: none. Minimum sample size: none.** |
| 5 | Ex-ante and non-altering? | The friction anchor is ex ante and alters nothing. **But the package it belongs to cannot be completed without σ, and no σ may lawfully be produced pre-registration.** |

---

## 6 · Unchanged

| Item | State |
|---|---|
| D-1 | **ACCEPTED, CLOSED** — v004, fingerprint `e1375264…fba`, 76 sessions / 61,335 ticker-days |
| Null | **H₀ : `theta_primary ≤ 0`** · **H₁ : `theta_primary > 0`** — unchanged |
| All substantive I7 fields | **unchanged** — mechanism, prediction, signal, conditioning, estimand, estimator, horizon, threshold, inference, multiplicity, cost convention, kill rule, outcome |
| v004 / v003 / I7 spec | **unmodified** — `e1375264…`, `a4a9f7f9…`, `76a96545…` |
| Registries, DECISION_LOG, Dataset B, v002, production | **unmodified** — no family slot consumed |
| C3 / C7 and prior valid tests | **untouched, not retested** |

---

# FINAL STATUS

## **D-2 REMAINS OPEN — I7 NOT READY FOR REGISTRATION**

**What exists:** an authoritative, already-declared economic MDE anchor — the **0.60% round-trip friction
floor** from the versioned cost authority, ratified at registration for two prior P-M hypotheses and present
in I7 §14 today.

**What does not exist:** any authorized **assumed σ** for I7's daily-series estimand, and any authorized
**feasibility gate** (minimum qualifying event-days per state). Neither can be produced before registration
without measuring the sealed relation or reverse-engineering from the 76-session cohort.

**The remaining decision is unchanged and is the Owner's**: supply σ and the feasibility gate ex ante, or
rule — as was ruled for C7 — that no MDE/power claim is authorized. **This document proposes neither.**
