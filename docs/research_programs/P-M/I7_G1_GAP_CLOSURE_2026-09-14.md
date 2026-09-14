# I7 — G1 GAP CLOSURE — 2026-09-14

**Authority:** generated point-in-time record. **Scope:** records the Owner's D-1 acceptance and supplies
the one missing §5.2 intake element (the null). **Documentary completion only.**

> **I7 is NOT registered and NOT executed.** No outcome, return, IC or p-value has been inspected. v003 and
> v004 are untouched. No methodology was invented, no threshold tuned, no sample-size rule added, no new
> hypothesis or family created. C3 and C7 are not retested.

---

## 1 · D-1 — ACCEPTED (Owner, 2026-09-14)

The PIT-valid v004 population is **accepted** as I7's registration population, superseding the historical
window described in spec §7/§12.

| Field | Value |
|---|---|
| Sessions | **76** |
| Window | **2026-04-28 → 2026-09-11** |
| Admissible ticker-days | **61,335** |
| Tickers | **868** |
| Bar rows | **19,793,865** |
| **Fingerprint (binding)** | **`e1375264133b42f417d8e74f48a48646197d15b8961e3bdf431d6eebc8784fba`** |
| Store | `i7_accrual/store/I7_V004_ADMISSIBLE_v1.sqlite` (read-only, overwrite-protected) |

The population binds **by fingerprint, not by name** (`RESEARCH_OBJECT_SCHEMA` l.233). Spec §7 and §12
are superseded **as descriptions**; they are descriptive coverage statements, not registered parameters.

**D-1 is closed and is not revisited in this document.**

### Exclusion set, as validated (unchanged)

| Rule | Disposition | Count |
|---|---|---|
| **X1** (2025-04-14 fixture) | subsumed by E-PIT-1 — region ends before the 2026-04-28 boundary | — |
| **X2** (2025-08-04 → 2025-09-17 zone) | subsumed by E-PIT-1 — same | — |
| **X3** (non-admitted sessions) | **enforced at cohort layer**, session-level, ahead of the E-PIT predicates | **7,038** cells / 8 sessions |
| **X4** | **≡ E-PIT-4** (bars present, exact weekday grid 335 Mon–Thu / 275 Fri) | **10,890** |
| **X5** (CA / RAJA / price floor / liquidity floor) | **estimation-layer** — applied and counted by the estimator; deliberately not at accrual | — |
| **X6** (*t, t+1, t+2* consecutivity) | **estimation-layer** — same | — |
| **E-PIT-1** (historical interval, wholesale) | enforced — bounds the candidate set | 239,695 ticker-days |
| **E-PIT-2** (no contemporaneous provenance) | enforced | **2,044** |
| **E-PIT-3** (same-day capture before 16:15 WIB) | enforced | **1,507** |

Ledger: **61,335 + 7,038 + 2,044 + 1,507 + 10,890 = 82,814** candidate cells — exact, MECE, duplicate-free.

---

## 2 · THE NULL — documentary completion of §5.2

`RESEARCH_PROGRAM` §5.1 requires all six intake elements or *"G1 REFUSES (not defers)"*. Five were present;
**null** was absent. It is supplied here by **derivation from the already-authored §1 prediction only** —
no new design choice is made.

### 2.1 Source (verbatim, unchanged)

> **§1 Prediction:** *"conditional on a day being a **net-buying** day, a day whose net buying was
> **back-loaded** is followed by higher subsequent return than a day whose net buying of the same sign was
> **front-loaded**. The daily total is held fixed by construction; only *when* it happened varies."*
>
> **§9:** `m(d) = mean fwd return of LATE_TILTED cells − mean fwd return of EARLY_TILTED cells`;
> `theta_primary = mean of the daily series m(d)`. **`PREDICTION: theta_primary > 0.`**

### 2.2 The null, stated

> **H₀ (null).** Conditional on a day being a net-buying day (`daily_net > 0`), a day whose net buying was
> back-loaded is followed by a subsequent return **no higher** than that of a day whose net buying of the
> same sign was front-loaded. Within-session back-loading of net buying carries **no** information beyond
> the daily total.
>
> **Formally: `H₀ : theta_primary ≤ 0`.**
>
> **H₁ (alternative, unchanged from §1/§9): `theta_primary > 0`.**

### 2.3 Verification that this is the exact complement

