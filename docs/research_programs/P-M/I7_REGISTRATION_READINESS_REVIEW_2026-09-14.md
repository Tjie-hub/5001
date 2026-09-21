# I7 · v003 REGISTRATION-READINESS REVIEW — 2026-09-14

**Authority:** generated point-in-time record. **Mode:** registration audit. **REVIEW ONLY.**

> **I7 not executed, not registered.** No return, IC, p-value, power figure, or P&L computed. C3/C7 not
> retested. Dataset B, v002 and the v003 freeze unmodified. No hypothesis or family created. No methodology
> rescue proposed. **No sample-size threshold, power target, minimum-session count, minimum-cell rule, or
> stopping rule was invented by this review.** All access read-only.

**Specification under review:** `BRANCH_A_NEW_MECHANISM_AUDIT_2026-09-14.md` §§1–17 + §G (the I7 candidate
spec). **Cohort under review:** v003, sha256 `a4a9f7f9…`, commit `cd40b03`.

---

# 1 · HYPOTHESIS — **PRESERVED**

v003 is a *population* artifact. It touches no substantive field of the specification:

| Field | Spec | Affected by v003? |
|---|---|---|
| Mechanism (§1) | informed execution back-loads within the session; M2/I7 | **No** |
| Signal (§5) | OPEN 09:00–09:59, LATE 14:50–15:49; `nbuy(LATE)/daily_net ≥ 0.50` | **No** |
| Conditioning (§5) | `daily_net > 0` | **No** |
| Estimand (§9) | daily series of LATE−EARLY means; NW lag 5; two-sided | **No** |
| Horizon (§10) | k = 1; outcome `close(t+2)/close(t+1)−1` | **No** |
| Multiplicity (§14) | single cell; Holm = identity; P-M `{I5,I6,I7,I12}` | **No** |
| Kill rule (§16) | θ not positive at p < 0.05 ⇒ FAILED F2 | **No** |
| Exclusion of 16:00–16:14 bars (§5) | deliberate | **No** — v003 preserves the full 335/275 grid; the estimator drops them |

**The hypothesis is unchanged. No modification proposed or required.**

# 2 · SAMPLE / COHORT

## 2.1 E-PIT-4 ≡ X4 — mechanical

Spec X4 excludes `coverage_state != 'BARS'` or `n_bars` ≠ the weekday grid (335 Mon–Thu / 275 Fri).
E-PIT-4 is the same rule. **Verified in the freeze: 0 cells violate the structural grid.** Mechanical.

## 2.2 E-PIT-2 and E-PIT-3 — mechanical, but additions to the declared set

Neither appears in the spec's X1–X6. Both are **provenance** filters: write-lag and the 16:15 WIB cutoff.
Neither consults an outcome (§4). They do not alter what I7 measures — they remove cells whose *capture*
cannot support the measurement (E-PIT-3 removes cells holding a partial session, which would be
`EARLY_TILTED` by artifact).

**They are mechanical in character but must be named in the registration**, because the spec's declared
exclusion set is X1–X6 and these are not in it. Since I7 is not yet registered, naming them at registration
is ordinary specification, not an amendment.

## 2.3 E-PIT-1 — **NOT a mechanical exclusion. This is a population replacement.**

| | Spec (§7, §12) | v003 |
|---|---|---|
| Window | **2025-01-02 → 2026-04-27** | **2026-04-28 → 2026-09-11** |
| Sessions | "~277 admitted" | **77** |
| Bars | 77,559,605 | 20,070,910 |

**The two intervals are disjoint. Not one session of the population the specification describes survives
into v003.** The spec's own §12 anchors its expected sample at "~277 observations — the same order as C3's
329"; v003 delivers 77, roughly **28%** of that and **23%** of C3's.

X1 (2025-04-14 fixture) and X2 (contradiction zone) are *subsumed* by E-PIT-1 — they sit inside the
interval it removes — so they are not contradicted, merely made moot.

> **This is not a narrowing of the registered population; it is a substitution of a different one.** It is
> justified — the PIT audit established the old interval is 99.41% backfilled at a median lag of 364 days —
> but the justification does not make it mechanical. **Owner decision (§9, D-1).**

## 2.4 **MECHANICAL DEFECT — X3 is not implemented by v003**

Spec X3 excludes *"non-admitted sessions per `session_calendar.is_admitted = 0`"*. The v003 builder does
not consult `session_calendar` at all. Two consequences, both verified:

