# I7 — D-2 FINAL EVIDENCE RECORD — 2026-09-14

**Authority:** generated point-in-time record. **Status:** **TERMINAL for the D-2 search.**
**Owner instruction:** record the determination and stop.

> **D-2 REMAINS OPEN. I7 is NOT READY FOR REGISTRATION.** I7 is NOT registered and NOT executed. No I7
> outcome, return, IC or p-value has been inspected or computed at any point. v003, v004 and the I7
> specification are unmodified. No value for σ, power, minimum-N or feasibility is proposed, inferred,
> estimated, imported or implied by this record.

**Supersedes nothing. Closes:** the authoritative-methodology search recorded in
`I7_D2_METHODOLOGY_SEARCH_2026-09-14.md` (commit `64432e1`), whose stopping rule is hereby satisfied.

---

## 1 · THE DETERMINATION (recorded as instructed)

### 1.1 — The 0.60% economic / friction MDE floor IS authoritatively supported for I7

| Source | Standing |
|---|---|
| `HYP-PM-0001_POWER.md` §3–§4 — *"the ex-ante MDE must be economic, not statistical … a **friction floor** … taken from the versioned cost model"*; R2 verdict: *"the friction floor does the work of making the test severe"* | **Ratified methodology**, applied at registration to **HYP-PM-0001** and **HYP-PM-0003** (`HYPOTHESIS_REGISTRY`: *"friction-anchored MDE (round-trip ≈ 0.60% from the cost authority, `engine/exits/costs.py`)"*) |
| `RESEARCH_PROGRAM` §6.1 — **F4**: *"Predicted effect < friction → free kill under the cost model"* | Program-level admissibility gate, applies to every hypothesis |
| `EXPERIMENT_STANDARD` §1 Q2 — **PR-3**: *"Is the predicted effect larger than the friction to capture it?"* | Program-level pre-flight question |
| `engine/exits/costs.py` | The versioned cost authority both precedents cite |

**Applies to I7 without import:** I7 §14 already declares this floor —
`theta_net = theta_primary − 0.006`, *"per program convention"*. Recognising it as the economic MDE
transfers nothing and alters no substantive field.

### 1.2 — No authoritative, genuinely applicable ex-ante assumed σ for the I7 estimand was found

The I7 estimand is `theta_primary` — the mean of a **daily series `m(d)` of cross-sectional LATE−EARLY
differences**. No σ for that quantity exists anywhere in the corpus.

`HYP-PM-0001_POWER` §1's σ (**0.287 %/min**, 1-minute log-return **price** volatility over a
**12,728,445-bar** panel) is a different object at a different grain and is **not** I7's σ.

### 1.3 — No authoritative feasibility gate applicable to the I7 76-session daily cross-sectional estimand was found

No minimum-N rule of any kind exists in the corpus. `HYP-PM-0001_POWER` required none because power was
*abundant* on a 12.7-million-bar panel; that premise does not hold for a series of **at most 76 points**,
and it was not asserted to.

**Corpus evidence that the friction anchor does not self-apply:** `HYP-PM-0003_POWER.md`, written eight
weeks after HYP-PM-0001 registered under it, nonetheless records *"test selection, MDE, and alpha/power
target **remain CRO-open**."* Ratification is **per hypothesis under R5**.

---

## 2 · STANDING PROHIBITIONS (binding from this record)

| # | Prohibition | Status |
|---|---|---|
| 4 | **Do not estimate σ from the frozen I7 cohort.** Constructing `m(d)` requires forward returns — the sealed relation — and a criterion derived from a sample already seen is not ex ante (R5; `HYPOTHESIS_LIFECYCLE` §2.3: *"criteria chosen after the data are seen are not criteria; they are descriptions"*) | **OBSERVED** |
| 5 | **Do not import σ, power, minimum-N or feasibility values by analogy** from HYP-PM-0001, HYP-PM-0003, C7, HYP-PM-0008 or any other hypothesis | **OBSERVED** |
| 6 | **Do not alter I7 §13 or any other substantive I7 specification** | **OBSERVED** — spec unmodified, sha256 `76a965459425e7c1006569d05d8e43fe2e877164e605d0e2d9a9caeb92bba03f` |
| 7 | **Do not register or execute I7** | **OBSERVED** |
| 8 | **Preserve D-1 CLOSED and H₀/H₁ unchanged** | **OBSERVED** — see §3 |
| 9 | **No further corpus search** unless the Owner explicitly reopens D-2 | **BINDING** — the search is closed |

---

## 3 · PRESERVED STATE

**D-1 — ACCEPTED and CLOSED.** The v004 PIT-valid population is I7's registration population, binding by
fingerprint:

| Field | Value |
|---|---|
| Sessions / window | **76** · 2026-04-28 → 2026-09-11 |
| Admissible ticker-days | **61,335** |
| Tickers / bar rows | **868** · **19,793,865** |
| Fingerprint | `e1375264133b42f417d8e74f48a48646197d15b8961e3bdf431d6eebc8784fba` |

**Null — unchanged:**

> **H₀ : `theta_primary ≤ 0`**  ·  **H₁ : `theta_primary > 0`**

One-sided; a negative `theta_primary` falls inside H₀ as a non-rejection, never as a reversed finding.

**All substantive I7 fields unchanged:** mechanism · directional prediction · signal · conditioning ·
estimand · estimator · horizon · threshold · inference · multiplicity · cost convention · kill rule ·
outcome definition.

**Artifacts verified unmodified at the time of this record:**

| Artifact | sha256 |
|---|---|
| v004 cohort | `e1375264133b42f417d8e74f48a48646197d15b8961e3bdf431d6eebc8784fba` |
| v003 cohort (immutable) | `a4a9f7f90a8d3610d5f86163528f7f6fbde0994d8bb14651001bc16cd86ba0e0` |
| I7 specification | `76a965459425e7c1006569d05d8e43fe2e877164e605d0e2d9a9caeb92bba03f` |

`HYPOTHESIS_REGISTRY`, `FAILURE_REGISTRY`, `EXPERIMENT_LEDGER`, `DECISION_LOG`, Dataset B, the v002 freeze
and the production database are **unmodified**. **No family slot consumed.** C3, C7 and every prior valid
test are **untouched and not retested**.

---

## 4 · G1 STANDING

| §5.2 element | Status |
|---|---|
| Mechanism · directional prediction · multiplicity family · refutation sentence · mechanism-blind · data Available (D-002) | ✅ |
| **Null** | ✅ supplied `I7_G1_GAP_CLOSURE_2026-09-14.md` |
| **Scope** | ✅ **D-1 accepted** |
| **Ex-ante criterion incl. effect size** | ⚠️ **PARTIAL** — economic MDE floor authoritatively supported (§1.1); **assumed σ and feasibility gate absent** (§1.2, §1.3) |
| CRO approval | ⏳ follows D-2 |

**A partially-satisfied gate is an unsatisfied gate.** `RESEARCH_PROGRAM` §5.1: G1 *"REFUSES (not defers)"*.

---

# FINAL STATUS

## **D-2 OPEN — I7 NOT READY FOR REGISTRATION**

The authoritative-methodology search is **complete and closed**. Its stopping rule is satisfied: the corpus
supports the economic MDE floor and does **not** supply an applicable assumed σ or feasibility gate, and
neither may be produced without measuring the sealed relation or reasoning by prohibited analogy.

**The remaining decision is the Owner's alone** — supply σ and the feasibility gate ex ante, or rule that no
MDE/power claim is authorized. **This record proposes neither and contains no candidate value.**

**No further work will be undertaken on D-2 unless the Owner explicitly reopens it.**
