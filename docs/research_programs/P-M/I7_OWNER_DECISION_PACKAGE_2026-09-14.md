# I7 — OWNER DECISION PACKAGE — 2026-09-14

**Authority:** generated point-in-time record. **Type:** decision-support artifact. **Not methodology design.**

> **I7 is NOT registered and NOT executed.** No specification was modified. v003 and v004 are untouched.
> No hypothesis was created. **No I7 outcome, return, IC, p-value, or trading result has been inspected at
> any point**, and nothing in this memo argues from I7 performance — because no performance exists to argue
> from.

**Verified state carried into this memo** (independently re-derived, commit `efd1a6e`):
76 sessions · 61,335 admissible ticker-days · 868 tickers · 19,793,865 bar rows ·
v004 `e1375264…fba` · v003 `a4a9f7f9…0e0` immutable · 27/27 tests · 8/8 validation gates.

---

# D-1 — POPULATION SUBSTITUTION

The I7 specification (`BRANCH_A_NEW_MECHANISM_AUDIT_2026-09-14.md` §7, §12) describes a population of
**~277 admitted sessions over 2025-01-02 → 2026-04-27**. The PIT-valid cohort is **76 sessions beginning
2026-04-28**. The two intervals are **disjoint**: not one session of the described population survives.

## 1 · What changes if the Owner accepts

| # | Change |
|---|---|
| 1 | **The registered population becomes the v004 cohort**, bound **by fingerprint** — `I7_V004_ADMISSIBLE_v1.sqlite`, sha256 `e1375264133b42f417d8e74f48a48646197d15b8961e3bdf431d6eebc8784fba` — not by name. (`RESEARCH_OBJECT_SCHEMA` l.233: *"Experiments bind the fingerprint, not the name — otherwise a silent upstream revision retroactively changes what a completed experiment tested, which is F7 arriving through the back door."*) |
| 2 | **Window: 2026-04-28 → 2026-09-11**, superseding §7's 2025-01-02 → 2026-04-27. |
| 3 | **Scale: 76 sessions / 61,335 ticker-days**, superseding §12's "~277 observations". |
| 4 | **The exclusion set becomes X3–X6 ∪ E-PIT-1..4**, with X1 and X2 recorded as *subsumed* (both regions end before the 2026-04-28 boundary — a date fact, asserted in code and validated by gate 7). |
| 5 | **§7 and §12 are superseded as descriptions.** They are descriptive coverage statements, not registered parameters; replacing stale figures is not a methodology change. |
| 6 | **The PIT limitation and the B4 (PPK/board) limitation are declared at registration**, not discovered afterwards. |

## 2 · What remains unchanged

**Every substantive field.** Nothing in the hypothesis moves:

| Field | §ref | Status |
|---|---|---|
| Mechanism — informed execution back-loads within the session (M2/I7) | §1 | **unchanged** |
| Signal — OPEN 09:00–09:59, LATE 14:50–15:49; `nbuy(LATE)/daily_net ≥ 0.50` | §5 | **unchanged** |
| Conditioning — `daily_net > 0` | §5 | **unchanged** |
| Estimand — daily LATE−EARLY series, NW lag 5, two-sided | §9 | **unchanged** |
| Horizon — k = 1; outcome `close(t+2)/close(t+1)−1`; entry reference `close(t+1)` | §10 | **unchanged** |
| Multiplicity — single cell, Holm = identity; family P-M `{I5,I6,I7,I12}`, slot #3 | §14 | **unchanged** |
| Kill rule | §16 | **unchanged** |
| Cost convention — `θ_net = θ − 0.006`, reported sensitivity only | §14 | **unchanged** |
| No-rescue rule | §18 | **unchanged** |

**The direction of the change is against the hypothesis, not for it.** The substitution reduces the sample
to roughly 28% of what the specification anticipated. It makes the test *harder to resolve*, not easier to
pass. It is not a loosening of any criterion, and no threshold, state definition, estimator or decision rule
moves in either direction.

## 3 · Amendment, or population decision?

**Neither an amendment nor a rescue is available or required, because I7 is not registered.**

> `RESEARCH_PROGRAM` §4: *"**G1 is a one-way door** (HL-2). **Before it — states `DRAFT` / `REFINING` —
> refinement is unlimited and free.** After it — `REGISTERED` onward — the claim is frozen; any edit is
> R7.4 (threshold migration) or R15 (rescue) and **deletes the evidence retroactively**."*
>
> `HYPOTHESIS_LIFECYCLE` HL-2: *"G1 is a one-way door. **Before it, refine freely — nothing has been risked,
> so nothing can be corrupted.**"*