| Finding | Detail |
|---|---|
| **X3 violation** | **`2026-07-09` is in the v003 cohort but `session_calendar` marks it `is_admitted = 0`** — reason: *"member price coverage below threshold"*. The registered exclusion set forbids it; v003 contains it |
| **X3 unevaluable** | `session_calendar` spans 2025-01-02 → **2026-08-27**. **11 v003 sessions fall beyond it** — 2026-08-28, 08-31, 09-01, 09-02, 09-03, 09-04, 09-07, 09-08, 09-09, 09-10, 09-11 — so X3 cannot be evaluated for them at all |

The other two non-admitted sessions are already out: `2026-07-24` (E-PIT-2, lag 3) and `2026-08-25` (no
bars). Only **2026-07-09** is an actual violation.

This is the defect that makes the cohort mechanically non-conformant to its own specification. **§10.**

## 2.5 X5 and X6 — correctly absent from the cohort

X5 (corporate action on *t/t+1/t+2*; `RAJA`; `close(t) < Rp 100`; PIT liquidity floor) and X6 (*t, t+1, t+2*
strictly consecutive) are **estimation-time** filters over `ohlcv`, not cohort-time filters over bars. Their
absence from v003 is correct, not a defect. They must be applied by the estimator and counted there.

One interaction worth recording: v003's exclusions create holes in the **formation** set only. The outcome
path `close(t+1) → close(t+2)` is read from `ohlcv`, so a formation-side exclusion at *t* never breaks the
outcome for another session. X6 still binds independently.

## 2.6 2026-09-08 — **left in, per instruction**

It carries one admissible ticker-day. **No minimum-cell rule was invented and the session was not
excluded.** The existing estimator disposes of it: §9 skips and counts any formation date lacking either
state, and a one-cell date cannot contain both. **No action required.**

# 3 · PIT PROVENANCE — **the `updated_at` proxy IS acceptable under the existing standard**

## 3.1 What governance actually requires

| Requirement | Source | Met by v003? |
|---|---|---|
| Dataset declares `point_in_time` — *"whether reconstructible as-known-then (**F7**)"* | `RESEARCH_OBJECT_SCHEMA` §Dataset (l.225) | **Yes** — declarable, with the argument in §3.2 |
| Feature declares `point_in_time_argument` — *"why no future information enters (**F7**)"* | `RESEARCH_OBJECT_SCHEMA` §Feature (l.247) | **Yes** — formation uses only session-*t* bars; entry is `close(t+1)` |
| *"**Immutable on fingerprint.** … Experiments bind the fingerprint, not the name — otherwise a silent upstream revision retroactively changes what a completed experiment tested, which is F7 arriving through the back door"* | `RESEARCH_OBJECT_SCHEMA` l.233 | **Yes** — sha256 `a4a9f7f9…`, read-only, overwrite-refusing |
| **X2 · Specified** — *"complete enough that a competent stranger could re-derive the conclusion"*; **minimum for any tier ≥ E3** | `EVIDENCE_MODEL` §4 | **Yes** — frozen store + 82,814-row admissibility ledger + rules in code |
| `custody_partition` — in-sample / out-of-sample / forward | `RESEARCH_OBJECT_SCHEMA` §Dataset | **Must be declared** — v003 is historical relative to registration ⇒ **in-sample** |

**Governance nowhere requires an original vendor payload or an original vendor response timestamp.** The
reproducibility axis (X0–X4) is about re-deriving the *conclusion from the specification*; the PIT
requirement is about a *reconstructible-as-known-then argument*. Both are satisfiable here.

> **This review therefore does not raise the bar to raw-payload provenance.** Doing so would invent a
> standard the corpus does not contain.

## 3.2 And governance positively supports E-PIT-1

`LITERATURE_RESEARCH_STANDARD` bias **B3** — *"**Backfill / index-inclusion**: Data added retrospectively →
**F7 look-ahead in the source itself**, inherited silently by anyone who transports the design."*

Excluding the 99.41%-backfilled v002 interval is not over-caution; it is the corpus's own named bias
control. **E-PIT-1 is governance-aligned even though it is an Owner-level population change.**

## 3.3 Exact limitation language that must appear in the registration