| Check | Result |
|---|---|
| **Collectively exhaustive** | `{θ ≤ 0} ∪ {θ > 0} = ℝ` — every possible value of the estimand falls in exactly one |
| **Mutually exclusive** | `{θ ≤ 0} ∩ {θ > 0} = ∅` |
| **Complement of the economic claim** | "higher than" → "no higher than". The negation of a strict inequality is the non-strict opposite; nothing else changed |
| **Does it introduce a two-sided test?** | **No.** H₁ remains strictly `θ > 0`. A negative `theta_primary`, however large, falls inside H₀ and is a **non-rejection** — not a separate finding, not a reversed alternative, not reportable as a discovery |
| **Does it introduce a new alternative?** | **No.** H₁ is copied from §9 verbatim |
| **Is it a point null?** | **No — deliberately.** `H₀ : θ = 0` would be a point null whose natural complement is `θ ≠ 0`, i.e. a two-sided alternative. That would be a methodology change. The composite one-sided `θ ≤ 0` is the true complement of `θ > 0` |
| **Consistent with the §16 kill rule?** | **Yes.** §16 refutes when `theta_primary` is *"not positive with two-sided p < 0.05"*. Non-rejection of H₀ covers both `θ ≤ 0` and `θ > 0` that fails significance — exactly the set §16 already describes. The kill rule is unchanged |

### 2.4 One descriptive note on the inference, offered because D-2 will need it

§9 reports a **two-sided p**; §16 requires **`θ > 0` AND two-sided p < 0.05**. That conjunction is a
**one-sided decision implemented with a two-sided statistic**: the sign condition, not the p-value, is what
makes the test directional. Its rejection region therefore has nominal one-sided size **0.025**.

**This is a description of the already-registered rule, not a change to it and not a proposal.** It is
recorded only because an MDE cannot be computed without knowing the effective α, and that computation is
D-2's subject. **Nothing here alters §9 or §16.**

---

## 3 · Substantive-field invariance

Every substantive field is carried **verbatim**. The null is additive; it displaces nothing.

| Field | §ref | Status |
|---|---|---|
| Mechanism — informed execution back-loads within the session (M2 / I7) | §1 | **unchanged** |
| Directional prediction — `theta_primary > 0` | §1, §9 | **unchanged** |
| Signal — OPEN 09:00–09:59, LATE 14:50–15:49; `nbuy(LATE)/daily_net ≥ 0.50` | §5 | **unchanged** |
| Conditioning — `daily_net > 0` | §5 | **unchanged** |
| Estimand — `m(d)` = LATE−EARLY daily mean difference | §9 | **unchanged** |
| Estimator — mean of the daily series, Newey-West, lag 5 | §9 | **unchanged** |
| Horizon — k = 1; outcome `close(t+2)/close(t+1) − 1`; entry reference `close(t+1)` | §10 | **unchanged** |
| Threshold — 0.50 back-loading split | §5 | **unchanged** |
| Inference — NW lag 5, two-sided p, sign condition | §9, §16 | **unchanged** |
| Multiplicity — single cell, Holm = identity; P-M `{I5,I6,I7,I12}` slot #3 | §14 | **unchanged** |
| Cost convention — `θ_net = θ − 0.006`, reported sensitivity only | §14 | **unchanged** |
| Kill / decision rule | §16 | **unchanged** |
| Outcome definition | §10 | **unchanged** |
| 16:00–16:14 bars excluded from every quantity | §5 | **unchanged** |
| No-rescue rule | §18 | **unchanged** |

**No threshold was tuned. No sample-size rule was added. No estimator was introduced.**

---

## 4 · D-2 — REMAINS OPEN

### 4.1 Where the specification requires it

| # | Location | Requirement |
|---|---|---|
| 1 | I7 spec **§13** | *"At registration the MDE must be declared **ex ante from a stated assumed σ** … and a **pre-execution feasibility gate** must specify a minimum count of qualifying event-days per state, with shortfall terminating the hypothesis as **RETIRED — UNPOWERED**. **No MDE number is asserted here.**"* |
| 2 | I7 spec **§G.2** | the same, restated as a registration precondition |
| 3 | `RESEARCH_PROGRAM` **§6.1** | *"The test **could not fail** (no power / MDE) → **R2**"* — **auto-rejection** at admissibility |
| 4 | `RESEARCH_PROGRAM` **§6.1** | *"Predicted effect **< friction** → **F4**"* |
| 5 | `RESEARCH_PROGRAM` **§5.1** | the G1 packet must carry *"power/MDE showing the test CAN fail (R2)"* or G1 **refuses** |
| 6 | `RESEARCH_PROGRAM` **§9.2** | thresholds declared *"per hypothesis at registration (ex ante, **R5**)"* |

### 4.2 Status

> **No authorized I7 value exists for the MDE, the assumed σ, the power target, the minimum sample size,
> the feasibility threshold, or any stopping rule.** §13 states the requirement and explicitly declines to
> satisfy it.

