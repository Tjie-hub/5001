# HYP-PM-0009 — REGISTERED (frozen, immutable)

> **This is the frozen registration record.** Per Owner/CRO authorization (2026-09-14, `DECISION_LOG`
> **D-050**), HYP-PM-0009 passed **G1** and underwent the irreversible **DRAFT → REGISTERED** transition
> ([[HYPOTHESIS_LIFECYCLE]] T4/G1, HL-2). The claim is now **risked** and has **joined the P-M family
> {I5, I6, I7, I12} permanently** (PG-3, OS-10) as its **third** independently-counted member. The bytes
> between the FROZEN markers are sealed by the SHA-256 in the receipt; **any change is a new hypothesis
> (supersession T12), never an edit** (R15).
>
> **NOT EXECUTED.** Registration stops here. No return, IC, p-value or outcome has been computed.

<!--FROZEN-START-->
```
hypothesis_id:          HYP-PM-0009
status:                 REGISTERED
program:                P-M · Microstructure Flow
family:                 P-M {I5, I6, I7, I12}   # DECISION_LOG D-028 — append-only; joined permanently
                        (PG-3, OS-10). THIRD independently-counted REGISTERED member, joining
                        HYP-PM-0001 (FAILED F2) and HYP-PM-0003 (FAILED F2 -> INVALID-DATA).
                        HYP-PM-0002 remains DRAFT/unregistered and consumes no slot.
registered_at:          2026-09-14
authorization:          Owner/CRO ruling, DECISION_LOG D-050

# ---------------------------------------------------------------- mechanism ---
short_name:             Intraday execution timing
mechanism_class:        M2 · information / adverse selection
taxonomy_entry:         I7
mechanism:              Informed and size-constrained participants execute progressively and back-load
                        within the session. A participant with private information or a large parent
                        order cannot lift the book at the open without revealing itself and paying
                        impact; it works the order, and its residual demand concentrates into the final
                        continuous hour, when the closing reference price is forming and liquidity is
                        deepest. Uninformed flow shows the opposite profile: front-loaded at the open,
                        reacting to overnight news.
blind_to:               The mechanism was authored 2026-08-21 (S1 literature sweep,
                        BRANCH_A_NEW_MECHANISM_AUDIT_2026-09-14.md), months before the v004 cohort
                        existed and without any outcome having been computed. No I7 return, IC,
                        p-value or performance quantity has been inspected at any point.

# --------------------------------------------------------------- prediction ---
directional_prediction: Conditional on a day being a net-buying day, a day whose net buying was
                        back-loaded is followed by higher subsequent return than a day whose net buying
                        of the same sign was front-loaded. The daily total is held fixed by
                        construction; only WHEN it happened varies.
H1:                     theta_primary > 0
H0:                     theta_primary <= 0
                        # Economic form: conditional on a net-buying day, a back-loaded day is followed
                        # by a subsequent return NO HIGHER than a front-loaded day of the same sign;
                        # within-session back-loading carries NO information beyond the daily total.
                        # One-sided by construction: a negative theta_primary falls inside H0 as a
                        # NON-REJECTION, never as a reversed finding. H0 is deliberately composite
                        # (theta <= 0), not the point null theta = 0, whose complement would be a
                        # two-sided alternative.

# --------------------------------------------------------------- population ---
population:             I7 v004 admissible cohort (D-050 / D-1 ACCEPTED)
store:                  docs/research_programs/P-M/i7_accrual/store/I7_V004_ADMISSIBLE_v1.sqlite
store_sha256:           e1375264133b42f417d8e74f48a48646197d15b8961e3bdf431d6eebc8784fba
                        # BINDING BY FINGERPRINT, NOT BY NAME (RESEARCH_OBJECT_SCHEMA l.233).
sessions:               76        window: 2026-04-28 .. 2026-09-11
admissible_ticker_days: 61335     tickers: 868     bar_rows: 19793865
pit_universe:           declared from ohlcv by trailing-60-session median traded value, shift(1);
                        the 101-ticker Dataset B roster is NOT used (the intraday asset spans 958).
instrument:             stockbit_flow_bars (vendor aggressor-side 1-minute bars; buy_lot and sell_lot
                        SEPARATE -> structurally immune to the all-broker accounting identity).
                        freq is NEVER read. No broker table is consumed.
required_data:          Available Today (D-002) — frozen v004 store + ohlcv (outcome leg only)

# ------------------------------------------------------------------- signal ---
segments:               clock-time, grid-robust (verified: all 58 Fridays 275 bars, all Mon-Thu 335)
                        OPEN := bars 09:00 <= bar_time <= 09:59
                        LATE := bars 14:50 <= bar_time <= 15:49   (final continuous hour)
                        The 16:00-16:14 post-auction bars are EXCLUDED from every quantity.
nbuy(seg):              SUM(buy_lot) - SUM(sell_lot) over the segment
daily_net:              nbuy over 09:00..15:49 (continuous session only)
conditioning:           POPULATION := ticker-days with daily_net > 0   (net-buying days only)
state:                  LATE_TILTED  if nbuy(LATE) / daily_net >= 0.50
                        EARLY_TILTED otherwise
threshold:              0.50 — a structural midpoint (more than half the day's net buying in the final
                        hour), frozen here; NOT tuned, and may not be varied at execution.

# ---------------------------------------------------------------- estimand ---
primary_estimand:       theta_primary
step_1:                 For each admitted formation date d with >= 1 LATE_TILTED and >= 1 EARLY_TILTED
                        cell: m(d) = mean fwd return of LATE_TILTED cells
                                   - mean fwd return of EARLY_TILTED cells
                        Dates lacking either side are SKIPPED AND COUNTED (never zero-filled).
step_2:                 theta_primary = mean of the daily series m(d)
estimator:              daily-series-first aggregation (BFI-001 §G/§I convention; used by C3 and C7)
horizon:                k = 1 (primary).  k in {2,3} reported as robustness ONLY; may never become
                        primary.
outcome:                fwd_return = close(t+2)/close(t+1) - 1
entry_reference:        close(t+1) — one full session after formation
inference:              Newey-West HAC, lag = 5; two-sided p
                        # The §16 decision additionally requires theta_primary > 0, so the DECISION is
                        # one-sided implemented with a two-sided statistic (nominal one-sided size
                        # 0.025). Recorded descriptively; unchanged from the specification.
multiplicity:           SINGLE CELL. Holm at the primary is the identity (holm_p = raw two-sided p).
                        Every other quantity is non-confirmatory and enters no Holm family.

# ------------------------------------------------------------- exclusions ---
X1:                     2025-04-14 fixture — SUBSUMED by E-PIT-1 (region ends before 2026-04-28)
X2:                     2025-08-04..2025-09-17 contradiction zone — SUBSUMED by E-PIT-1
X3:                     ENFORCED, session-level, ahead of the E-PIT predicates. A candidate session is
                        admissible only if present in the EFFECTIVE session calendar with admitted
                        status. Effective calendar = DATASET_B_SESSION_CALENDAR_v2 (sha 5012be23...)
                        UNION I7_SESSION_CALENDAR_EXTENSION_v1 (sha a7a4eedf...).
                        Excluded sessions (8): 2026-05-01, 05-14, 05-15, 05-28, 06-16 (non-trading
                        days), 2026-07-09, 2026-07-24 (is_admitted=0), 2026-09-14 (beyond horizon).
X4:                     ENFORCED as E-PIT-4 (bars present; n_bars == weekday structural grid)
X5:                     ESTIMATION-LAYER (ohlcv: corporate action t/t+1/t+2, RAJA, close(t) < Rp100,
                        PIT liquidity floor) — applied and COUNTED by the estimator; deliberately not
                        applied at accrual, where reading prices would breach result-blindness.
X6:                     ESTIMATION-LAYER (t, t+1, t+2 strictly consecutive admitted sessions) — as X5.
E-PIT-1:                historical/backfilled interval excluded wholesale (session <= 2026-04-27)
E-PIT-2:                no contemporaneous provenance (write lag outside 0..1 days)
E-PIT-3:                same-day capture before the 16:15 WIB post-session cutoff
E-PIT-4:                bars absent, or n_bars != weekday structural grid (335 Mon-Thu / 275 Fri)
ledger:                 61335 admitted + 7038 X3 + 2044 E-PIT-2 + 1507 E-PIT-3 + 10890 E-PIT-4
                        = 82814 candidate cells (exact, MECE, duplicate-free)
no_minimum_unit_rule:   NONE. No minimum-cell or minimum-session rule exists at the accrual layer.
                        2026-09-08 retains its single admissible cell and is disposed of by step_1.

# ------------------------------------------------- ex-ante criterion (D-050) ---
effect_size_floor:      0.60% round-trip friction (versioned cost authority engine/exits/costs.py)
                        Authoritatively supported by the ratified HYP-PM-0001_POWER §3-§4 methodology
                        ("the ex-ante MDE must be economic, not statistical"), program gate F4
                        (RESEARCH_PROGRAM §6.1) and PR-3 (EXPERIMENT_STANDARD §1 Q2).
cost_convention:        theta_net = theta_primary - 0.006, reported as a SENSITIVITY ONLY; never a
                        statistical verdict.
power_mde_claim:        NONE beyond the economic floor above. Per Owner ruling D-050, I7 proceeds
                        WITHOUT an ex-ante statistical power/MDE claim. The absence of an authoritative
                        I7-specific assumed sigma and of an applicable feasibility gate is ACCEPTED AS A
                        GOVERNANCE LIMITATION, not filled by estimation from the frozen cohort, by
                        analogy to any other hypothesis, or by newly invented methodology.
minimum_n / stopping:   NONE. No power-derived minimum-N, feasibility gate or stopping rule exists for
                        I7, and none may be introduced after registration (R15).
interpretation_limit:   I7 CARRIES NO POWER CLAIM. A non-rejection is therefore NOT evidence of
                        absence and must never be reported as one.

# ------------------------------------------------------------- decision rule ---
kill_rule:              If theta_primary is not positive with two-sided p < 0.05 under the primary
                        specification, the hypothesis that within-session back-loading of net buying
                        carries information beyond the daily total is REFUTED, and the hypothesis
                        terminates as FAILED (mode F2 · prediction failure).
direction_read:         after execution, never prejudged (BFI-001 §G convention)
no_rescue:              A null is terminal; continuation only via T12 supersession (a new registration
                        consuming its own slot). No re-cut may be promoted to primary post hoc — not by
                        tier, liquidity, side, horizon, threshold, sub-period, regime re-pooling or
                        universe floor. The segment bounds, the 0.50 threshold, the conditioning, the
                        horizon, the exclusion set and the inference are frozen by this record.

# ------------------------------------------------------------- limitations ---
pit_provenance (R7):    Declared TRUE WITH QUALIFICATION. PIT status rests on stockbit_flow.updated_at,
                        a write timestamp emitted by this system's own writer in the SAME COMMIT as the
                        corresponding bars (naive Asia/Jakarta); the backfill skips already-complete
                        cells, so an updated_at still bearing its own trade date also establishes the
                        cell was never later rewritten. Admits only cells written within one day of
                        their session and, for same-day writes, only after 16:15 WIB.
                        This supports "this system held these values contemporaneously with the session,
                        and they were not later altered". It does NOT preserve the vendor's original
                        payload, request parameters or vendor-side timestamp, and therefore does NOT
                        support "the original vendor response is independently re-verifiable".
                        A VERIFICATION limitation, not an AVAILABILITY one. Byte-for-byte reproduction
                        from recorded inputs is impossible; a source-agreement spot check records
                        200/200 sampled admitted cells matching the live source
                        (I7_V004_SOURCE_PROVENANCE_v1.json).
custody_partition:      in-sample
b4_limitation:          Papan Pemantauan Khusus / board membership is unidentifiable in held data; the
                        PIT liquidity floor is a mitigation, not a solution.
oos_partition:          NONE — this hypothesis is in-sample only.
semantic_gate (D-049):  COMPLIANT, trivially — no all-broker net is constructed anywhere; the
                        instrument's buy and sell sides are separate aggressor-side quantities.
```
<!--FROZEN-END-->