I7 sits in **DRAFT**. Nothing has been risked; no family slot is consumed; no evidence exists to corrupt.
The population is therefore **declared at G1**, as one of the six §5.2 intake elements — it is not an edit
to a frozen record.

**Therefore:** acceptance is an **explicit population / exclusion decision recorded at registration**, not a
preregistration amendment. No superseding DECISION_LOG entry is required for the substitution itself,
though the Owner may elect to record one.

**The asymmetry that makes this decision consequential is the opposite one:** the substitution is free *now*
and impossible *later*. Once G1 closes, the same change would be R7.4/R15 and would delete the evidence
retroactively.

---

# D-2 — MDE / ASSUMED σ / FEASIBILITY GATE

## 1 · The requirement, quoted exactly

`BRANCH_A_NEW_MECHANISM_AUDIT_2026-09-14.md` **§13**:

> *"At registration the MDE must be declared **ex ante from a stated assumed σ** (the pattern used in
> `HYP-PM-0008_SPEC` §11), and a **pre-execution feasibility gate** must specify a minimum count of
> qualifying event-days per state, with shortfall terminating the hypothesis as **RETIRED — UNPOWERED** (a
> non-failure). **No MDE number is asserted here.**"*

Same document **§G.2**:

> *"**An ex-ante MDE with a declared assumed σ**, plus a **pre-execution feasibility gate** (minimum
> qualifying event-days per state) whose shortfall yields **RETIRED — UNPOWERED**, not FAILED."*

## 2 · Every place sample adequacy is required

| # | Location | Requirement |
|---|---|---|
| 1 | I7 spec **§13** | ex-ante MDE from a stated assumed σ; feasibility gate with a minimum event-day count per state; shortfall ⇒ RETIRED — UNPOWERED |
| 2 | I7 spec **§G.2** | the same, restated as a registration precondition |
| 3 | I7 spec **§12** | *"The estimand is a **daily series of ~277 observations**"* — a descriptive expectation, now superseded by 76 sessions |
| 4 | `RESEARCH_PROGRAM` **§6.1** (admissibility, binary, non-negotiable) | *"The test **could not fail** (no power / MDE) → **R2** — a test that cannot fail produces no evidence"* — **auto-rejection** at G1 |
| 5 | `RESEARCH_PROGRAM` **§6.1** | *"Predicted effect **< friction** → **F4** — free kill under the cost model"* |
| 6 | `RESEARCH_PROGRAM` **§5.1** intake gate | the G1 packet must carry *"**power/MDE showing the test CAN fail (R2)**"* or *"G1 **REFUSES** (not defers)"* |
| 7 | `RESEARCH_PROGRAM` **§9.2** | pre-registered thresholds are *"declared **per hypothesis at registration** (ex ante, **R5**)"* |

## 3 · Current status

> **No MDE, no assumed σ, no minimum event-day count, no power target, no sample-adequacy threshold and no
> stopping rule is specified anywhere for I7.** §13 states the requirement and then explicitly declines to
> satisfy it: *"No MDE number is asserted here."*

Consequence, stated neutrally: under §6.1 item 4 the candidate is **auto-rejected at G1** while this field
is empty, and per §5.1 the intake gate **refuses rather than defers**. The field must be supplied by the
Owner before registration can proceed.

## 4 · This is an OWNER DECISION

**No value is proposed, recommended, preferred, or implied by this memo.** Nothing here narrows the choice.
The two precedent families below are reported **as source evidence only**, in chronological order, with no
comparison, ranking, or suitability assessment. **The Owner is not being asked to pick from this list** —
it exists so the decision is made with the corpus in view, not against a blank page.

### Source evidence A — prior hypotheses with a friction-anchored MDE

`HYPOTHESIS_REGISTRY.md`, HYP-PM-0001 and HYP-PM-0003 notes: registered under a *"**friction-anchored MDE**
(round-trip ≈ **0.60%** from the cost authority, `engine/exits/costs.py`)"*, with
*"α=**0.05**/power=**0.80** (hypothesis-specific convention)"*.

### Source evidence B — the C7 owner decision of 2026-09-11

`C7_REGISTRATION_v1_2026-09-11.md` §3 item 5, recording the Owner's verbatim ruling on this exact question:

> *"**No MDE or formal power claim is authorized unless already supported by an existing authoritative
> methodology.**" None exists.* → **Registered: "MDE/power not used as a confirmation criterion."** *No power
> claim may be attached to C7 outputs.*

### Source evidence C — the HYP-PM-0008 draft pattern §13 cites by name

`HYP-PM-0008_SPEC.md` §11 — **a DRAFT, never registered, never Owner-approved**:

| Parameter | Value | Stated source |
|---|---|---|
| Δ (minimum detectable difference) | 0.60% | estate round-trip friction floor (the §6.1 F4 bar) |
| σ (assumed sd of the daily series) | 2.0% | *"declared ex ante, **not measured**; a conservative round figure"* |
| σ (assumed sd at event level) | 5.0% | *"declared, not measured"* |
| α / power | 0.05 two-sided / 0.80 | program convention |
| ⇒ event-days per arm | n ≥ 175 | `n = 2σ²(z_{α/2}+z_β)²/Δ²` |
| ⇒ events per arm | N ≥ 1,090 | same expression at event level |

**Note on C:** §13 cites this document as *"the pattern"* — i.e. the *form* of the declaration
(ex-ante σ → MDE → feasibility gate). Whether the *values* transfer is not stated by §13 and is not
resolved here.

**Observation offered without recommendation:** evidence B and evidence C are **structurally different
answers to the same question** — B declines to attach an MDE at all; C declares one ex ante. Both are
already in the corpus. **Choosing between them, or choosing neither, is the Owner's decision.**

---

# R7 — PROVENANCE LIMITATION

## 1 · The exact limitation

The 76-session cohort predates the prospective capture service. Its point-in-time status rests on
`stockbit_flow.updated_at` — a write timestamp emitted by this system's own writer in the **same commit** as
the corresponding bars (`tools/backfill_flow_bars.py::_persist`), in naive Asia/Jakarta time. Because the
backfill **skips** already-complete cells rather than overwriting them, an `updated_at` still bearing its own
trade date additionally establishes the cell was **never subsequently rewritten**.

**The original vendor raw payload, request parameters, and vendor-side response timestamp are not
preserved.** No raw response archive exists for `stockbit_flow_bars`.

## 2 · Why MITIGATED and not CLOSED

**Mitigated** — the strongest available fingerprint is now recorded
(`store/I7_V004_SOURCE_PROVENANCE_v1.json`), every field labelled with its evidential strength and none
presented as a content hash: schema fingerprint `cabe892cc70e87ab…`; source extents; size/mtime marked
**WEAK**; and a **source-agreement spot check — 200/200 sampled admitted cells match the live source, 0
disagreements**.

**Not closed** — two facts cannot be retired by any action available now:

1. **Byte-for-byte reproduction is impossible.** The source is a live 13.7 GB table under continuous cron
   writes, unhashed by design (a hash would be stale before use), and the builder stamps `built_utc`.
2. **Third-party re-verification of the vendor's original response is impossible**, because that response
   was never retained.

**This is inherent to accruing from a live vendor-fed table. It was not introduced by v004**, and it is
exactly the gap the prospective capture service closes for *future* sessions.

## 3 · The standard is not raised

Governance requires a Dataset to declare `point_in_time` — *"whether reconstructible as-known-then (F7)"* —
and a Feature to carry a `point_in_time_argument` (`RESEARCH_OBJECT_SCHEMA` l.225, l.247); immutability
**on fingerprint** (l.233); and **X2 · Specified** — *"complete enough that a competent stranger could
re-derive the conclusion"* — as the minimum for any tier ≥ E3 (`EVIDENCE_MODEL` §4). **Nothing in the corpus
requires a raw vendor payload.** This memo does not introduce that requirement.

Governance also positively supports the E-PIT-1 exclusion: `LITERATURE_RESEARCH_STANDARD` bias **B3** —
*"Backfill / index-inclusion: Data added retrospectively → **F7 look-ahead in the source itself**, inherited
silently by anyone who transports the design."*

## 4 · Draft registration disclosure language