### 4.3 What this document deliberately did NOT do

- **Did not transplant the HYP-PM-0008 values** (Δ 0.60%, σ 2.0%/5.0%, α 0.05 / power 0.80, n ≥ 175,
  N ≥ 1,090). That document is a **DRAFT, never registered, never Owner-approved**.
- **Did not substitute the C7 precedent** (*"MDE/power not used as a confirmation criterion"*).
- **Did not create any new statistical rule**, α, threshold or gate.
- **Did not infer a value from the cohort size.** The 76-session count is recorded as a fact of D-1; it is
  **not** used here to reverse-engineer an MDE, which would be a criterion chosen after the data were seen.

**D-2 is an OWNER DECISION and is the sole remaining blocker.**

---

## 5 · R7 — provenance limitation (concise)

The cohort predates the prospective capture service. Its PIT status rests on `stockbit_flow.updated_at`, a
write timestamp emitted by this system's own writer in the **same commit** as the corresponding bars (naive
Asia/Jakarta). Because the backfill **skips** already-complete cells rather than overwriting them, an
`updated_at` still bearing its own trade date also establishes the cell was **never later rewritten**. Only
cells written within one day of their session are admitted, and for same-day writes only those after
**16:15 WIB** — after the session's final bar.

This supports **"this system held these values contemporaneously with the session, and they were not later
altered."** It does **not** preserve the vendor's original payload, request parameters or vendor-side
timestamp, so it does **not** support **"the original vendor response is independently re-verifiable."**

A **verification** limitation, not an **availability** one — and materially weaker than the defect that
disqualified the historical interval (99.41% of cells written >120 days after their session, median lag 364
days), excluded wholesale by E-PIT-1 under bias **B3 / F7**. **MITIGATED, not closed:** byte-for-byte
reproduction is impossible (live 13.7 GB source, unhashed by design; builder stamps `built_utc`), but a
source-agreement spot check records **200/200 sampled admitted cells matching the live source**
(`I7_V004_SOURCE_PROVENANCE_v1.json`). Inherent to accruing from a live vendor-fed table; not introduced by
v004. Declared at registration: `point_in_time` **true with this qualification**, `custody_partition`
**in-sample**.

---

## 6 · Untouched — confirmed

| Artifact | State |
|---|---|
| `I7_V004_ADMISSIBLE_v1.sqlite` | **unmodified** — `e1375264…fba` |
| `I7_V003_ADMISSIBLE_v1.sqlite` | **unmodified, immutable** — `a4a9f7f9…0e0` |
| `BRANCH_A_NEW_MECHANISM_AUDIT_2026-09-14.md` (the I7 spec) | **unmodified** — `76a96545…` |
| v002 freeze, Dataset B, base session calendar | **unmodified** |
| `HYPOTHESIS_REGISTRY`, `FAILURE_REGISTRY`, `EXPERIMENT_LEDGER`, `DECISION_LOG` | **unmodified** — I7 unregistered; no family slot consumed |
| C3, C7 and every prior valid test | **untouched, not retested** — I7's grain is within-session; it reads no broker table, so C3 (broker counts) and C7 (`gross/ADV20`) are not computable from its inputs |
| Production database | **no writes** |

**Validation state carried forward:** 27/27 tests · 8/8 executable gates · commits `efd1a6e`, `3589190`.

---

## 7 · G1 intake — current standing

| §5.2 element | Status |
|---|---|
| Mechanism (M-class + constraint + participant) | ✅ §1 |
| Directional prediction | ✅ §1 / §9 |
| **Null** | ✅ **supplied by §2 of this document** |
| Scope | ✅ **D-1 accepted** — v004, fingerprint-bound |
| **Ex-ante criterion incl. effect size** | ❌ **D-2 — OPEN** |
| Multiplicity family | ✅ P-M `{I5,I6,I7,I12}`, slot #3 |
| Refutation in one sentence (R14) | ✅ §16 |
| Mechanism blind to result | ✅ authored 2026-08-21, months before the cohort existed |
| Data Available/Obtainable (D-002) | ✅ v004 frozen and fingerprinted |
| CRO approval | ⏳ follows D-2 |

**Exactly one blocker remains.**

---

# FINAL STATUS

## **NOT READY — OWNER DECISION REQUIRED (D-2)**

D-1 is accepted and closed. The null is supplied as a documentary completion derived solely from the
existing §1 prediction, verified to be its exact one-sided complement, introducing neither a two-sided test
nor a new alternative. Every substantive field is unchanged.

**D-2 — the ex-ante MDE, assumed σ, and pre-execution feasibility gate — is the sole remaining blocker, and
no value for it is proposed, inferred, or implied by this document.**