## Registration receipt (HL-1)

> One transition, one receipt. This receipt binds the transition; the SHA-256 seals the frozen object above.

| Field | Value |
|---|---|
| **Hypothesis ID** | HYP-PM-0009 |
| **Transition** | `DRAFT → REGISTERED` (T4 / G1) |
| **Registered at** | 2026-09-14 |
| **Registered by** | Owner / CRO ruling — `DECISION_LOG` **D-050** ("I explicitly authorize I7 to proceed without an ex-ante statistical power/MDE claim beyond the already-authorized 0.60% economic/friction floor … If all other G1 gates pass, register I7 and stop before execution.") |
| **G1 gate** | **Satisfied.** All six §5.2 elements present — mechanism (M2/I7 + constraint + participant class), directional prediction, **null** (H₀ : θ ≤ 0), scope (v004, fingerprint-bound, D-1 ACCEPTED), ex-ante criterion incl. effect size (0.60% friction floor; power/MDE claim closed by D-050), multiplicity family (P-M {I5,I6,I7,I12}); mechanism `blind_to` stated; refutation condition in one sentence; `required_data` resolves Available Today (D-002); CRO approval recorded above |
| **preregistration_sha256** | `d19dfd0f6b059a4b4c564361087bf9aa59e327c8105c5229e166afa64f76b75a` (SHA-256 of the exact frozen specification block between the FROZEN markers above) |
| **Immutability** | This record is immutable. A revision is a **new** hypothesis (supersession, T12/HL), never an edit (R15, HL-2). |
| **Family effect** | HYP-PM-0009 is the **third REGISTERED member of P-M {I5, I6, I7, I12}** — joining `HYP-PM-0001` (REGISTERED 2026-07-17, FAILED F2) and `HYP-PM-0003` (REGISTERED 2026-09-09, FAILED F2 → INVALID-DATA). The slot is permanent (PG-3, OS-10). `HYP-PM-0002` remains DRAFT and consumes no slot |
| **Pre-registration verification** | 27/27 tests (`test_i7_admissibility.py` 18, `test_i7_x3.py` 9); 8/8 executable validation gates (`validate_v004_freeze.py --with-source`, exit 0); ledger exact and MECE; v003 immutable `a4a9f7f9…`; cohort unchanged |
| **Next** | **Experiment execution — NOT PERFORMED.** Registration stops here per the Owner's instruction ("register I7 and stop before execution"). No OOS/Blind partition is released (none exists) |