> **PIT provenance limitation (declared at registration).** The v003 cohort predates the prospective capture
> service. Its point-in-time status rests on `stockbit_flow.updated_at`, a write timestamp emitted by this
> system's own writer in the same commit as the corresponding bars, in naive Asia/Jakarta time. Because the
> backfill skips already-complete cells rather than overwriting them, an `updated_at` still bearing its own
> trade date additionally establishes that the cell was never subsequently rewritten. The cohort admits only
> cells written within one day of their session and, for same-day writes, only those after 16:15 WIB — after
> the session's final bar.
>
> This evidence supports the claim **"this system held these values contemporaneously with the session, and
> they were not later altered."** It does **not** preserve the vendor's original response payload, request
> parameters, or vendor-side response timestamp, and therefore does **not** support the stronger claim
> **"the original vendor response is independently re-verifiable."**
>
> This is a **verification** limitation, not an **availability** limitation. It is materially weaker than
> the defect that disqualified the v002 interval (99.41% of cells written >120 days after their session,
> median lag 364 days), which is excluded wholesale by E-PIT-1 under bias **B3 / F7**. Dataset
> `point_in_time` is declared **true with this qualification**; `custody_partition` is **in-sample**.

# 4 · OUTCOME BLINDNESS — **VERIFIED**

| Check | Result |
|---|---|
| Gate signature | `admissible(session_date, captured_at_wib, n_bars)` — no price, return, or outcome can reach it; asserted by `test_gate_is_outcome_blind` |
| Inputs to the E-PIT rules | session date, capture timestamp, bar count, weekday. **Nothing else** |
| Builder reads | bar columns, `stockbit_flow.updated_at`. **No `close`, no `ohlcv` outcome column** |
| Bars copied vs bars used for admission | `price`, `net_value`, `delta` are copied into the freeze but admission uses `COUNT(*)` only |
| Selection on performance | none possible — the cohort boundary is a **capture-infrastructure change dated 2026-04-28**, exogenous to any market or outcome property |
| Tests | 18/18 pass, incl. exact `16:14:59` / `16:15:00` boundary |

**No outcome information participated in cohort selection.**

# 5 · CAPTURE — **activation NOT required before registration**

v003 is frozen, hash-pinned and self-sufficient: it contains its own bars and its own admissibility ledger,
and does not read the live table. Registration and execution against v003 need nothing from the prospective
service.

**Activation is required only for future accrual** — to extend the cohort past 2026-09-11 and to raise
future cells above the §3.3 limitation by preserving raw payloads.

**No operational requirement is invented here.** The only standing operational note already exists in the
built artifacts: a capture run must occur after **16:15 WIB**, enforced by `capture_guarded.py` and by the
cohort gate.

# 6 · POWER / DETERMINACY — **NO RULE EXISTS**

The specification **requires** such a rule and **does not contain one**. Verbatim, §13:

> *"At registration the MDE must be declared **ex ante from a stated assumed σ** … and a **pre-execution
> feasibility gate** must specify a minimum count of qualifying event-days per state, with shortfall
> terminating the hypothesis as **RETIRED — UNPOWERED** (a non-failure). **No MDE number is asserted
> here.**"*

And §G.2, as a registration requirement:

> *"**An ex-ante MDE with a declared assumed σ**, plus a **pre-execution feasibility gate** (minimum
> qualifying event-days per state) whose shortfall yields **RETIRED — UNPOWERED**, not FAILED."*

The spec's only sample statement is descriptive and now superseded (§12: *"~277 observations — the same
order as C3's 329"*), against v003's 77 sessions.

## **OWNER DECISION REQUIRED**