> **PIT provenance limitation.** The registered cohort predates the prospective capture service. Its
> point-in-time status rests on `stockbit_flow.updated_at`, a write timestamp emitted by this system's own
> writer in the same commit as the corresponding bars (naive Asia/Jakarta). Because the backfill skips
> already-complete cells rather than overwriting them, an `updated_at` still bearing its own trade date also
> establishes the cell was never subsequently rewritten. The cohort admits only cells written within one day
> of their session and, for same-day writes, only those after 16:15 WIB — after the session's final bar.
>
> This evidence supports the claim **"this system held these values contemporaneously with the session, and
> they were not later altered."** It does **not** preserve the vendor's original response payload, request
> parameters, or vendor-side timestamp, and therefore does **not** support **"the original vendor response is
> independently re-verifiable."**
>
> This is a **verification** limitation, not an **availability** limitation, and it is materially weaker than
> the defect that disqualified the historical interval (99.41% of cells written >120 days after their
> session, median lag 364 days), which is excluded wholesale by E-PIT-1 under bias **B3 / F7**.
> Dataset `point_in_time` is declared **true with this qualification**; `custody_partition` is **in-sample**.
> Byte-for-byte reproduction from recorded inputs is not possible; content re-derivation is evidenced by a
> 200/200 source-agreement spot check recorded in `I7_V004_SOURCE_PROVENANCE_v1.json`.

---

# ADDITIONAL VERIFICATIONS

| Item | Finding | Evidence |
|---|---|---|
| **2026-09-08 governed by the existing estimator** | **CONFIRMED.** It retains its single admissible cell; **no minimum-cell or minimum-session rule exists** at the accrual layer. Spec §9 Step 1 disposes of it: *"For each admitted formation date d with **>= 1 LATE_TILTED and >= 1 EARLY_TILTED** cell … Dates lacking either side are **skipped and counted** (never zero-filled)."* A one-cell date cannot contain both states, so the **estimator** skips it — no accrual-layer rule is needed or was added | `test_frozen_2026_09_08_retains_single_admitted_cell`; `test_no_minimum_cell_rule_in_source` |
| **Capture activation is not a prerequisite to registration** | **CONFIRMED.** v004 is frozen, hash-pinned and self-sufficient — it holds its own bars and its own 82,814-row admissibility ledger and does not read the live table. Activation is required only to extend the cohort past 2026-09-11 and to raise *future* cells above the §R7 limitation | validation gates 1–7 run entirely on frozen state; only opt-in gate 8 touches production |
| **No outcome-dependent selection** | **CONFIRMED.** `admissible()`'s signature is `(session_date, captured_at_wib, n_bars)` — no price, return or outcome can reach it. AST analysis: **no outcome token in any executable SQL of the accrual builder, and no dynamic SQL**. Bar value columns are read only when copying admitted cells, *after* admission is decided. The cohort boundary (2026-04-28) is a **capture-infrastructure** date, exogenous to any market or outcome property. The one `close` access is a **presence** test (`close IS NOT NULL`) inside the calendar's inherited predicate — the value is never read, compared, ranked or returned | gate 6; `test_x5_x6_not_applied_at_accrual`; `test_gate_is_outcome_blind` |
| **No retest of C3/C7 or any prior hypothesis** | **CONFIRMED.** I7's grain is **within-session**; every prior registered P-M test is daily-grain. It reads no broker table, so C3 (broker counts) and C7 (`gross/ADV20`) are not computable from its inputs. Conditioning on `daily_net > 0` holds the daily-direction variable fixed, keeping it orthogonal to HYP-PM-0001/0002's variable. C3 and C7 remain terminal and untouched | spec §4 independence table; §17 checked against all 21 inventory objects |

---

# OWNER DECISIONS REQUIRED

### **D-1 — Population substitution**

Accept the PIT-valid cohort — **76 sessions, 2026-04-28 → 2026-09-11, 61,335 ticker-days**, bound by
fingerprint `e1375264…fba` — as I7's registered population, superseding the ~277-session interval described
in spec §7/§12, which is disjoint from it.

*Available as an explicit population/exclusion decision at G1; no preregistration amendment is required
because I7 is in DRAFT (HL-2). Free now; R7.4/R15 after G1.*

### **D-2 — MDE / assumed σ / feasibility gate**

Supply the field spec §13 and §G.2 require and do not contain: the ex-ante MDE, the assumed σ, and the
pre-execution feasibility gate (minimum qualifying event-days per state, shortfall ⇒ **RETIRED —
UNPOWERED**) — **or** rule that none is authorized, as the Owner previously ruled for C7.

*No value is proposed by this memo. Source evidence A, B and C are reported for visibility only, and B and
C are structurally different answers already present in the corpus.*

---

**Nothing else is requested.** The R7 disclosure (§4 above) is drafting support, not a decision; it is
adopted as part of whichever registration follows. **I7 remains NOT registered and NOT executed.**