## Lineage

| Artifact | Role |
|---|---|
| `BRANCH_A_NEW_MECHANISM_AUDIT_2026-09-14.md` §1–§17 (sha256 `76a96545…`) | Candidate specification — source of every substantive field frozen above; **unmodified** |
| `I7_PIT_PROVENANCE_AUDIT_2026-09-14.md` | Established the E-PIT-1 boundary and the R7 limitation |
| `I7_ACCRUAL_READINESS_2026-09-14.md` | v003 cohort + E-PIT gate implementation |
| `I7_REGISTRATION_READINESS_REVIEW_2026-09-14.md` | Forensic review; identified the X3 defect |
| `I7_V004_REMEDIATION_RECORD_2026-09-14.md` | X3 enforcement, calendar extension, R1–R9 closure |
| `I7_OWNER_DECISION_PACKAGE_2026-09-14.md` | D-1 / D-2 decision support |
| `I7_G1_GAP_CLOSURE_2026-09-14.md` | Null supplied as the exact complement of the §1 prediction |
| `I7_D2_METHODOLOGY_SEARCH_2026-09-14.md` · `I7_D2_EVIDENCE_RECORD_2026-09-14.md` | D-2 authoritative-methodology search and its terminal record |
| `DECISION_LOG` **D-050** | Owner ruling: D-1 accepted, D-2 closed, registration authorized |
| `I7_V004_MANIFEST.json` · `I7_V004_SOURCE_PROVENANCE_v1.json` | Cohort manifest and source-state fingerprint |