**No σ, no MDE, no minimum event-day count, no session threshold, and no stopping rule is proposed by this
review.** Per §6 of the task brief, inventing one is prohibited, and per `RESEARCH_PROGRAM` §6.1 a test
without a power/MDE argument is auto-rejected at admissibility (**R2** — *"a test that could not fail
produces no evidence"*). The field must be supplied by the Owner before registration.

# 7 · REGISTRATION INTEGRITY

## 7.1 Substantive fields — all unchanged

Hypothesis · estimator · primary window *(k=1, entry `close(t+1)`)* · threshold *(0.50)* · state definition
*(LATE/EARLY on `nbuy(LATE)/daily_net`)* · outcome *(`close(t+2)/close(t+1)−1`)* · inference *(NW lag 5,
two-sided)* · multiplicity *(single cell, Holm identity)* · decision rule *(§16)*. **None requires
modification to register against v003.**

## 7.2 Fields that must be frozen before execution

| # | Field | State |
|---|---|---|
| 1 | Mechanism, signal, conditioning, estimand, horizon, entry reference, inference, multiplicity, cost convention, kill rule, interpretation rule, no-rescue rule | **Ready — carry from the spec verbatim** |
| 2 | **Population / cohort** — v003 sha256 `a4a9f7f9…`, 77 sessions, bound by fingerprint not name | **Owner decision** (§2.3) |
| 3 | **Exclusion set** — X3–X6 **plus** E-PIT-1..4, with X1/X2 recorded as subsumed | **Ready once §10 is remediated** |
| 4 | **MDE / σ / feasibility gate** | **MISSING — Owner decision** (§6) |
| 5 | PIT limitation language | **Ready — §3.3 verbatim** |
| 6 | `point_in_time`, `custody_partition` (= in-sample), `fidelity_limit`, `proxy_for` | **Ready to declare** |
| 7 | B4 limitation (PPK/board unidentifiable) | **Ready to declare** |
| 8 | Family: P-M `{I5,I6,I7,I12}`, slot #3, HYP-PM-0002 overlap recorded | **Ready — no amendment needed** |
| 9 | D-049 semantic-gate compliance (no all-broker net constructed) | **Ready — trivially satisfied** |
| 10 | Superseding §7/§12 coverage figures | **Ready — descriptive correction, not a methodology change** |

> **On item 10:** §7 and §12 carry v002-era coverage numbers (77,559,605 bars; 309 sessions; ~277 admitted).
> These are **descriptive** fields, not registered parameters. Replacing them with the v003 figures corrects
> a stale description and is **not** a change to hypothesis, estimator or decision rule.

---

# FINAL CLASSIFICATION

## **NOT READY — MECHANICAL ISSUE**

# 8 · The exact defect and its remediation

**Defect.** The v003 cohort does not implement the specification's exclusion **X3**
(`session_calendar.is_admitted = 0`). `build_v003_freeze.py` never consults `session_calendar`.

**Manifestation, verified:**

1. **`2026-07-09` is present in v003 and is X3-excluded** (`is_admitted = 0`, *"member price coverage below
   threshold"*). The cohort contains a session its own specification forbids.
2. **`session_calendar` ends 2026-08-27, while v003 runs to 2026-09-11** — X3 is **unevaluable** for 11
   sessions: 2026-08-28, 08-31, 09-01, 09-02, 09-03, 09-04, 09-07, 09-08, 09-09, 09-10, 09-11.

**Remediation — the smallest sufficient change:**

- **(a)** Extend the admission calendar to cover 2026-08-28 → 2026-09-11 using the criteria already encoded
  for it, **then** rebuild the cohort as **v004** applying X3 alongside E-PIT-1..4; **or**
- **(b)** If the Owner determines X3's admission criteria do not govern the v003 era, record that
  determination as a dated decision and register with X3 formally superseded for this cohort.

In either case the freeze is **not edited** — v003 is immutable and the builder refuses overwrite; a
corrected cohort is a **new version**. Remediation changes no substantive field in §7.1 and requires no
methodology change.

# 9 · Owner decisions still required after remediation

Both are outstanding **independently** of §8, and registration cannot proceed until both are answered:

| # | Decision | Smallest form |
|---|---|---|
| **D-1** | **Accept the population substitution.** v003 (77 sessions, 2026-04-28→2026-09-11) is **disjoint** from the interval the spec describes (~277 sessions, 2025-01-02→2026-04-27), and ~28% of its size. | *"Register I7 against the v003 cohort, bound by fingerprint `a4a9f7f9…`, superseding §7/§12's v002-era coverage description."* |
| **D-2** | **Supply the missing MDE / feasibility gate** required by §13 and §G.2. | *"Declared σ = ___; MDE = ___; minimum qualifying event-days per state = ___; shortfall ⇒ RETIRED — UNPOWERED."* |

Subsidiary and unchanged: spend P-M slot #3; accept the B4 limitation; whether to activate prospective
capture for accrual.

---

# CONFIRMATIONS

- **I7 not executed, not registered; specification unmodified**
- **Zero returns / IC / p-values / power figures / P&L; no alpha inspected; C3 and C7 not retested**
- **No new hypothesis or family; no registry mutation; no methodology rescue**
- **Dataset B, v002 and the v003 freeze unmodified** (review was read-only)
- **No sample-size threshold, power target, minimum-session count, minimum-cell rule, or stopping rule
  invented** — §6 reports the absence and stops
- **2026-09-08 left in the cohort**, per instruction; the existing estimator disposes of it
- **Files created by this task: 1** — this review
